import copy
import uuid
import datetime
import json
from io import StringIO
import traceback

from astropy.time import Time
from astropy.table import Table
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
import sncosmo
from sncosmo.photdata import PhotometricData
import arrow
from matplotlib import cm
from matplotlib.colors import rgb2hex, LinearSegmentedColormap

import sqlalchemy as sa
from sqlalchemy.sql import column, Values
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log
from baselayer.app.flow import Flow
from ..base import BaseHandler
from ...models import (
    DBSession,
    Annotation,
    Group,
    Stream,
    Photometry,
    PhotometricSeries,
    Instrument,
    Obj,
    PHOT_ZP,
    GroupPhotometry,
    StreamPhotometry,
    PhotStat,
    User,
)

from ...models.schema import (
    PhotometryMag,
    PhotometryFlux,
    PhotFluxFlexible,
    PhotMagFlexible,
    PhotometryRangeQuery,
)
from ...enum_types import ALLOWED_MAGSYSTEMS, ALLOWED_BANDPASSES
from .photometry_validation import USE_PHOTOMETRY_VALIDATION

_, cfg = load_env()


log = make_log('api/photometry')

MAX_NUMBER_ROWS = 10000

cmap_ir = cm.get_cmap('autumn')
cmap_deep_ir = LinearSegmentedColormap.from_list(
    "deep_ir", [(0.8, 0.2, 0), (0.6, 0.1, 0)]
)


def hex2rgb(hex):
    """Convert hex color string to rgb tuple.

    Parameters
    ----------
    hex : str
        Hex color string.

    Returns
    -------
    tuple
        RGB tuple.
    """

    return tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))


def get_effective_wavelength(bandpass_name, radius=None):
    """Get the effective wavelength of an sncosmo bandpass.

    Parameters
    ----------
    bandpass_name : str
        Name of the bandpass.
    radius : float, optional
        Radius to get the bandpass for. If None, the default bandpass is used.

    Returns
    -------
    float
        Effective wavelength of the bandpass.
    """
    try:
        args = {}
        if radius is not None:
            args['radius'] = radius
        bandpass = sncosmo.get_bandpass(bandpass_name, **args)
    except ValueError as e:
        raise ValueError(
            f"Could not get bandpass for {bandpass_name} due to sncosmo error: {e}"
        )

    return float(bandpass.wave_eff)


def get_color(bandpass, format="hex"):
    """Get a color for a bandpass, in hex or rgb format.

    Parameters
    ----------
    bandpass : str
        Name of the sncosmo bandpass.
    format : str, optional
        Format of the output color. Must be one of "hex" or "rgb".

    Returns
    -------
    str or tuple
        Color of the bandpass in the requested format
    """

    wavelength = get_effective_wavelength(bandpass)

    if 0 < wavelength <= 1500:  # EUV
        bandcolor = '#4B0082'
    elif 1500 < wavelength <= 2100:  # uvw2
        bandcolor = '#6A5ACD'
    elif 2100 < wavelength <= 2400:  # uvm2
        bandcolor = '#9400D3'
    elif 2400 < wavelength <= 3000:  # uvw1
        bandcolor = '#FF00FF'
    elif 3000 < wavelength <= 4000:  # U, sdss u
        bandcolor = '#0000FF'
    elif 4000 < wavelength <= 4800:  # B, sdss g
        bandcolor = '#02d193'
    elif 4800 < wavelength <= 5000:  # ztfg
        bandcolor = '#008000'
    elif 5000 < wavelength <= 6000:  # V
        bandcolor = '#9ACD32'
    elif 6000 < wavelength <= 6400:  # sdssr
        bandcolor = '#ff6f00'
    elif 6400 < wavelength <= 6600:  # ztfr
        bandcolor = '#FF0000'
    elif 6400 < wavelength <= 7000:  # bessellr, atlaso
        bandcolor = '#c80000'
    elif 7000 < wavelength <= 8000:  # sdss i
        bandcolor = '#FFA500'
    elif 8000 < wavelength <= 9000:  # sdss z
        bandcolor = '#A52A2A'
    elif 9000 < wavelength <= 10000:  # PS1 y
        bandcolor = '#B8860B'
    elif 10000 < wavelength <= 13000:  # 2MASS J
        bandcolor = '#000000'
    elif 13000 < wavelength <= 17000:  # 2MASS H
        bandcolor = '#9370D8'
    elif 17000 < wavelength <= 1e5:  # mm to Radio
        bandcolor = rgb2hex(cmap_ir((5 - np.log10(wavelength)) / 0.77)[:3])
    elif 1e5 < wavelength <= 3e5:  # JWST miri and miri-tophat
        bandcolor = rgb2hex(cmap_deep_ir((5.48 - np.log10(wavelength)) / 0.48)[:3])
    else:
        log(
            f'{bandpass} with effective wavelength {wavelength} is out of range for color maps, using black'
        )
        bandcolor = '#000000'

    if format == "rgb":
        return hex2rgb(bandcolor[1:])
    elif format not in ["hex", "rgb"]:
        raise ValueError(f"Invalid color format: {format}")

    return bandcolor


def get_bandpasses_to_colors(bandpasses, colors_type="rgb"):
    return {bandpass: get_color(bandpass, colors_type) for bandpass in bandpasses}


BANDPASSES_COLORS = get_bandpasses_to_colors(ALLOWED_BANDPASSES, "rgb")

BANDPASSES_WAVELENGTHS = {
    bandpass: get_effective_wavelength(bandpass) for bandpass in ALLOWED_BANDPASSES
}


def save_data_using_copy(rows, table, columns):
    # Prepare data
    output = StringIO()
    df = pd.DataFrame.from_records(rows)
    # Coerce missing non-numbers and numbers, respectively, for SQLAlchemy
    df.replace("NaN", "null", inplace=True)
    df.replace(np.nan, "NaN", inplace=True)

    df.to_csv(
        output,
        index=False,
        sep='\t',
        header=False,
        encoding='utf8',
        quotechar="'",
    )
    output.seek(0)

    # Insert data
    connection = DBSession().connection().connection
    cursor = connection.cursor()
    cursor.copy_from(
        output,
        table,
        sep='\t',
        null='',
        columns=columns,
    )
    cursor.close()
    output.close()


def nan_to_none(value):
    """Coerce a value to None if it is nan, else return value."""
    try:
        return None if np.isnan(value) else value
    except TypeError:
        return value


def allscalar(d):
    return all(np.isscalar(v) or v is None for v in d.values())


def serialize(
    phot,
    outsys,
    format,
    created_at=True,
    groups=True,
    annotations=True,
    owner=False,
    stream=False,
    validation=False,
):
    return_value = {
        'obj_id': phot.obj_id,
        'ra': phot.ra,
        'dec': phot.dec,
        'filter': phot.filter,
        'mjd': phot.mjd,
        'snr': phot.snr,
        'instrument_id': phot.instrument_id,
        'instrument_name': phot.instrument.name,
        'ra_unc': phot.ra_unc,
        'dec_unc': phot.dec_unc,
        'origin': phot.origin,
        'id': phot.id,
        'altdata': phot.altdata,
    }
    if created_at:
        return_value['created_at'] = phot.created_at
    if groups:
        return_value['groups'] = [
            {
                'id': group.id,
                'name': group.name,
                'nickname': group.nickname,
                'single_user_group': group.single_user_group,
            }
            for group in phot.groups
        ]
    if annotations:
        return_value['annotations'] = (
            [annotation.to_dict() for annotation in phot.annotations]
            if hasattr(phot, 'annotations')
            else []
        )
    if owner:
        return_value['owner'] = {
            'id': phot.owner.id,
            'username': phot.owner.username,
            'first_name': phot.owner.first_name,
            'last_name': phot.owner.last_name,
        }
    if stream:
        return_value['streams'] = [
            {
                'id': stream.id,
                'name': stream.name,
            }
            for stream in phot.streams
        ]
    if USE_PHOTOMETRY_VALIDATION and validation:
        return_value['validations'] = [
            validation.to_dict() for validation in phot.validations
        ]

    if (
        phot.ref_flux is not None
        and not np.isnan(phot.ref_flux)
        and phot.ref_fluxerr is not None
        and not np.isnan(phot.ref_fluxerr)
    ):
        return_value['ref_flux'] = phot.ref_flux
        return_value['tot_flux'] = phot.tot_flux
        return_value['ref_fluxerr'] = phot.ref_fluxerr
        return_value['tot_fluxerr'] = phot.tot_fluxerr
        return_value['magref'] = phot.magref
        return_value['magtot'] = phot.magtot
        return_value['e_magref'] = phot.e_magref
        return_value['e_magtot'] = phot.e_magtot

    filter = phot.filter

    magsys_db = sncosmo.get_magsystem('ab')
    outsys = sncosmo.get_magsystem(outsys)

    try:
        relzp_out = 2.5 * np.log10(outsys.zpbandflux(filter))

        # note: these are not the actual zeropoints for magnitudes in the db or
        # packet, just ones that can be used to derive corrections when
        # compared to relzp_out

        relzp_db = 2.5 * np.log10(magsys_db.zpbandflux(filter))
        db_correction = relzp_out - relzp_db

        # this is the zeropoint for fluxes in the database that is tied
        # to the new magnitude system
        corrected_db_zp = PHOT_ZP + db_correction

        if format not in ['mag', 'flux', 'both']:
            raise ValueError(
                'Invalid output format specified. Must be one of '
                f"['flux', 'mag', 'both'], got '{format}'."
            )

        if format in ['mag', 'both']:
            if (
                phot.original_user_data is not None
                and 'limiting_mag' in phot.original_user_data
            ):
                magsys_packet = sncosmo.get_magsystem(phot.original_user_data['magsys'])
                relzp_packet = 2.5 * np.log10(magsys_packet.zpbandflux(filter))
                packet_correction = relzp_out - relzp_packet
                maglimit = float(phot.original_user_data['limiting_mag'])
                maglimit_out = maglimit + packet_correction
            else:
                # calculate the limiting mag
                fluxerr = phot.fluxerr
                fivesigma = 5 * fluxerr
                maglimit_out = -2.5 * np.log10(fivesigma) + corrected_db_zp

            return_value.update(
                {
                    'mag': phot.mag + db_correction
                    if nan_to_none(phot.mag) is not None
                    else None,
                    'magerr': phot.e_mag
                    if nan_to_none(phot.e_mag) is not None
                    else None,
                    'magsys': outsys.name,
                    'limiting_mag': maglimit_out,
                }
            )
            if (
                phot.ref_flux is not None
                and not np.isnan(phot.ref_flux)
                and phot.ref_fluxerr is not None
                and not np.isnan(phot.ref_fluxerr)
            ):
                return_value.update(
                    {
                        'magref': phot.magref + db_correction
                        if nan_to_none(phot.magref) is not None
                        else None,
                        'magtot': phot.magtot,
                        'e_magref': phot.e_magref,
                        'e_magtot': phot.e_magtot,
                    }
                )

        if format in ['flux', 'both']:
            return_value.update(
                {
                    'flux': nan_to_none(phot.flux),
                    'magsys': outsys.name,
                    'zp': corrected_db_zp,
                    'fluxerr': phot.fluxerr,
                }
            )
            if (
                phot.ref_flux is not None
                and not np.isnan(phot.ref_flux)
                and phot.ref_fluxerr is not None
                and not np.isnan(phot.ref_fluxerr)
            ):
                return_value.update(
                    {
                        'ref_flux': phot.ref_flux,
                        'tot_flux': phot.tot_flux,
                        'ref_fluxerr': phot.ref_fluxerr,
                        'tot_fluxerr': phot.tot_fluxerr,
                    }
                )
    except ValueError as e:
        raise ValueError(
            f"Could not serialize phot_id: {phot.id} "
            f"on obj {phot.obj_id} with filter: {filter},  "
            f"due to error: {e}"
        )
    return return_value


def standardize_photometry_data(data):
    if not isinstance(data, dict):
        raise ValidationError(
            'Top level JSON must be an instance of `dict`, got ' f'{type(data)}.'
        )

    max_num_elements = max(
        [
            len(data[key])
            for key in data
            if isinstance(data[key], (list, tuple))
            and key not in ["group_ids", "stream_ids"]
        ]
        + [1]
    )

    if "altdata" in data and not data["altdata"]:
        del data["altdata"]
    if "altdata" in data:
        if isinstance(data["altdata"], dict):
            for key in data["altdata"].keys():
                if isinstance(data["altdata"][key], list):
                    if not len(data["altdata"][key]) == max_num_elements:
                        if len(data["altdata"][key]) == 1:
                            data["altdata"][key] = (
                                data["altdata"][key] * max_num_elements
                            )
                        else:
                            raise ValueError(f'{key} in altdata incorrect length')
                elif max_num_elements > 1:
                    data["altdata"][key] = [data["altdata"][key]] * max_num_elements

            altdata = data.pop("altdata")
            try:
                df = pd.DataFrame(altdata)
            except ValueError:
                df = pd.DataFrame(altdata, index=[0])
            altdata = df.to_dict(orient='records')
        else:
            altdata = data.pop("altdata")
    else:
        altdata = None

    # quick validation - just to make sure things have the right fields
    try:
        data = PhotMagFlexible.load(data)
    except ValidationError as e1:
        try:
            data = PhotFluxFlexible.load(data)
        except ValidationError as e2:
            raise ValidationError(
                'Invalid input format: Tried to parse data '
                f'in mag space, got: '
                f'"{e1.normalized_messages()}." Tried '
                f'to parse data in flux space, got:'
                f' "{e2.normalized_messages()}."'
            )
        else:
            kind = 'flux'
    else:
        kind = 'mag'

    # not used here
    _ = data.pop('group_ids', None)
    _ = data.pop('stream_ids', None)

    if allscalar(data):
        data = [data]

    try:
        if max_num_elements == 1:
            df = pd.DataFrame(data, index=[0])
        else:
            df = pd.DataFrame(data)
    except ValueError as e:
        raise ValidationError(
            'Unable to coerce passed JSON to a series of packets. ' f'Error was: "{e}"'
        )

    if altdata is not None and len(altdata) > 0:
        for index, e in enumerate(altdata):
            altdata[index] = (
                {k: v for k, v in e.items() if v not in [None, '']}
                if not all([v in [None, ''] for v in e.values()])
                else None
            )
        df['altdata'] = altdata

    # `to_numeric` coerces numbers written as strings to numeric types
    #  (int, float)

    #  errors='ignore' means if something is actually an alphanumeric
    #  string, just leave it alone and dont error out

    #  apply is used to apply it to each column
    # (https://stackoverflow.com/questions/34844711/convert-entire-pandas
    # -dataframe-to-integers-in-pandas-0-17-0/34844867
    df = df.apply(pd.to_numeric, errors='ignore')

    # set origin to 'None' where it is None.
    df.loc[df['origin'].isna(), 'origin'] = 'None'
    ref_phot_table = None

    if kind == 'mag':
        # ensure that neither or both mag and magerr are null
        magnull = df['mag'].isna()
        magerrnull = df['magerr'].isna()
        magdet = ~magnull

        # https://en.wikipedia.org/wiki/Bitwise_operation#XOR
        bad = magerrnull ^ magnull  # bitwise exclusive or -- returns true
        #  if A and not B or B and not A

        # coerce to numpy array
        bad = bad.values

        if any(bad):
            # find the first offending packet
            first_offender = np.argwhere(bad)[0, 0]
            packet = df.iloc[first_offender].to_dict()

            # coerce nans to nones
            for key in packet:
                if key != 'standardized_flux':
                    packet[key] = nan_to_none(packet[key])

            raise ValidationError(
                f'Error parsing packet "{packet}": mag '
                f'and magerr must both be null, or both be '
                f'not null.'
            )

        for field in ['mag', 'magerr', 'limiting_mag']:
            infinite = np.isinf(df[field].values)
            if any(infinite):
                first_offender = np.argwhere(infinite)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                # coerce nans to nones
                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": '
                    f'field {field} must be finite.'
                )

        # ensure nothing is null for the required fields
        for field in PhotMagFlexible.required_keys:
            missing = df[field].isna()
            if any(missing):
                first_offender = np.argwhere(missing.values)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                # coerce nans to nones
                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": '
                    f'missing required field {field}.'
                )

        # convert the mags to fluxes
        # detections
        detflux = 10 ** (-0.4 * (df[magdet]['mag'] - PHOT_ZP))
        detfluxerr = df[magdet]['magerr'] / (2.5 / np.log(10)) * detflux

        # non-detections
        limmag_flux = 10 ** (-0.4 * (df[magnull]['limiting_mag'] - PHOT_ZP))
        ndetfluxerr = limmag_flux / df[magnull]['limiting_mag_nsigma']

        # initialize flux to be none
        phot_table = Table.from_pandas(df[['mjd', 'magsys', 'filter']])

        phot_table['zp'] = PHOT_ZP
        phot_table['flux'] = np.nan
        phot_table['fluxerr'] = np.nan
        phot_table['flux'][magdet] = detflux
        phot_table['fluxerr'][magdet] = detfluxerr
        phot_table['fluxerr'][magnull] = ndetfluxerr

        if "magref" in df.columns and "e_magref" in df.columns:
            ref_phot_table = Table.from_pandas(df[['mjd', 'magsys', 'filter']])
            magref = df['magref'].fillna(np.nan)
            ref_phot_table['flux'] = 10 ** (-0.4 * (magref - PHOT_ZP))
            ref_phot_table['fluxerr'] = (
                df['e_magref'] / (2.5 / np.log(10)) * ref_phot_table['flux']
            )
            ref_phot_table['zp'] = PHOT_ZP

    else:
        for field in PhotFluxFlexible.required_keys:
            missing = df[field].isna().values
            if any(missing):
                first_offender = np.argwhere(missing)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": '
                    f'missing required field {field}.'
                )

        for field in ['flux', 'fluxerr']:
            infinite = np.isinf(df[field].values)
            if any(infinite):
                first_offender = np.argwhere(infinite)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                # coerce nans to nones
                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": '
                    f'field {field} must be finite.'
                )

        phot_table = Table.from_pandas(df[['mjd', 'magsys', 'filter', 'zp']])
        phot_table['flux'] = df['flux'].fillna(np.nan)
        phot_table['fluxerr'] = df['fluxerr'].fillna(np.nan)

        if "ref_flux" in df.columns and "ref_fluxerr" in df.columns:
            ref_phot_table = Table.from_pandas(df[['mjd', 'magsys', 'filter']])
            ref_phot_table['flux'] = df['ref_flux'].fillna(np.nan)
            ref_phot_table['fluxerr'] = df['ref_fluxerr'].fillna(np.nan)
            if 'ref_zp' in df.columns:
                ref_phot_table['zp'] = df['ref_zp'].fillna(np.nan)
            else:
                ref_phot_table['zp'] = PHOT_ZP

    unknown_filters = set(phot_table['filter']).difference(ALLOWED_BANDPASSES)
    if len(unknown_filters) > 0:
        raise ValidationError(
            f'Filter(s) {unknown_filters} is not allowed. '
            f'Allowed filters are: {ALLOWED_BANDPASSES}'
        )

    # convert to microjanskies, AB for DB storage as a vectorized operation
    pdata = PhotometricData(phot_table)
    standardized = pdata.normalized(zp=PHOT_ZP, zpsys='ab')

    df['standardized_flux'] = standardized.flux
    df['standardized_fluxerr'] = standardized.fluxerr

    # convert the reference flux to microjanskies, AB
    if ref_phot_table:
        ref_pdata = PhotometricData(ref_phot_table)
        ref_standardized = ref_pdata.normalized(zp=PHOT_ZP, zpsys='ab')
        df['ref_standardized_flux'] = ref_standardized.flux
        df['ref_standardized_fluxerr'] = ref_standardized.fluxerr

    instrument_cache = {}
    for iid in df['instrument_id'].unique():
        instrument = Instrument.query.get(int(iid))
        if not instrument:
            raise ValidationError(f'Invalid instrument ID: {iid}')
        instrument_cache[iid] = instrument

    # convert the object IDs to str datatype
    df['obj_id'] = df['obj_id'].astype(str)

    for oid in df['obj_id'].unique():
        obj = Obj.query.get(oid)
        if not obj:
            raise ValidationError(f'Invalid object ID: {oid}')

    return df, instrument_cache


def get_values_table_and_condition(df, ignore_flux=False):
    """Return a postgres VALUES representation of the indexed columns of
    a photometry dataframe returned by `standardize_photometry_data`.
    Also returns the join condition for cross-matching the VALUES
    representation of `df` against the Photometry table using the
    deduplication index.

    Parameters
    ----------
    df: `pandas.DataFrame`
        Dataframe with the columns 'obj_id', 'instrument_id', 'origin',
        'mjd', 'standardized_fluxerr', 'standardized_flux'.
    ignore_flux: bool
        Whether or not we take flux into account when deduplicating

    Returns
    -------
    values_table: `sqlalchemy.sql.expression.FromClause`
        The VALUES representation of the photometry DataFrame.

    condition: `sqlalchemy.sql.elements.AsBoolean`
       The join condition for cross matching the VALUES representation of
       `df` against the Photometry table using the deduplication index.
    """
    values_table = (
        Values(
            column("pdidx", sa.Integer),
            column("obj_id", sa.String),
            column("instrument_id", sa.Integer),
            column("origin", sa.String),
            column("mjd", sa.Float),
            column("fluxerr", sa.Float),
            column("flux", sa.Float),
        )
        .data(
            [
                (
                    row.Index,
                    row.obj_id,
                    row.instrument_id,
                    str(row.origin),
                    float(row.mjd),
                    float(row.standardized_fluxerr),
                    float(row.standardized_flux),
                )
                for row in df.itertuples()
            ]
        )
        .alias("values_table")
    )
    # make sure no duplicate data are posted
    if ignore_flux:
        # WARNING: here we don't use the unique index, so that might be slower
        condition = and_(
            Photometry.obj_id == values_table.c.obj_id,
            Photometry.instrument_id == values_table.c.instrument_id,
            Photometry.origin == values_table.c.origin,
            Photometry.mjd == values_table.c.mjd,
        )
    else:
        # here we use the existing deduplication index
        condition = and_(
            Photometry.obj_id == values_table.c.obj_id,
            Photometry.instrument_id == values_table.c.instrument_id,
            Photometry.origin == values_table.c.origin,
            Photometry.mjd == values_table.c.mjd,
            Photometry.fluxerr == values_table.c.fluxerr,
            Photometry.flux == values_table.c.flux,
        )

    return values_table, condition


def insert_new_photometry_data(
    df,
    instrument_cache,
    group_ids,
    stream_ids,
    user,
    session,
    validate=True,
    refresh=False,
):
    # check for existing photometry and error if any is found
    if validate:
        values_table, condition = get_values_table_and_condition(df)

        duplicated_photometry = (
            session.execute(sa.select(Photometry).join(values_table, condition))
            .scalars()
            .all()
        )

        dict_rep = [d.to_dict() for d in duplicated_photometry]

        if len(dict_rep) > 0:
            raise ValidationError(
                'The following photometry already exists '
                f'in the database: {dict_rep}.'
            )

    # pre-fetch the photometry PKs. these are not guaranteed to be
    # gapless (e.g., 1, 2, 3, 4, 5, ...) but they are guaranteed
    # to be unique in the table and thus can be used to "reserve"
    # PK slots for uninserted rows

    pkq = sa.text(
        f"SELECT nextval('photometry_id_seq') FROM " f"generate_series(1, {len(df)})"
    )

    proxy = session.execute(pkq)

    # cache this as list for response
    ids = [i[0] for i in proxy]
    df['id'] = ids

    df = df.where(pd.notnull(df), None)
    df.loc[df['standardized_flux'].isna(), 'standardized_flux'] = np.nan

    rows = df.to_dict('records')
    upload_id = str(uuid.uuid4())

    params = []
    group_photometry_params = []
    stream_photometry_params = []
    for packet in rows:
        if (
            instrument_cache[packet['instrument_id']].type == "imager"
            and packet["filter"]
            not in instrument_cache[packet['instrument_id']].filters
        ):
            instrument = instrument_cache[packet['instrument_id']]
            raise ValidationError(
                f"Instrument {instrument.name} has no filter " f"{packet['filter']}."
            )

        flux = packet.pop('standardized_flux')
        fluxerr = packet.pop('standardized_fluxerr')

        # reduce the DB size by ~2x
        keys = ['limiting_mag', 'magsys', 'limiting_mag_nsigma']
        original_user_data = {key: packet[key] for key in keys if key in packet}
        if original_user_data == {}:
            original_user_data = None

        utcnow = datetime.datetime.utcnow().isoformat()
        phot = dict(
            id=packet['id'],
            original_user_data=json.dumps(original_user_data),
            upload_id=upload_id,
            flux=flux,
            fluxerr=fluxerr,
            obj_id=packet['obj_id'],
            altdata=json.dumps(packet.get('altdata')),
            instrument_id=packet['instrument_id'],
            ra_unc=packet['ra_unc'],
            dec_unc=packet['dec_unc'],
            mjd=packet['mjd'],
            filter=packet['filter'],
            ra=packet['ra'],
            dec=packet['dec'],
            origin=packet["origin"],
            owner_id=user.id,
            created_at=utcnow,
            modified=utcnow,
        )

        if 'ref_standardized_flux' in packet:
            phot['ref_flux'] = packet.pop('ref_standardized_flux')
            phot['ref_fluxerr'] = packet.pop('ref_standardized_fluxerr')
        else:
            phot['ref_flux'] = None
            phot['ref_fluxerr'] = None

        params.append(phot)

        for group_id in group_ids:
            group_photometry_params.append(
                {
                    'photometr_id': packet['id'],
                    'group_id': group_id,
                    'created_at': utcnow,
                    'modified': utcnow,
                }
            )

        for stream_id in stream_ids:
            stream_photometry_params.append(
                {
                    'photometr_id': packet['id'],
                    'stream_id': stream_id,
                    'created_at': utcnow,
                    'modified': utcnow,
                }
            )

    if len(params) > 0:
        save_data_using_copy(
            params,
            "photometry",
            (
                'id',
                'original_user_data',
                'upload_id',
                'flux',
                'fluxerr',
                'obj_id',
                'altdata',
                'instrument_id',
                'ra_unc',
                'dec_unc',
                'mjd',
                'filter',
                'ra',
                'dec',
                'origin',
                'owner_id',
                'created_at',
                'modified',
                'ref_flux',
                'ref_fluxerr',
            ),
        )

    if len(group_photometry_params) > 0:
        # Bulk COPY in the group_photometry records
        save_data_using_copy(
            group_photometry_params,
            "group_photometry",
            ('photometr_id', 'group_id', 'created_at', 'modified'),
        )

    if len(stream_photometry_params) > 0:
        # Bulk COPY in the stream_photometry records
        save_data_using_copy(
            stream_photometry_params,
            "stream_photometry",
            ('photometr_id', 'stream_id', 'created_at', 'modified'),
        )

    # add a phot stats for each photometry
    obj_id = phot['obj_id']
    phot_stat = session.scalars(
        sa.select(PhotStat).where(PhotStat.obj_id == obj_id)
    ).first()
    # if there are a lot of new points, should just
    # pull up all the photometry and recalculate
    # instead of adding them one-by-one
    if phot_stat is None or len(params) > 50:
        all_phot = session.scalars(
            sa.select(Photometry).where(Photometry.obj_id == obj_id)
        ).all()

        if phot_stat is None:
            phot_stat = PhotStat(obj_id=obj_id)

        phot_stat.full_update(all_phot)

    else:
        for phot in params:
            phot_stat.add_photometry_point(phot)

    session.add(phot_stat)
    session.commit()  # add the updated phot_stats

    if refresh:
        flow = Flow()
        # grab the list of unique obj_ids
        obj_ids = df['obj_id'].unique()
        for obj_id in obj_ids:
            internal_key = session.scalar(
                sa.select(Obj.internal_key).where(Obj.id == obj_id)
            )
            flow.push(
                '*',
                'skyportal/REFRESH_SOURCE',
                payload={'obj_key': internal_key},
            )

            flow.push(
                '*',
                'skyportal/FETCH_SOURCE_PHOTOMETRY',
                payload={'obj_id': obj_id},
            )

    return ids, upload_id


def get_group_ids(data, user, parent_session=None):
    if parent_session is None:
        session = DBSession()
    else:
        session = parent_session

    group_ids = data.pop("group_ids", [])
    if isinstance(group_ids, (list, tuple)):
        try:
            group_ids = {int(group_id) for group_id in group_ids}
        except ValueError:
            raise ValidationError(
                "Invalid format for group_ids parameter. Must be a list of integers."
            )
        groups = (
            session.scalars(sa.select(Group).where(Group.id.in_(list(group_ids))))
            .unique()
            .all()
        )
        available_group_ids = {group.id for group in groups}
        diff_group_ids = group_ids - available_group_ids
        if diff_group_ids:
            raise ValidationError(
                f"Invalid group IDs: {diff_group_ids}. Available group IDs: {available_group_ids}"
            )
    elif group_ids == 'all':
        public_group = session.scalar(
            sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
        )
        if public_group is None:
            raise ValidationError(
                f"Public group {cfg['misc.public_group_name']} not found."
            )
        group_ids = {public_group.id}
    else:
        raise ValidationError(
            "Invalid group_ids parameter value. Must be a list of IDs "
            "(integers) or the string 'all'."
        )

    group_ids = list(group_ids)
    # always add the single user group
    if user.single_user_group.id not in group_ids:
        group_ids.append(user.single_user_group.id)

    return group_ids


def get_stream_ids(data, user, parent_session=None):
    if parent_session is None:
        session = DBSession()
    else:
        session = parent_session
    stream_ids = data.pop("stream_ids", [])
    if isinstance(stream_ids, (list, tuple)):
        try:
            stream_ids = {int(stream_id) for stream_id in stream_ids}
        except ValueError:
            raise ValidationError(
                "Invalid format for stream_ids parameter. Must be a list of integers."
            )
        streams = (
            session.scalars(Stream.select(user).where(Stream.id.in_(list(stream_ids))))
            .unique()
            .all()
        )
        available_stream_ids = {stream.id for stream in streams}
        diff_stream_ids = stream_ids - available_stream_ids
        if diff_stream_ids:
            raise ValidationError(
                f"Invalid stream IDs: {diff_stream_ids}. Available stream IDs: {available_stream_ids}"
            )
    else:
        raise ValidationError(
            "Invalid stream_ids parameter value. Must be a list of IDs (integers)."
        )

    return list(stream_ids)


def add_external_photometry(
    json, user, parent_session=None, duplicates="update", refresh=False
):
    """
    Posts external photometry to the database (as from
    another API)

    Parameters
    ----------
    json : dict
        Photometry to be posted. Schema follows that of
        schemas/PhotMagFlexible or schemas/PhotFluxFlexible.
    user : SingleUser
        User posting the photometry
    parent_session : sqlalchemy.orm.session.Session
        Session to use for the database transaction (optional)
    """

    if duplicates not in ["error", "ignore", "update"]:
        raise ValueError(
            "duplicates argument can only be one of: error, ignore, update"
        )

    if parent_session is None:
        session = DBSession()
    else:
        session = parent_session

    group_ids = get_group_ids(json, user, session)
    stream_ids = get_stream_ids(json, user, session)
    df, instrument_cache = standardize_photometry_data(json)

    if len(df.index) > MAX_NUMBER_ROWS:
        raise ValueError(
            f'Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. '
            'Please break up the data into smaller sets and try again'
        )

    username = user.username
    log(f'Pending request from {username} with {len(df.index)} rows')

    # This lock ensures that the Photometry table data are not modified in any way
    # between when the query for duplicate photometry is first executed and
    # when the insert statement with the new photometry is performed.
    # From the psql docs: This mode protects a table against concurrent
    # data changes, and is self-exclusive so that only one session can
    # hold it at a time.
    try:
        session.execute(
            sa.text(
                f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
            )
        )
        if duplicates in ["ignore", "update"]:
            values_table, condition = get_values_table_and_condition(df)

            new_photometry_query = session.execute(
                sa.select(values_table.c.pdidx)
                .outerjoin(Photometry, condition)
                .filter(Photometry.id.is_(None))
            )

            new_photometry_df_idxs = [g[0] for g in new_photometry_query]

            duplicated_photometry = (
                session.execute(
                    sa.select(values_table.c.pdidx, Photometry)
                    .join(Photometry, condition)
                    .options(joinedload(Photometry.groups))
                    .options(joinedload(Photometry.streams))
                )
                .unique()
                .all()
            )

            id_map = {}
            id_map_no_update_needed = {}
            for df_index, duplicate in duplicated_photometry:
                id_map[df_index] = duplicate.id

                if duplicates in ["ignore"]:
                    continue

                duplicate_group_ids = {g.id for g in duplicate.groups}
                duplicate_stream_ids = {s.id for s in duplicate.streams}

                updated = False
                # posting to new groups?
                if len(set(group_ids) - duplicate_group_ids) > 0:
                    # select old + new groups
                    group_ids_update = set(group_ids).union(duplicate_group_ids)
                    groups = (
                        session.execute(
                            sa.select(Group).filter(Group.id.in_(group_ids_update))
                        )
                        .scalars()
                        .all()
                    )
                    # update the corresponding photometry entry in the db
                    duplicate.groups = groups
                    log(
                        f'Adding groups {group_ids_update} to photometry {duplicate.id}'
                    )
                    updated = True

                # posting to new streams?
                if stream_ids:
                    # Add new stream_photometry rows if not already present
                    stream_ids_update = set(stream_ids) - duplicate_stream_ids
                    if len(stream_ids_update) > 0:
                        for id in stream_ids_update:
                            session.add(
                                StreamPhotometry(
                                    photometr_id=duplicate.id, stream_id=id
                                )
                            )
                        log(
                            f'Adding streams {stream_ids_update} to photometry {duplicate.id}'
                        )
                        updated = True

                if updated:
                    id_map_no_update_needed[df_index] = duplicate.id

            if duplicates in ["update"] and len(id_map_no_update_needed) > 0:
                log(
                    f'A total of (len{id_map_no_update_needed}) duplicate photometry points did not need to be updated: {id_map_no_update_needed.values()}'
                )
            # now safely drop the duplicates:
            new_photometry = df.loc[new_photometry_df_idxs]
            log(
                f'Inserting {len(new_photometry.index)} '
                f'(out of {len(df.index)}) new photometry points'
            )
        else:
            new_photometry = df.copy()

        ids, upload_id = [], None
        if len(new_photometry) > 0:
            ids, upload_id = insert_new_photometry_data(
                new_photometry,
                instrument_cache,
                group_ids,
                stream_ids,
                user,
                session,
                validate=True if duplicates in ["error"] else False,
                refresh=refresh,
            )

            if duplicates in ["ignore", "update"]:
                for (df_index, _), id in zip(new_photometry.iterrows(), ids):
                    id_map[df_index] = id

        # release the lock
        session.commit()

        if duplicates in ["ignore", "update"]:
            # get ids in the correct order
            ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]

        if len(new_photometry) > 0:
            log(
                f'Request from {username} with '
                f'{len(new_photometry.index)} rows complete with upload_id {upload_id}.'
            )
        else:
            log(
                f'Request from {username} with '
                f'{len(new_photometry.index)} rows complete with no new photometry.'
            )
        return ids, upload_id
    except Exception as e:
        session.rollback()
        log(f"Unable to post photometry: {e}")
        return None, None
    finally:
        if parent_session is None:
            session.close()


class PhotometryHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        f"""
        ---
        description: Upload photometry. Posting is capped at {MAX_NUMBER_ROWS} for database stability purposes.
        tags:
          - photometry
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/PhotMagFlexible"
                  - $ref: "#/components/schemas/PhotFluxFlexible"
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            ids:
                              type: array
                              items:
                                type: integer
                              description: List of new photometry IDs
                            upload_id:
                              type: string
                              description: |
                                Upload ID associated with all photometry points
                                added in request. Can be used to later delete all
                                points in a single request.
        """

        try:
            group_ids = get_group_ids(self.get_json(), self.associated_user_object)
        except ValidationError as e:
            return self.error(e.args[0])
        try:
            stream_ids = get_stream_ids(self.get_json(), self.associated_user_object)
        except ValidationError as e:
            return self.error(e.args[0])

        refresh = self.get_query_argument('refresh', default=False)

        try:
            df, instrument_cache = standardize_photometry_data(self.get_json())
        except (ValidationError, RuntimeError) as e:
            return self.error(e.args[0])

        if len(df.index) > MAX_NUMBER_ROWS:
            return self.error(
                f'Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. '
                'Please break up the data into smaller sets and try again'
            )

        obj_id = df['obj_id'].unique()[0]
        username = self.associated_user_object.username
        log(
            f'Pending request from {username} for object {obj_id} with {len(df.index)} rows'
        )

        # This lock ensures that the Photometry table data are not modified in any way
        # between when the query for duplicate photometry is first executed and
        # when the insert statement with the new photometry is performed.
        # From the psql docs: This mode protects a table against concurrent
        # data changes, and is self-exclusive so that only one session can
        # hold it at a time.
        with DBSession() as session:
            try:
                session.execute(
                    sa.text(
                        f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
                    )
                )
                ids, upload_id = insert_new_photometry_data(
                    df,
                    instrument_cache,
                    group_ids,
                    stream_ids,
                    self.associated_user_object,
                    session,
                    refresh=refresh,
                )
            except Exception:
                session.rollback()
                return self.error(traceback.format_exc())

            log(
                f'Request from {username} for object {obj_id} with {len(df.index)} rows complete with upload_id {upload_id}'
            )

            return self.success(data={'ids': ids, 'upload_id': upload_id})

    @permissions(['Upload data'])
    def put(self):
        """
        ---
        description: Update and/or upload photometry, resolving potential duplicates
        tags:
          - photometry
        parameters:
          - in: path
            name: refresh
            schema:
              type: boolean
            required: false
            description: |
              If true, triggers a refresh of the object's photometry on the web page,
              only for the users that have the object's source page open.
          - in: path
            name: duplicate_ignore_flux
            schema:
              type: boolean
            required: false
            description: |
              If true, will not use the flux/fluxerr of existing rows when looking for duplicates
              but only mjd, instrument_id, filter, and origin. Reserved to super admin users only,
              to avoid misuse and permanent data loss.
          - in: path
            name: overwrite_flux
            schema:
              type: boolean
            required: false
            description: |
              If true and duplicate_ignore_flux is also true, will update the flux/fluxerr of
              existing rows (duplicates) with the new values. Applies only to rows with
              an origin already specified. If existing duplicates have no origin, the update
              will be skipped.
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/PhotMagFlexible"
                  - $ref: "#/components/schemas/PhotFluxFlexible"
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            ids:
                              type: array
                              items:
                                type: integer
                              description: List of new photometry IDs
                            upload_id:
                              type: string
                              description: |
                                Upload ID associated with all photometry points
                                added in request. Can be used to later delete all
                                points in a single request.
        """

        try:
            group_ids = get_group_ids(self.get_json(), self.associated_user_object)
        except ValidationError as e:
            return self.error(e.args[0])

        try:
            stream_ids = get_stream_ids(self.get_json(), self.associated_user_object)
        except ValidationError as e:
            return self.error(e.args[0])

        refresh = self.get_query_argument('refresh', default=False)

        if refresh is not None and str(refresh).lower() in ['true', 't', '1']:
            refresh = True
        else:
            refresh = False

        try:
            df, instrument_cache = standardize_photometry_data(self.get_json())
        except ValidationError as e:
            return self.error(e.args[0])

        if len(df.index) > MAX_NUMBER_ROWS:
            return self.error(
                f'Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. '
                'Please break up the data into smaller sets and try again'
            )

        ignore_flux = self.get_query_argument('duplicate_ignore_flux', False)
        overwrite_flux = self.get_query_argument('overwrite_flux', False)

        if ignore_flux is not None and str(ignore_flux).lower() in ['true', 't', '1']:
            ignore_flux = True
        else:
            ignore_flux = False

        # if ignore_flux is True, verify that the current_user is a super admin
        if ignore_flux and not self.associated_user_object.is_admin:
            return self.error(
                'Ignoring flux/fluxerr when checking for duplicates is reserved to super admin users only'
            )

        if overwrite_flux is not None and str(overwrite_flux).lower() in [
            'true',
            't',
            '1',
        ]:
            overwrite_flux = True
        else:
            overwrite_flux = False

        obj_id = df['obj_id'].unique()[0]
        username = self.associated_user_object.username
        log(
            f'Pending request from {username} for object {obj_id} with {len(df.index)} rows'
        )

        values_table, condition = get_values_table_and_condition(df, ignore_flux)

        # This lock ensures that the Photometry table data are not modified
        # in any way between when the query for duplicate photometry is first
        # executed and when the insert statement with the new photometry is
        # performed. From the psql docs: This mode protects a table against
        # concurrent data changes, and is self-exclusive so that only one
        # session can hold it at a time.

        with DBSession() as session:
            try:
                session.execute(
                    sa.text(
                        f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
                    )
                )
                new_photometry_query = session.execute(
                    sa.select(values_table.c.pdidx)
                    .outerjoin(Photometry, condition)
                    .filter(Photometry.id.is_(None))
                )

                new_photometry_df_idxs = [g[0] for g in new_photometry_query]

                duplicated_photometry = (
                    session.execute(
                        sa.select(values_table.c.pdidx, Photometry)
                        .join(Photometry, condition)
                        .options(joinedload(Photometry.groups))
                        .options(joinedload(Photometry.streams))
                    )
                    .unique()
                    .all()
                )

                id_map = {}

                updated_ids = []
                updated_duplicate_values = []
                for df_index, duplicate in duplicated_photometry:
                    id_map[df_index] = duplicate.id
                    duplicate_group_ids = {g.id for g in duplicate.groups}
                    duplicate_stream_ids = {s.id for s in duplicate.streams}

                    # posting to new groups?
                    if len(set(group_ids) - duplicate_group_ids) > 0:
                        # select old + new groups
                        group_ids_update = set(group_ids).union(duplicate_group_ids)
                        groups = (
                            session.execute(
                                sa.select(Group).filter(Group.id.in_(group_ids_update))
                            )
                            .scalars()
                            .all()
                        )
                        # update the corresponding photometry entry in the db
                        duplicate.groups = groups
                        log(
                            f'Adding groups {group_ids_update} to photometry {duplicate.id}'
                        )

                    # posting to new streams?
                    if stream_ids:
                        # Add new stream_photometry rows if not already present
                        stream_ids_update = set(stream_ids) - duplicate_stream_ids
                        if len(stream_ids_update) > 0:
                            for id in stream_ids_update:
                                session.add(
                                    StreamPhotometry(
                                        photometr_id=duplicate.id, stream_id=id
                                    )
                                )
                            log(
                                f'Adding streams {stream_ids_update} to photometry {duplicate.id}'
                            )

                    # update duplicate's flux and fluxerr if we are ignoring flux deduplication
                    # and both the duplicate and the new datapoint have origins that are not None, '', 'nan', or 'null'
                    if (
                        "origin" in df.columns
                        and ignore_flux
                        and overwrite_flux
                        and str(duplicate.origin).strip().lower()
                        not in ['none', '', 'nan', 'null']
                        and str(df.loc[df_index]['origin']).strip().lower()
                        not in ['none', '', 'nan', 'null']
                    ):
                        # we might have more than one datapoint at a given: jd, instrument_id, filter, and origin
                        # that have different flux values (i.e, multiple duplicates not just one)
                        # because we have a unique index that includes flux and fluxerr, we can't update all the duplicates
                        # with the new flux values, as we would end up with more than one entry with the same columns in the database
                        # which will yield an error. So, we keep track of the duplicates we have already updated
                        # to avoid updating more than one row with the same values
                        duplicate_value = f"{duplicate.jd}_{duplicate.instrument_id}_{duplicate.filter}_{duplicate.origin}".encode()
                        if duplicate_value in updated_duplicate_values:
                            continue
                        duplicate.flux = df.loc[df_index]['standardized_flux']
                        duplicate.fluxerr = df.loc[df_index]['standardized_fluxerr']
                        duplicate.filter = df.loc[df_index]['filter']
                        duplicate.ra = df.loc[df_index]['ra']
                        duplicate.dec = df.loc[df_index]['dec']
                        duplicate.ra_unc = df.loc[df_index]['ra_unc']
                        duplicate.dec_unc = df.loc[df_index]['dec_unc']
                        duplicate.ref_flux = df.loc[df_index]['ref_standardized_flux']
                        duplicate.ref_fluxerr = df.loc[df_index][
                            'ref_standardized_fluxerr'
                        ]
                        duplicate.altdata = json.dumps(df.loc[df_index]['altdata'])
                        duplicate.modified = datetime.datetime.utcnow().isoformat()
                        updated_ids.append(duplicate.id)
                        updated_duplicate_values.append(duplicate_value)

                # now safely drop the duplicates:
                new_photometry = df.loc[new_photometry_df_idxs]
                log(
                    f'Inserting {len(new_photometry.index)} '
                    f'(out of {len(df.index)}) new photometry points'
                )
                if ignore_flux and overwrite_flux and len(updated_ids) > 0:
                    log(
                        f'A total of {len(updated_ids)} duplicate photometry points (by obj_id, instrument_id, mjd, origin only, ignoring flux/fluxerr) were updated as requested.'
                    )

                if len(new_photometry) > 0:
                    ids, upload_id = insert_new_photometry_data(
                        new_photometry,
                        instrument_cache,
                        group_ids,
                        stream_ids,
                        self.associated_user_object,
                        session,
                        validate=False,
                        refresh=refresh,
                    )

                    for (df_index, _), id in zip(new_photometry.iterrows(), ids):
                        id_map[df_index] = id

                # release the lock
                self.verify_and_commit()

                # get ids in the correct order
                ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]

                if len(new_photometry) > 0:
                    log(
                        f'Request from {username} for object {obj_id} with '
                        f'{len(new_photometry.index)} rows complete with upload_id {upload_id}.'
                    )
                else:
                    log(
                        f'Request from {username} for object {obj_id} with '
                        f'{len(new_photometry.index)} rows complete with no new photometry.'
                    )
                return self.success(data={'ids': ids})

            except Exception:
                session.rollback()
                return self.error(traceback.format_exc())

    @auth_or_token
    def get(self, photometry_id):
        # The full docstring/API spec is below as an f-string

        with self.Session() as session:
            phot = session.scalars(
                Photometry.select(session.user_or_token).where(
                    Photometry.id == photometry_id
                )
            ).first()

            if phot is None:
                return self.error(
                    f'Cannot find photometry point with ID: {photometry_id}.'
                )

            # get the desired output format
            format = self.get_query_argument('format', 'mag')
            outsys = self.get_query_argument('magsys', 'ab')
            output = serialize(phot, outsys, format)
            return self.success(data=output)

    @permissions(['Upload data'])
    def patch(self, photometry_id):
        """
        ---
        description: Update photometry
        tags:
          - photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: "#/components/schemas/PhotometryMag"
                  - $ref: "#/components/schemas/PhotometryFlux"
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            photometry_id = int(photometry_id)
        except ValueError:
            return self.error('Photometry id must be an int.')

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        stream_ids = data.pop("stream_ids", None)
        magsys = data.get('magsys', 'ab')

        refresh = self.get_query_argument('refresh', default=False)

        with self.Session() as session:
            photometry = session.scalars(
                Photometry.select(session.user_or_token, mode="update").where(
                    Photometry.id == photometry_id
                )
            ).first()

            if photometry is None:
                return self.error(
                    f'Cannot find photometry point with ID: {photometry_id}.'
                )

            original_user_data = copy.deepcopy(data)

            nan_if_none_keys = {'flux', 'fluxerr', 'mag', 'magerr'}
            for key in nan_if_none_keys:
                if key in data and data[key] is None:
                    data[key] = np.nan

            optional_keys = {'ra', 'dec', 'ra_unc', 'dec_unc', 'assignment_id'}
            for key in optional_keys:
                if key not in data:
                    data[key] = None

            try:
                phot = PhotometryFlux.load(data, partial=True)
            except ValidationError as e1:
                try:
                    phot = PhotometryMag.load(data, partial=True)
                except ValidationError as e2:
                    return self.error(
                        'Invalid input format: Tried to parse '
                        f'{data} as PhotometryFlux, got: '
                        f'"{e1.normalized_messages()}." Tried '
                        f'to parse {data} as PhotometryMag, got:'
                        f' "{e2.normalized_messages()}."'
                    )

            phot.original_user_data = original_user_data
            phot.id = photometry_id

            session.merge(phot)

            # Update groups, if relevant
            if group_ids is not None:
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()
                if not groups:
                    return self.error(
                        "Invalid group_ids field. Specify at least one valid group ID."
                    )
                accessible_group_ids = [
                    g.id for g in self.current_user.accessible_groups
                ]
                if not all([g.id in accessible_group_ids for g in groups]):
                    return self.error(
                        "Cannot upload photometry to groups you are not a member of."
                    )
                photometry.groups = groups

            # Update streams, if relevant
            if stream_ids is not None:
                streams = session.scalars(
                    Stream.select(session.user_or_token).where(
                        Stream.id.in_(stream_ids)
                    )
                ).all()

                if not streams:
                    return self.error(
                        "Invalid stream_ids field. Specify at least one valid stream ID."
                    )

                # Add new stream_photometry rows if not already present
                for stream in streams:
                    stream_photometry = session.scalars(
                        StreamPhotometry.select(session.user_or_token).where(
                            StreamPhotometry.stream_id == stream.id,
                            StreamPhotometry.photometr_id == photometry_id,
                        )
                    ).first()
                    if stream_photometry is None:
                        session.add(
                            StreamPhotometry(
                                photometr_id=photometry_id, stream_id=stream.id
                            )
                        )

            phot_stat = session.scalars(
                PhotStat.select(session.user_or_token, mode="update").where(
                    PhotStat.obj_id == photometry.obj_id
                )
            ).first()
            if phot_stat is None:
                phot_stat = PhotStat(obj_id=photometry.obj_id)

            all_phot = session.scalars(
                sa.select(Photometry).where(Photometry.obj_id == photometry.obj_id)
            ).all()
            phot_stat.full_update(all_phot)
            for phot in all_phot:
                session.expunge(phot)

            session.commit()

            if refresh:
                flow = Flow()
                internal_key = session.scalar(
                    sa.select(Obj.internal_key).where(Obj.id == photometry.obj_id)
                )
                flow.push(
                    '*',
                    'skyportal/REFRESH_SOURCE',
                    payload={'obj_key': internal_key},
                )

                flow.push(
                    '*',
                    'skyportal/FETCH_SOURCE_PHOTOMETRY',
                    payload={'obj_id': photometry.obj_id, 'magsys': magsys},
                )

            return self.success()

    @permissions(['Upload data'])
    def delete(self, photometry_id):
        """
        ---
        description: Delete photometry
        tags:
          - photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            photometry = session.scalars(
                Photometry.select(session.user_or_token, mode="delete").where(
                    Photometry.id == photometry_id
                )
            ).first()

            if photometry is None:
                return self.error(
                    f'Cannot find photometry point with ID: {photometry_id}.'
                )

            obj_id = photometry.obj_id

            session.delete(photometry)

            phot_stat = session.scalars(
                PhotStat.select(session.user_or_token, mode="update").where(
                    PhotStat.obj_id == photometry.obj_id
                )
            ).first()
            if phot_stat is not None:
                all_phot = session.scalars(
                    sa.select(Photometry).where(Photometry.obj_id == photometry.obj_id)
                ).all()
                phot_stat.full_update(all_phot)

            session.commit()

            self.push_all(
                action="skyportal/FETCH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )

            return self.success()


class ObjPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        individual_or_series = self.get_query_argument("individualOrSeries", "both")
        phase_fold_data = self.get_query_argument("phaseFoldData", False)
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        include_owner_info = self.get_query_argument('includeOwnerInfo', False)
        include_stream_info = self.get_query_argument('includeStreamInfo', False)
        include_validation_info = self.get_query_argument(
            'includeValidationInfo', False
        )
        include_annotation_info = self.get_query_argument(
            'includeAnnotationInfo', False
        )
        deduplicate_photometry = self.get_query_argument('deduplicatePhotometry', False)

        if str(include_owner_info).lower() in ['true', 't', '1']:
            include_owner_info = True
        else:
            include_owner_info = False

        if str(include_stream_info).lower() in ['true', 't', '1']:
            include_stream_info = True
        else:
            include_stream_info = False

        if str(include_validation_info).lower() in ['true', 't', '1']:
            include_validation_info = True
        else:
            include_validation_info = False

        if str(include_annotation_info).lower() in ['true', 't', '1']:
            include_annotation_info = True
        else:
            include_annotation_info = False

        with self.Session() as session:
            obj = session.scalars(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            ).first()
            if obj is None:
                return self.error(
                    f"Insufficient permissions for User {self.current_user.id} to read Obj {obj_id}",
                    status=403,
                )

            phot_data = []
            series_data = []
            if individual_or_series in ["individual", "both"]:
                options = [
                    joinedload(Photometry.instrument).load_only(Instrument.name),
                    joinedload(Photometry.groups).load_only(
                        Group.id, Group.name, Group.nickname, Group.single_user_group
                    ),
                ]
                if include_annotation_info:
                    options.append(joinedload(Photometry.annotations))
                if include_owner_info:
                    options.append(
                        joinedload(Photometry.owner).load_only(
                            User.id,
                            User.username,
                            User.first_name,
                            User.last_name,
                        )
                    )
                if include_stream_info:
                    options.append(
                        joinedload(Photometry.streams).load_only(
                            Stream.id,
                            Stream.name,
                        )
                    )

                stmt = (
                    Photometry.select(
                        session.user_or_token,
                        options=options,
                    )
                    .where(Photometry.obj_id == obj_id)
                    .distinct()
                )
                photometry = session.scalars(stmt).unique().all()

                phot_data = [
                    serialize(
                        phot,
                        outsys,
                        format,
                        annotations=include_annotation_info,
                        owner=include_owner_info,
                        stream=include_stream_info,
                        validation=include_validation_info,
                    )
                    for phot in photometry
                ]
                if deduplicate_photometry and len(phot_data) > 0:
                    df_phot = pd.DataFrame.from_records(phot_data)
                    # drop duplicate mjd/filter points, keeping most recent
                    phot_data = (
                        df_phot.sort_values(by="created_at", ascending=False)
                        .drop_duplicates(["mjd", "filter"])
                        .reset_index(drop=True)
                        .to_dict(orient='records')
                    )

            if individual_or_series in ["series", "both"]:
                series = (
                    session.scalars(
                        PhotometricSeries.select(session.user_or_token).where(
                            PhotometricSeries.obj_id == obj_id
                        )
                    )
                    .unique()
                    .all()
                )
                series_data = []
                for s in series:
                    series_data += s.get_data_with_extra_columns().to_dict(
                        orient='records'
                    )

            data = phot_data + series_data

            data.sort(key=lambda x: x['mjd'])

            if phase_fold_data:
                period, modified = None, arrow.Arrow(1, 1, 1)

                annotations = session.scalars(
                    Annotation.select(session.user_or_token).where(
                        Annotation.obj_id == obj_id
                    )
                ).all()
                period_str_options = ['period', 'Period', 'PERIOD']
                for an in annotations:
                    if not isinstance(an.data, dict):
                        continue
                    for period_str in period_str_options:
                        if period_str in an.data and arrow.get(an.modified) > modified:
                            period = an.data[period_str]
                            modified = arrow.get(an.modified)
                if period is None:
                    self.error(f'No period for object {obj_id}')
                for ii in range(len(data)):
                    data[ii]['phase'] = np.mod(data[ii]['mjd'], period) / period

            return self.success(data=data)

    @permissions(["Delete bulk photometry"])
    def delete(self, obj_id):
        """
        ---
        description: Delete object photometry
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            photometry_to_delete = session.scalars(
                Photometry.select(session.user_or_token, mode="delete").where(
                    Photometry.obj_id == obj_id
                )
            ).all()

            n = len(photometry_to_delete)
            if n == 0:
                return self.error('Invalid object id.')

            for phot in photometry_to_delete:
                session.delete(phot)

            stat = session.scalars(
                PhotStat.select(session.user_or_token, mode="update").where(
                    PhotStat.obj_id == obj_id
                )
            ).first()
            all_phot = session.scalars(
                sa.select(Photometry).where(Photometry.obj_id == obj_id)
            ).all()
            stat.full_update(all_phot)

            session.commit()
            return self.success(f"Deleted {n} photometry point(s) of {obj_id}.")


class BulkDeletePhotometryHandler(BaseHandler):
    @permissions(["Delete bulk photometry"])
    def delete(self, upload_id):
        """
        ---
        description: Delete bulk-uploaded photometry set
        tags:
          - photometry
        parameters:
          - in: path
            name: upload_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            photometry_to_delete = session.scalars(
                Photometry.select(session.user_or_token, mode="delete").where(
                    Photometry.upload_id == upload_id
                )
            ).all()

            n = len(photometry_to_delete)
            if n == 0:
                return self.error('Invalid bulk upload id.')

            for phot in photometry_to_delete:
                session.delete(phot)

            obj_ids = {phot.obj_id for phot in photometry_to_delete}
            for oid in obj_ids:
                stat = session.scalars(
                    PhotStat.select(session.user_or_token, mode="update").where(
                        PhotStat.obj_id == oid
                    )
                ).first()
                all_phot = session.scalars(
                    sa.select(Photometry).where(Photometry.obj_id == oid)
                ).all()
                stat.full_update(all_phot)

            session.commit()
            return self.success(f"Deleted {n} photometry point(s).")


class PhotometryRangeHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """Docstring appears below as an f-string."""

        json = self.get_json()
        magsys = self.get_query_argument('magsys', default='ab')

        if magsys not in ALLOWED_MAGSYSTEMS:
            return self.error('Invalid mag system.')

        format = self.get_query_argument('format', default='mag')
        if format not in ['mag', 'flux']:
            return self.error('Invalid output format.')

        with self.Session() as session:
            try:
                standardized = PhotometryRangeQuery.load(json)
            except ValidationError as e:
                return self.error(f'Invalid request body: {e.normalized_messages()}')

            instrument_ids = standardized['instrument_ids']
            min_date = standardized['min_date']
            max_date = standardized['max_date']

            gids = [g.id for g in self.current_user.accessible_groups]

            group_phot_subquery = (
                GroupPhotometry.select(session.user_or_token)
                .where(GroupPhotometry.group_id.in_(gids))
                .subquery()
            )
            query = Photometry.select(session.user_or_token)

            if instrument_ids is not None:
                query = query.where(Photometry.instrument_id.in_(instrument_ids))
            if min_date is not None:
                mjd = Time(min_date, format='datetime').mjd
                query = query.where(Photometry.mjd >= mjd)
            if max_date is not None:
                mjd = Time(max_date, format='datetime').mjd
                query = query.where(Photometry.mjd <= mjd)

            query = query.join(
                group_phot_subquery, Photometry.id == group_phot_subquery.c.photometr_id
            )

            output = [
                serialize(p, magsys, format)
                for p in session.scalars(query.distinct()).unique().all()
            ]
            return self.success(data=output)


class PhotometryOriginHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """
        ---
        description: Get all photometry origins
        tags:
          - photometry
        responses:
          200:
            content:
              application/json:
                schema: Success
          400:
            content:
              application/json:
                schema: Error
        """

        with self.Session() as session:
            origins = (
                session.scalars(sa.select(Photometry.origin).distinct()).unique().all()
            )
            return self.success(data=origins)


PhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve photometry
        tags:
          - photometry
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: integer
          - in: query
            name: format
            required: false
            description: >-
              Return the photometry in flux or magnitude space?
              If a value for this query parameter is not provided, the
              result will be returned in magnitude space.
            schema:
              type: string
              enum:
                - mag
                - flux
          - in: query
            name: magsys
            required: false
            description: >-
              The magnitude or zeropoint system of the output. (Default AB)
            schema:
              type: string
              enum: {list(ALLOWED_MAGSYSTEMS)}

        responses:
          200:
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: "#/components/schemas/SinglePhotometryFlux"
                    - $ref: "#/components/schemas/SinglePhotometryMag"
          400:
            content:
              application/json:
                schema: Error
        """

ObjPhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve all photometry associated with an Object
        tags:
          - photometry
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve photometry for
          - in: query
            name: format
            required: false
            description: >-
              Return the photometry in flux or magnitude space?
              If a value for this query parameter is not provided, the
              result will be returned in magnitude space.
            schema:
              type: string
              enum:
                - mag
                - flux
          - in: query
            name: magsys
            required: false
            description: >-
              The magnitude or zeropoint system of the output. (Default AB)
            schema:
              type: string
              enum: {list(ALLOWED_MAGSYSTEMS)}
          - in: query
            name: individualOrSeries
            nullable: true
            schema:
              type: string
              enum: [individual, series, both]
            description: >-
                Whether to return individual photometry points,
                photometric series, or both (Default).
          - in: query
            name: phaseFoldData
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to phase fold the light curve. Defaults to false.
          - in: query
            name: deduplicatePhotometry
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to deduplicate photometry. Defaults to false.
          - in: query
            name: includeOwnerInfo
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include photometry owner. Defaults to false.
          - in: query
            name: includeStreamInfo
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include photometry stream information. Defaults to false.
          - in: query
            name: includeValidationInfo
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to include photometry validation information. Defaults to false.
        responses:
          200:
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: "#/components/schemas/ArrayOfPhotometryFluxs"
                    - $ref: "#/components/schemas/ArrayOfPhotometryMags"
          400:
            content:
              application/json:
                schema: Error
        """

PhotometryRangeHandler.get.__doc__ = f"""
        ---
        description: Get photometry taken by specific instruments over a date range
        tags:
          - photometry
        parameters:
          - in: query
            name: format
            required: false
            description: >-
              Return the photometry in flux or magnitude space?
              If a value for this query parameter is not provided, the
              result will be returned in magnitude space.
            schema:
              type: string
              enum:
                - mag
                - flux
          - in: query
            name: magsys
            required: false
            description: >-
              The magnitude or zeropoint system of the output. (Default AB)
            schema:
              type: string
              enum: {list(ALLOWED_MAGSYSTEMS)}
        requestBody:
          content:
            application/json:
              schema:
                PhotometryRangeQuery
        responses:
          200:
            content:
              application/json:
                schema:
                  oneOf:
                    - $ref: "#/components/schemas/ArrayOfPhotometryFluxs"
                    - $ref: "#/components/schemas/ArrayOfPhotometryMags"
          400:
            content:
              application/json:
                schema: Error
        """

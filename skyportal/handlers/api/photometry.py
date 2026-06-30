import copy
import json
import traceback
import uuid
from collections import defaultdict
from io import StringIO

import arrow
import astropy.utils.data
import numpy as np
import pandas as pd
import sncosmo
import sqlalchemy as sa
from astropy.table import Table
from astropy.time import Time
from marshmallow.exceptions import ValidationError
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap, rgb2hex
from sncosmo.photdata import PhotometricData
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import joinedload, load_only

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ...enum_types import ALLOWED_BANDPASSES, ALLOWED_MAGSYSTEMS
from ...models import (
    PHOT_ZP,
    Annotation,
    Group,
    GroupPhotometry,
    Instrument,
    Obj,
    PhotometricSeries,
    Photometry,
    PhotStat,
    Stream,
    StreamPhotometry,
    SuperObj,
    User,
)
from ...models.schema import (
    PhotFluxFlexible,
    PhotMagFlexible,
    PhotometryFlux,
    PhotometryMag,
    PhotometryRangeQuery,
)
from ...utils.extinction import calculate_extinction, deredden_flux
from ...utils.naive_datetime import utcnow_naive
from ...utils.parse import str_to_bool
from ..base import BaseHandler, format_doc
from .photometry_validation import USE_PHOTOMETRY_VALIDATION

_, cfg = load_env()


log = make_log("api/photometry")

MAX_NUMBER_ROWS = 10000

# Above this many newly-inserted points for one object, recompute its PhotStat
# from the table (full_update) instead of incrementally adding each point — past
# this break-even the single recompute is cheaper than the per-point updates, and
# it bounds any floating-point drift in the running mean/RMS stats.
INCREMENTAL_PHOTSTAT_MAX = 50


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy scalar types.

    In numpy 2.x, numpy scalars (e.g., np.float64, np.int64) are no longer
    subclasses of Python float/int, so the default JSON encoder cannot
    serialize them. This encoder converts them to native Python types.
    """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def numpy_to_native(value):
    """Recursively convert numpy scalars and arrays inside ``value`` to
    native Python types. Passes through anything that's already native.

    In numpy 2.x, numpy scalars are no longer subclasses of Python built-in
    types, which can cause issues with JSON serialization and database
    adapters (e.g., psycopg2/3 rejecting np.float64 in JSONB payloads).

    Use this on a dict/list before handing it to ``pg_insert.values()`` for
    a JSONB column, instead of a ``json.loads(json.dumps(..., NumpyEncoder))``
    round-trip — same effect, no parse step.
    """
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {k: numpy_to_native(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [numpy_to_native(x) for x in value]
    return value


cmap_ir = cm.get_cmap("autumn")
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
            args["radius"] = radius
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
        bandcolor = "#4B0082"
    elif 1500 < wavelength <= 2100:  # uvw2
        bandcolor = "#6A5ACD"
    elif 2100 < wavelength <= 2400:  # uvm2
        bandcolor = "#9400D3"
    elif 2400 < wavelength <= 3000:  # uvw1
        bandcolor = "#FF00FF"
    elif 3000 < wavelength <= 4000:  # U, sdss u
        bandcolor = "#0000FF"
    elif 4000 < wavelength <= 4800:  # B, sdss g
        bandcolor = "#02d193"
    elif 4800 < wavelength <= 5000:  # ztfg
        bandcolor = "#008000"
    elif 5000 < wavelength <= 6000:  # V
        bandcolor = "#9ACD32"
    elif 6000 < wavelength <= 6400:  # sdssr
        bandcolor = "#ff6f00"
    elif 6400 < wavelength <= 6600:  # ztfr
        bandcolor = "#FF0000"
    elif 6400 < wavelength <= 7000:  # bessellr, atlaso
        bandcolor = "#c80000"
    elif 7000 < wavelength <= 8000:  # sdss i
        bandcolor = "#FFA500"
    elif 8000 < wavelength <= 9000:  # sdss z
        bandcolor = "#A52A2A"
    elif 9000 < wavelength <= 10000:  # PS1 y
        bandcolor = "#B8860B"
    elif 10000 < wavelength <= 13000:  # 2MASS J
        bandcolor = "#000000"
    elif 13000 < wavelength <= 17000:  # 2MASS H
        bandcolor = "#9370D8"
    elif 17000 < wavelength <= 1e5:  # mm to Radio
        bandcolor = rgb2hex(cmap_ir((5 - np.log10(wavelength)) / 0.77)[:3])
    elif 1e5 < wavelength <= 3e5:  # JWST miri and miri-tophat
        bandcolor = rgb2hex(cmap_deep_ir((5.48 - np.log10(wavelength)) / 0.48)[:3])
    else:
        log(
            f"{bandpass} with effective wavelength {wavelength} is out of range for color maps, using black"
        )
        bandcolor = "#000000"

    if format == "rgb":
        return hex2rgb(bandcolor[1:])
    elif format not in ["hex", "rgb"]:
        raise ValueError(f"Invalid color format: {format}")

    return bandcolor


def get_bandpasses_to_colors(bandpasses, colors_type="rgb"):
    # Build per-bandpass instead of with a dict comprehension so a single
    # broken sncosmo bandpass (occasionally produces an empty Bandpass on some
    # runners, which makes get_effective_wavelength's downstream `np.max([])`
    # raise) doesn't take out the whole mapping — and, by extension, app-import
    # at module load. Skip the bad bandpass with a log line and continue.
    out = {}
    for bandpass in bandpasses:
        try:
            out[bandpass] = get_color(bandpass, colors_type)
        except Exception as e:
            log(f"Skipping bandpass {bandpass} in color mapping due to error: {e}")
    return out


def get_filters_mapper(photometry):
    filters = {phot["filter"] for phot in photometry}
    return get_bandpasses_to_colors(filters)


def _safe_effective_wavelength(bandpass):
    try:
        return get_effective_wavelength(bandpass)
    except Exception as e:
        log(f"Skipping bandpass {bandpass} in wavelength mapping due to error: {e}")
        return None


# Build the import-time bandpass→color and bandpass→wavelength maps under a
# short astropy `remote_timeout`. Without this, an uncached bandpass whose CDN
# (typically SVO) is unreachable blocks for the default 10s; with ~20 such
# bandpasses across ALLOWED_BANDPASSES the cumulative wait pushes app startup
# past test_frontend's 180s health-check window. 2s is enough for fast hosts
# but stops dead hosts from holding up module import.
with astropy.utils.data.conf.set_temp("remote_timeout", 2):
    BANDPASSES_COLORS = get_bandpasses_to_colors(ALLOWED_BANDPASSES, "rgb")
    BANDPASSES_WAVELENGTHS = {
        bandpass: _safe_effective_wavelength(bandpass)
        for bandpass in ALLOWED_BANDPASSES
    }
BANDPASSES_WAVELENGTHS = {
    bp: w for bp, w in BANDPASSES_WAVELENGTHS.items() if w is not None
}


# this is a drop-in replacement for pandas pd.to_numeric
# which now does not offer the errors='ignore' option anymore
def to_numeric(col):
    """Convert a column to numeric, ignoring errors."""
    try:
        return pd.to_numeric(col)
    except (ValueError, TypeError):
        return col


def save_data_using_copy(rows, table, columns, session):
    # Prepare data
    output = StringIO()
    df = pd.DataFrame.from_records(rows)
    # Coerce missing non-numbers and numbers, respectively, for SQLAlchemy
    df.replace("NaN", "null", inplace=True)
    df.replace(np.nan, "NaN", inplace=True)

    df.to_csv(
        output,
        index=False,
        sep="\t",
        header=False,
        encoding="utf8",
        quotechar="'",
    )
    output.seek(0)

    # Insert data via psycopg v3's COPY API. psycopg2 had
    # `cursor.copy_from(file, table, sep, null, columns)`; psycopg3 expects a
    # full `COPY ... FROM STDIN` statement and a context-managed copy object
    # that you write rows (or raw bytes) into.
    # Use the provided session's connection so that the COPY runs within the
    # same database connection/transaction that holds any table-level locks.
    connection = session.connection().connection
    quoted_columns = ", ".join(f'"{c}"' for c in columns)
    copy_sql = (
        f"COPY {table} ({quoted_columns}) FROM STDIN "
        "WITH (FORMAT text, DELIMITER E'\\t', NULL '')"
    )
    with connection.cursor() as cursor:
        with cursor.copy(copy_sql) as copy:
            copy.write(output.getvalue())
    output.close()


def nan_to_none(value):
    """Coerce a value to None if it is nan, else return value."""
    try:
        return None if np.isnan(value) else value
    except TypeError:
        return value


def allscalar(d):
    return all(np.isscalar(v) or v is None for v in d.values())


# Columns required by _serialize_plot. The slim ObjPhotometry path applies
# load_only(*PHOT_PLOT_COLUMNS) so the rest of the Photometry row (altdata,
# ra/dec, snr, ref_*, etc.) stays deferred.
PHOT_PLOT_COLUMNS = (
    "id",
    "obj_id",
    "filter",
    "mjd",
    "origin",
    "flux",
    "fluxerr",
    "original_user_data",
)


def _serialize_plot(phot, outsys):
    """Slim serializer for the lightcurve-plotter payload.

    Returns only the columns the front-end plot consumes
    (id, obj_id, filter, mjd, origin, mag, magerr, limiting_mag) and skips
    every per-point auxiliary join (groups, annotations, instrument, owner,
    streams, validations) plus the ref/tot/extinction blocks. Magnitudes are
    converted into ``outsys`` the same way the full ``serialize`` does.
    """
    filter = phot.filter

    if filter == "swiftxrt":
        outsys = "ab"

    magsys_db = sncosmo.get_magsystem("ab")
    outsys_ms = sncosmo.get_magsystem(outsys)

    try:
        relzp_out = 2.5 * np.log10(outsys_ms.zpbandflux(filter))
        relzp_db = 2.5 * np.log10(magsys_db.zpbandflux(filter))
        db_correction = relzp_out - relzp_db
        corrected_db_zp = PHOT_ZP + db_correction

        if (
            phot.original_user_data is not None
            and "limiting_mag" in phot.original_user_data
        ):
            magsys_packet = sncosmo.get_magsystem(phot.original_user_data["magsys"])
            relzp_packet = 2.5 * np.log10(magsys_packet.zpbandflux(filter))
            packet_correction = relzp_out - relzp_packet
            maglimit = float(phot.original_user_data["limiting_mag"])
            maglimit_out = maglimit + packet_correction
        else:
            maglimit_out = -2.5 * np.log10(5 * phot.fluxerr) + corrected_db_zp

        return {
            "id": phot.id,
            "obj_id": phot.obj_id,
            "filter": filter,
            "mjd": phot.mjd,
            "origin": phot.origin,
            "mag": (phot.mag + db_correction)
            if nan_to_none(phot.mag) is not None
            else None,
            "magerr": phot.e_mag if nan_to_none(phot.e_mag) is not None else None,
            "limiting_mag": maglimit_out,
        }
    except ValueError as e:
        raise ValueError(
            f"Could not serialize phot_id: {phot.id} "
            f"on obj {phot.obj_id} with filter: {filter},  "
            f"due to error: {e}"
        )


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
    extinction_dict=None,
):
    if format == "plot":
        return _serialize_plot(phot, outsys)
    return_value = {
        "obj_id": phot.obj_id,
        "ra": phot.ra,
        "dec": phot.dec,
        "filter": phot.filter,
        "mjd": phot.mjd,
        "snr": phot.snr,
        "instrument_id": phot.instrument_id,
        "instrument_name": phot.instrument.name,
        "ra_unc": phot.ra_unc,
        "dec_unc": phot.dec_unc,
        "origin": phot.origin,
        "id": phot.id,
        "altdata": phot.altdata,
    }
    if created_at:
        return_value["created_at"] = phot.created_at
    if groups:
        return_value["groups"] = [
            {
                "id": group.id,
                "name": group.name,
                "nickname": group.nickname,
                "single_user_group": group.single_user_group,
            }
            for group in phot.groups
        ]
    if annotations:
        return_value["annotations"] = (
            [annotation.to_dict() for annotation in phot.annotations]
            if hasattr(phot, "annotations")
            else []
        )
    if owner:
        return_value["owner"] = {
            "id": phot.owner.id,
            "username": phot.owner.username,
            "first_name": phot.owner.first_name,
            "last_name": phot.owner.last_name,
        }
    if stream:
        return_value["streams"] = [
            {
                "id": stream.id,
                "name": stream.name,
            }
            for stream in phot.streams
        ]
    if USE_PHOTOMETRY_VALIDATION and validation:
        return_value["validations"] = [
            validation.to_dict() for validation in phot.validations
        ]

    if (
        phot.ref_flux is not None
        and not np.isnan(phot.ref_flux)
        and phot.ref_fluxerr is not None
        and not np.isnan(phot.ref_fluxerr)
    ):
        return_value["ref_flux"] = phot.ref_flux
        return_value["tot_flux"] = phot.tot_flux
        return_value["ref_fluxerr"] = phot.ref_fluxerr
        return_value["tot_fluxerr"] = phot.tot_fluxerr
        return_value["magref"] = phot.magref
        return_value["magtot"] = phot.magtot
        return_value["e_magref"] = phot.e_magref
        return_value["e_magtot"] = phot.e_magtot

    filter = phot.filter

    if filter == "swiftxrt":
        outsys = "ab"

    magsys_db = sncosmo.get_magsystem("ab")
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

        extinction_value = None
        flux_corr = None
        mag_corr = None
        if extinction_dict is not None:
            extinction_value = extinction_dict.get(phot.filter)
            if extinction_value is not None:
                flux_corr = deredden_flux(phot.flux, extinction=extinction_value)
                if nan_to_none(phot.mag) is not None:
                    mag_corr = phot.mag + db_correction - extinction_value

        if format not in ["mag", "flux", "both"]:
            raise ValueError(
                "Invalid output format specified. Must be one of "
                f"['flux', 'mag', 'both'], got '{format}'."
            )

        if format in ["mag", "both"]:
            if (
                phot.original_user_data is not None
                and "limiting_mag" in phot.original_user_data
            ):
                magsys_packet = sncosmo.get_magsystem(phot.original_user_data["magsys"])
                relzp_packet = 2.5 * np.log10(magsys_packet.zpbandflux(filter))
                packet_correction = relzp_out - relzp_packet
                maglimit = float(phot.original_user_data["limiting_mag"])
                maglimit_out = maglimit + packet_correction
            else:
                # calculate the limiting mag
                maglimit_out = -2.5 * np.log10(5 * phot.fluxerr) + corrected_db_zp

            mag_data = {
                "mag": phot.mag + db_correction
                if nan_to_none(phot.mag) is not None
                else None,
                "magerr": phot.e_mag if nan_to_none(phot.e_mag) is not None else None,
                "magsys": outsys.name,
                "limiting_mag": maglimit_out,
            }

            if extinction_dict is not None:
                mag_data.update(
                    {
                        "extinction": extinction_value,
                        "mag_corr": mag_corr,
                        "flux_corr": flux_corr,
                    }
                )

            return_value.update(mag_data)
            if (
                phot.ref_flux is not None
                and not np.isnan(phot.ref_flux)
                and phot.ref_fluxerr is not None
                and not np.isnan(phot.ref_fluxerr)
            ):
                return_value.update(
                    {
                        "magref": phot.magref + db_correction
                        if nan_to_none(phot.magref) is not None
                        else None,
                        "magtot": phot.magtot,
                        "e_magref": phot.e_magref,
                        "e_magtot": phot.e_magtot,
                    }
                )

        if format in ["flux", "both"]:
            flux_data = {
                "flux": nan_to_none(phot.flux),
                "magsys": outsys.name,
                "zp": corrected_db_zp,
                "fluxerr": phot.fluxerr,
            }

            if extinction_dict is not None:
                flux_data.update(
                    {
                        "extinction": extinction_value,
                        "flux_corr": nan_to_none(flux_corr),
                    }
                )

            return_value.update(flux_data)
            if (
                phot.ref_flux is not None
                and not np.isnan(phot.ref_flux)
                and phot.ref_fluxerr is not None
                and not np.isnan(phot.ref_fluxerr)
            ):
                return_value.update(
                    {
                        "ref_flux": phot.ref_flux,
                        "tot_flux": phot.tot_flux,
                        "ref_fluxerr": phot.ref_fluxerr,
                        "tot_fluxerr": phot.tot_fluxerr,
                    }
                )
    except ValueError as e:
        raise ValueError(
            f"Could not serialize phot_id: {phot.id} "
            f"on obj {phot.obj_id} with filter: {filter},  "
            f"due to error: {e}"
        )
    return return_value


async def standardize_photometry_data(data, session):
    if not isinstance(data, dict):
        raise ValidationError(
            f"Top level JSON must be an instance of `dict`, got {type(data)}."
        )

    max_num_elements = max(
        [
            len(data[key])
            for key in data
            if isinstance(data[key], list | tuple)
            and key not in ["group_ids", "stream_ids"]
        ]
        + [1]
    )

    if "altdata" in data and not data["altdata"]:
        del data["altdata"]
    if "altdata" in data:
        if isinstance(data["altdata"], dict):
            for key in data["altdata"]:
                if isinstance(data["altdata"][key], list):
                    if len(data["altdata"][key]) != max_num_elements:
                        if len(data["altdata"][key]) == 1:
                            data["altdata"][key] = (
                                data["altdata"][key] * max_num_elements
                            )
                        else:
                            raise ValueError(f"{key} in altdata incorrect length")
                elif max_num_elements > 1:
                    data["altdata"][key] = [data["altdata"][key]] * max_num_elements

            altdata = data.pop("altdata")
            try:
                df = pd.DataFrame(altdata)
            except ValueError:
                df = pd.DataFrame(altdata, index=[0])
            altdata = df.to_dict(orient="records")
        else:
            altdata = data.pop("altdata")
    else:
        altdata = None

    # quick validation - just to make sure things have the right fields
    # Try the schema the payload's keys point at first, falling back to the
    # other; only the failure path validates twice. (Flux posts — every plugin
    # and most flux API callers — always failed PhotMagFlexible before.)
    if "flux" in data and "mag" not in data:
        first, second = ("flux", PhotFluxFlexible), ("mag", PhotMagFlexible)
    else:
        first, second = ("mag", PhotMagFlexible), ("flux", PhotFluxFlexible)
    errors = {}
    kind = None
    for kind_name, schema in (first, second):
        try:
            data = schema.load(data)  # load() does not mutate on failure
            kind = kind_name
            break
        except ValidationError as e:
            errors[kind_name] = e
    if kind is None:
        raise ValidationError(
            "Invalid input format: Tried to parse data "
            f"in mag space, got: "
            f'"{errors["mag"].normalized_messages()}." Tried '
            f"to parse data in flux space, got:"
            f' "{errors["flux"].normalized_messages()}."'
        )

    data.pop("group_ids", None)
    data.pop("stream_ids", None)

    if allscalar(data):
        data = [data]

    try:
        if max_num_elements == 1:
            df = pd.DataFrame(data, index=[0])
        else:
            df = pd.DataFrame(data)
    except ValueError as e:
        raise ValidationError(
            f'Unable to coerce passed JSON to a series of packets. Error was: "{e}"'
        )

    if altdata is not None and len(altdata) > 0:
        for index, e in enumerate(altdata):
            altdata[index] = (
                {k: v for k, v in e.items() if v not in [None, ""]}
                if not all(v in [None, ""] for v in e.values())
                else None
            )
        df["altdata"] = altdata

    # `to_numeric` coerces numbers written as strings to numeric types
    #  (int, float)

    #  errors='ignore' means if something is actually an alphanumeric
    #  string, just leave it alone and dont error out

    #  apply is used to apply it to each column
    # (https://stackoverflow.com/questions/34844711/convert-entire-pandas
    # -dataframe-to-integers-in-pandas-0-17-0/34844867
    df = df.apply(to_numeric)

    # set origin to 'None' where it is None.
    if "origin" in df.columns:
        df["origin"] = df["origin"].astype(object)
        df.loc[df["origin"].isna(), "origin"] = "None"
    ref_phot_table = None

    if kind == "mag":
        # ensure that neither or both mag and magerr are null
        magnull = df["mag"].isna()
        magerrnull = df["magerr"].isna()
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
                if key != "standardized_flux":
                    packet[key] = nan_to_none(packet[key])

            raise ValidationError(
                f'Error parsing packet "{packet}": mag '
                f"and magerr must both be null, or both be "
                f"not null."
            )

        for field in ["mag", "magerr", "limiting_mag"]:
            try:
                infinite = np.isinf(df[field].values)
            except TypeError:
                raise ValidationError(
                    f"Some values in the {field} field are not numeric."
                )
            if any(infinite):
                first_offender = np.argwhere(infinite)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                # coerce nans to nones
                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": field {field} must be finite.'
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
                    f'Error parsing packet "{packet}": missing required field {field}.'
                )

        # convert the mags to fluxes
        # detections
        detflux = 10 ** (-0.4 * (df[magdet]["mag"] - PHOT_ZP))
        detfluxerr = df[magdet]["magerr"] / (2.5 / np.log(10)) * detflux

        # non-detections
        limmag_flux = 10 ** (-0.4 * (df[magnull]["limiting_mag"] - PHOT_ZP))
        ndetfluxerr = limmag_flux / df[magnull]["limiting_mag_nsigma"]

        # initialize flux to be none
        phot_table = Table.from_pandas(df[["mjd", "magsys", "filter"]])

        phot_table["zp"] = PHOT_ZP
        phot_table["flux"] = np.nan
        phot_table["fluxerr"] = np.nan
        phot_table["flux"][magdet] = detflux
        phot_table["fluxerr"][magdet] = detfluxerr
        phot_table["fluxerr"][magnull] = ndetfluxerr

        if "magref" in df.columns and "e_magref" in df.columns:
            ref_phot_table = Table.from_pandas(df[["mjd", "magsys", "filter"]])
            magref = df["magref"].fillna(np.nan)
            ref_phot_table["flux"] = 10 ** (-0.4 * (magref - PHOT_ZP))
            ref_phot_table["fluxerr"] = (
                df["e_magref"] / (2.5 / np.log(10)) * ref_phot_table["flux"]
            )
            ref_phot_table["zp"] = PHOT_ZP

    else:
        for field in PhotFluxFlexible.required_keys:
            missing = df[field].isna().values
            if any(missing):
                first_offender = np.argwhere(missing)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": missing required field {field}.'
                )

        for field in ["flux", "fluxerr"]:
            infinite = np.isinf(df[field].values)
            if any(infinite):
                first_offender = np.argwhere(infinite)[0, 0]
                packet = df.iloc[first_offender].to_dict()

                # coerce nans to nones
                for key in packet:
                    packet[key] = nan_to_none(packet[key])

                raise ValidationError(
                    f'Error parsing packet "{packet}": field {field} must be finite.'
                )

        phot_table = Table.from_pandas(df[["mjd", "magsys", "filter", "zp"]])
        phot_table["flux"] = df["flux"].fillna(np.nan)
        phot_table["fluxerr"] = df["fluxerr"].fillna(np.nan)

        if "ref_flux" in df.columns and "ref_fluxerr" in df.columns:
            ref_phot_table = Table.from_pandas(df[["mjd", "magsys", "filter"]])
            ref_phot_table["flux"] = df["ref_flux"].fillna(np.nan)
            ref_phot_table["fluxerr"] = df["ref_fluxerr"].fillna(np.nan)
            if "ref_zp" in df.columns:
                ref_phot_table["zp"] = df["ref_zp"].fillna(np.nan)
            else:
                ref_phot_table["zp"] = PHOT_ZP

    unknown_filters = set(phot_table["filter"]).difference(ALLOWED_BANDPASSES)
    if len(unknown_filters) > 0:
        raise ValidationError(
            f"Filter(s) {unknown_filters} is not allowed. "
            f"Allowed filters are: {ALLOWED_BANDPASSES}"
        )

    # convert to microjanskies, AB for DB storage as a vectorized operation
    pdata = PhotometricData(phot_table)
    try:
        standardized = pdata.normalized(zp=PHOT_ZP, zpsys="ab")
    except Exception as e:
        raise ValidationError(f"Error standardizing photometry data: {e}.")

    df["standardized_flux"] = standardized.flux
    df["standardized_fluxerr"] = standardized.fluxerr

    # convert the reference flux to microjanskies, AB
    if ref_phot_table:
        ref_pdata = PhotometricData(ref_phot_table)
        try:
            ref_standardized = ref_pdata.normalized(zp=PHOT_ZP, zpsys="ab")
        except Exception as e:
            raise ValidationError(
                f"Error standardizing reference photometry data: {e}."
            )
        df["ref_standardized_flux"] = ref_standardized.flux
        df["ref_standardized_fluxerr"] = ref_standardized.fluxerr

    # Fetch all referenced instruments/objects in one query each (instead of
    # one per unique id) so multi-instrument / multi-object batches stay at a
    # constant two round-trips. Keep the cache keyed by the original id values
    # and preserve the per-id "Invalid ... ID" validation errors.
    unique_iids = df["instrument_id"].unique()
    instruments_by_id = {
        inst.id: inst
        for inst in (
            await session.scalars(
                sa.select(Instrument).where(
                    Instrument.id.in_([int(iid) for iid in unique_iids])
                )
            )
        ).all()
    }
    instrument_cache = {}
    for iid in unique_iids:
        instrument = instruments_by_id.get(int(iid))
        if not instrument:
            raise ValidationError(f"Invalid instrument ID: {iid}")
        instrument_cache[iid] = instrument

    # convert the object IDs to str datatype
    df["obj_id"] = df["obj_id"].astype(str)

    unique_oids = [str(oid) for oid in df["obj_id"].unique()]
    existing_oids = set(
        (await session.scalars(sa.select(Obj.id).where(Obj.id.in_(unique_oids)))).all()
    )
    for oid in unique_oids:
        if oid not in existing_oids:
            raise ValidationError(f"Invalid object ID: {oid}")

    return df, instrument_cache


# Per-column coercions applied when building a dedup key from either an
# input param dict (raw user data, may contain numpy scalars) or a row
# returned from RETURNING (driver types). Columns not listed pass through
# unchanged. Keep aligned with Photometry.DEDUP_COLUMNS.
_DEDUP_COERCIONS = {
    "origin": str,
    "mjd": float,
    "fluxerr": float,
    "flux": float,
}


# Dedup columns ignoring flux/fluxerr (the PUT handler's duplicate_ignore_flux
# mode, super-admin only): a posted row may then match several stored rows.
_NOFLUX_DEDUP_COLUMNS = ("obj_id", "instrument_id", "origin", "mjd")


def _dedup_key(row, columns=Photometry.DEDUP_COLUMNS):
    """Normalize a row (dict or ORM result) into a deduplication key tuple over
    `columns` (defaults to Photometry.DEDUP_COLUMNS). Coercing types here lets us
    treat returned rows and input params interchangeably in the id_by_key map.
    """
    if isinstance(row, dict):
        get = row.get
    else:
        get = lambda k: getattr(row, k)  # noqa: E731
    key = []
    for c in columns:
        v = _DEDUP_COERCIONS.get(c, lambda x: x)(get(c))
        # upper limits store/return flux as NaN; NaN != NaN would break the
        # id_by_key lookup below, so canonicalize to a sentinel.
        if isinstance(v, float) and np.isnan(v):
            v = "__nan__"
        key.append(v)
    return tuple(key)


async def find_duplicate_photometry(session, df, ignore_flux=False):
    """Return ``[(df_index, Photometry), ...]`` for posted rows (a
    standardized photometry DataFrame) that duplicate existing photometry.

    Replaces a VALUES-table join on the dedup index — which PostgreSQL plans
    very poorly (~950ms for an 8k-row post even when nothing matches) — with an
    indexed ``obj_id IN (...)`` fetch plus Python dedup-key matching (~1.5ms when
    empty). With ``ignore_flux`` the key omits flux/fluxerr, so a posted row can
    match several stored rows; all are returned (mirrors the old join).
    """
    columns = _NOFLUX_DEDUP_COLUMNS if ignore_flux else Photometry.DEDUP_COLUMNS
    unique_oids = [str(o) for o in df["obj_id"].unique()]
    unique_iids = [int(i) for i in df["instrument_id"].unique()]
    # Bound the fetch to the posted epochs (mjd is in both dedup-key variants):
    # a duplicate can only exist at an mjd we are posting, so this avoids pulling
    # a whole lightcurve when appending a few points to a well-observed object.
    unique_mjds = [float(m) for m in df["mjd"].unique()]
    result = await session.execute(
        sa.select(Photometry)
        .where(
            Photometry.obj_id.in_(unique_oids),
            Photometry.instrument_id.in_(unique_iids),
            Photometry.mjd.in_(unique_mjds),
        )
        .options(joinedload(Photometry.groups))
        .options(joinedload(Photometry.streams))
    )
    existing_rows = result.unique().scalars().all()
    existing_by_key = defaultdict(list)
    for p in existing_rows:
        existing_by_key[_dedup_key(p, columns)].append(p)

    out = []
    matched = set()
    for row in df.itertuples():
        key = _dedup_key(
            {
                "obj_id": str(row.obj_id),
                "instrument_id": int(row.instrument_id),
                "origin": row.origin,
                "mjd": row.mjd,
                "fluxerr": row.standardized_fluxerr,
                "flux": row.standardized_flux,
            },
            columns,
        )
        for p in existing_by_key.get(key, ()):
            out.append((row.Index, p))
            matched.add(p.id)
    # Drop non-matched rows from the session so a later read-check / identity-map
    # work doesn't iterate them (they're only loaded to find dups).
    for p in existing_rows:
        if p.id not in matched:
            session.expunge(p)
    return out


async def bulk_upsert_photometry(session, params, duplicates, return_inserted=False):
    """Atomic INSERT … ON CONFLICT on the photometry deduplication index.

    Replaces the older "LOCK TABLE then check-then-insert" pattern. The lock
    used to be necessary because the duplicate-check and the insert were
    separate statements; with ON CONFLICT the conflict resolution happens
    inside the INSERT and PostgreSQL handles the serialization at row level
    via the unique index.

    Parameters
    ----------
    session: sqlalchemy.orm.Session
    params: list[dict]
        Photometry rows ready for INSERT (all columns present).
    duplicates: str
        - "error":  ON CONFLICT DO NOTHING. If any row conflicts with an
                    existing one, raises ValidationError listing the
                    duplicate keys (preserves the old validate=True behavior
                    visible to API clients).
        - "ignore": ON CONFLICT DO NOTHING. Returns existing rows' IDs so
                    the caller can wire up group/stream rows even for the
                    skipped photometry rows.
        - "update": ON CONFLICT DO UPDATE on the non-key columns. Atomic
                    upsert; the previous worker's row is overwritten with
                    the new values.

    Returns
    -------
    list[int]
        Photometry IDs in the same order as input params.
    """
    if not params:
        return []

    # Approach: ON CONFLICT DO UPDATE with a self-assignment (`id = id`) is a
    # no-op at the row level but tells PostgreSQL to emit the row in RETURNING.
    # For "update", we use the real non-key column set instead. For "error",
    # we use DO NOTHING — the missing rows in RETURNING ARE the conflicts,
    # and that's what we report.
    #
    # We pass params to session.execute() as an executemany list rather than
    # baking them into stmt.values(): SQLAlchemy then compiles a single-row
    # template ONCE (cached) and batches via insertmanyvalues, instead of
    # recompiling a fresh N-row VALUES statement on every call (the row count
    # varies per call, so .values(params) was a compile-cache miss every time
    # — ~half the wall time on large lightcurves). insertmanyvalues does NOT
    # preserve input order in RETURNING under ON CONFLICT, so the ignore/update
    # branch below maps ids back to params by dedup key, not by position.
    stmt = pg_insert(Photometry)
    if duplicates == "error":
        stmt = stmt.on_conflict_do_nothing(
            index_elements=list(Photometry.DEDUP_COLUMNS),
        )
    elif duplicates == "ignore":
        # No-op set: keep the existing row exactly as-is, but emit it in
        # RETURNING so we can read back its id.
        stmt = stmt.on_conflict_do_update(
            index_elements=list(Photometry.DEDUP_COLUMNS),
            set_={"id": Photometry.id},
        )
    elif duplicates == "update":
        non_key_cols = {col.name for col in Photometry.__table__.columns} - {
            *Photometry.DEDUP_COLUMNS,
            "id",
            "created_at",
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=list(Photometry.DEDUP_COLUMNS),
            set_={c: stmt.excluded[c] for c in non_key_cols},
        )
    else:
        raise ValueError(f"bulk_upsert_photometry: invalid duplicates={duplicates!r}")

    # (xmax = 0) distinguishes a freshly-INSERTED row from one the ON CONFLICT
    # UPDATED (a concurrent or pre-existing collision). Reliable here: our just-
    # inserted rows are uncommitted and invisible to other workers during the
    # statement, so nothing else can lock them and bump xmax. Used to feed only
    # genuinely-new points to the incremental PhotStat path (concurrency-safe).
    stmt = stmt.returning(
        Photometry.id,
        *(getattr(Photometry, c) for c in Photometry.DEDUP_COLUMNS),
        sa.literal_column("(xmax = 0)").label("inserted"),
    )
    result = await session.execute(stmt, params)
    returned = result.all()

    if duplicates == "error":
        # Sparse RETURNING — rows missing from it conflicted with existing.
        if len(returned) < len(params):
            returned_keys = {_dedup_key(r) for r in returned}
            missing = [
                _dedup_key(p) for p in params if _dedup_key(p) not in returned_keys
            ]
            raise ValidationError(
                f"The following photometry already exists in the database "
                f"(deduplication keys: obj_id, instrument_id, origin, mjd, "
                f"fluxerr, flux): {missing}"
            )
        # DO NOTHING returns only inserted rows, so every returned row is new.
        ids = [r.id for r in returned]
        if return_inserted:
            return ids, {_dedup_key(r) for r in returned}
        return ids

    # ignore/update: one RETURNING row per input row, but insertmanyvalues does
    # not preserve input order under ON CONFLICT, so map back by dedup key.
    id_by_key = {_dedup_key(r): r.id for r in returned}
    ids = [id_by_key[_dedup_key(p)] for p in params]
    if return_inserted:
        inserted_keys = {_dedup_key(r) for r in returned if r.inserted}
        return ids, inserted_keys
    return ids


async def insert_new_photometry_data(
    df,
    instrument_cache,
    group_ids,
    stream_ids,
    user,
    session,
    validate=True,
    refresh=False,
    duplicates=None,
):
    # validate=True ⇒ ON CONFLICT DO NOTHING + raise if any row conflicted
    # (preserves the user-visible "duplicates already exist" error path).
    # validate=False ⇒ ON CONFLICT DO NOTHING but silently return existing IDs
    # (the PUT upsert path's "new rows" branch where the pre-check already ran).
    if duplicates is None:
        duplicates = "error" if validate else "ignore"

    df = df.where(pd.notnull(df), None)
    df.loc[df["standardized_flux"].isna(), "standardized_flux"] = np.nan

    rows = df.to_dict("records")
    upload_id = str(uuid.uuid4())

    params = []
    for packet in rows:
        if (
            instrument_cache[packet["instrument_id"]].type == "imager"
            and packet["filter"]
            not in instrument_cache[packet["instrument_id"]].filters
        ):
            instrument = instrument_cache[packet["instrument_id"]]
            raise ValidationError(
                f"Instrument {instrument.name} has no filter {packet['filter']}."
            )

        flux = packet.pop("standardized_flux")
        fluxerr = packet.pop("standardized_fluxerr")

        # reduce the DB size by ~2x
        keys = ["limiting_mag", "magsys", "limiting_mag_nsigma"]
        original_user_data = {key: packet[key] for key in keys if key in packet}
        if original_user_data == {}:
            original_user_data = None

        utcnow = utcnow_naive()
        # original_user_data and altdata are JSONB columns; with pg_insert.values()
        # SQLAlchemy serializes Python dicts via the column type, so we pass
        # the raw structures (None or dict). The old COPY path needed
        # json.dumps() strings because COPY's text protocol interprets them
        # as JSON literals on the wire. Also normalize NaN→None (pandas leaks
        # NaN for missing cells in object columns, and JSONB rejects NaN).
        altdata_val = packet.get("altdata")
        if isinstance(altdata_val, float) and np.isnan(altdata_val):
            altdata_val = None
        phot = {
            "original_user_data": numpy_to_native(original_user_data),
            "upload_id": upload_id,
            "flux": flux,
            "fluxerr": fluxerr,
            "obj_id": packet["obj_id"],
            "altdata": numpy_to_native(altdata_val),
            "instrument_id": packet["instrument_id"],
            "ra_unc": packet["ra_unc"],
            "dec_unc": packet["dec_unc"],
            "mjd": packet["mjd"],
            "filter": packet["filter"],
            "ra": packet["ra"],
            "dec": packet["dec"],
            "origin": packet["origin"],
            "owner_id": user.id,
            "created_at": utcnow,
            "modified": utcnow,
        }

        if "ref_standardized_flux" in packet:
            phot["ref_flux"] = packet.pop("ref_standardized_flux")
            phot["ref_fluxerr"] = packet.pop("ref_standardized_fluxerr")
        else:
            phot["ref_flux"] = None
            phot["ref_fluxerr"] = None

        params.append(phot)

    # Atomic upsert via INSERT ... ON CONFLICT on the deduplication index.
    # Returns IDs in the same order as params; raises ValidationError for
    # duplicates="error" if any row conflicted with an existing one.
    # inserted_keys = dedup keys of rows WE actually inserted (not concurrently/
    # pre-existing collisions) — feeds the incremental PhotStat path safely.
    ids, inserted_keys = await bulk_upsert_photometry(
        session, params, duplicates=duplicates, return_inserted=True
    )
    # Stitch the returned IDs back onto each param so we can build join rows.
    for packet, pid in zip(params, ids):
        packet["id"] = pid
        packet["_inserted"] = _dedup_key(packet) in inserted_keys

    # group_photometry and stream_photometry both have unique indexes on the
    # (group_id, photometr_id) and (stream_id, photometr_id) pairs respectively,
    # so concurrent workers re-inserting the same association must use
    # ON CONFLICT DO NOTHING to avoid IntegrityError.
    group_photometry_params = [
        {
            "photometr_id": packet["id"],
            "group_id": gid,
            "created_at": packet["created_at"],
            "modified": packet["modified"],
        }
        for packet in params
        for gid in group_ids
    ]
    if group_photometry_params:
        gp_stmt = pg_insert(GroupPhotometry).on_conflict_do_nothing(
            index_elements=["group_id", "photometr_id"]
        )
        await session.execute(gp_stmt, group_photometry_params)

    stream_photometry_params = [
        {
            "photometr_id": packet["id"],
            "stream_id": sid,
            "created_at": packet["created_at"],
            "modified": packet["modified"],
        }
        for packet in params
        for sid in stream_ids
    ]
    if stream_photometry_params:
        sp_stmt = pg_insert(StreamPhotometry).on_conflict_do_nothing(
            index_elements=["stream_id", "photometr_id"]
        )
        await session.execute(sp_stmt, stream_photometry_params)

    # PhotStat update. params may span MULTIPLE objs (bulk cross-object
    # posting); do the work in 3 bulk statements instead of 3-per-obj:
    #   1. one INSERT … ON CONFLICT DO NOTHING RETURNING obj_id — ensures a
    #      PhotStat row per obj; the returned obj_ids are the freshly-created
    #      ones (a fresh row has never been full_update'd, so it must take the
    #      full_update path below — matches the old "if phot_stat is None").
    #   2. one SELECT … FOR UPDATE over all obj_ids — row locks for the
    #      read-modify-write.
    #   3. one SELECT of all full_update objs' photometry, grouped in Python.
    # Initial PhotStat values mirror PhotStat.__init__ — raw pg_insert bypasses
    # the ORM __init__ that initializes the nullable JSONB dict/list columns.
    #
    # Per obj, take the incremental path (add only the points WE inserted, via
    # add_photometry_point — O(new points), no lightcurve re-read) when the
    # PhotStat already existed and few points were actually inserted; otherwise
    # full_update. `_inserted` (from RETURNING xmax=0) marks rows OUR insert
    # created, not a pre-existing/concurrent collision, so under the per-obj
    # FOR UPDATE lock each of several writers increments exactly its own rows
    # once — no double-count. Loaded photometry is expunged afterward.
    params_by_obj = {}
    for packet in params:
        params_by_obj.setdefault(packet["obj_id"], []).append(packet)
    phot_obj_ids = list(params_by_obj)

    _photstat_init = {
        "num_obs_per_filter": {},
        "num_det_per_filter": {},
        "predetection_mjds": [],
        "mean_mag_per_filter": {},
        "mean_color": {},
        "peak_mjd_per_filter": {},
        "peak_mag_per_filter": {},
        "faintest_mag_per_filter": {},
        "deepest_limit_per_filter": {},
        "mag_rms_per_filter": {},
    }
    newly_created_obj_ids = set(
        (
            await session.scalars(
                pg_insert(PhotStat)
                .on_conflict_do_nothing(index_elements=["obj_id"])
                .returning(PhotStat.obj_id),
                [{"obj_id": oid, **_photstat_init} for oid in phot_obj_ids],
            )
        ).all()
    )
    phot_stat_by_obj = {
        ps.obj_id: ps
        for ps in (
            await session.scalars(
                sa.select(PhotStat)
                .where(PhotStat.obj_id.in_(phot_obj_ids))
                .with_for_update()
            )
        ).all()
    }

    full_update_obj_ids = []
    for obj_id in phot_obj_ids:
        inserted_params = [p for p in params_by_obj[obj_id] if p.get("_inserted")]
        if (
            obj_id not in newly_created_obj_ids
            and len(inserted_params) <= INCREMENTAL_PHOTSTAT_MAX
        ):
            for packet in inserted_params:
                phot_stat_by_obj[obj_id].add_photometry_point(packet)
        else:
            full_update_obj_ids.append(obj_id)

    if full_update_obj_ids:
        all_phot = (
            await session.scalars(
                sa.select(Photometry)
                .where(Photometry.obj_id.in_(full_update_obj_ids))
                .options(
                    load_only(
                        Photometry.obj_id,
                        Photometry.filter,
                        Photometry.mjd,
                        Photometry.flux,
                        Photometry.fluxerr,
                        Photometry.origin,
                        Photometry.original_user_data,
                    )
                )
            )
        ).all()
        phot_by_obj = {}
        for p in all_phot:
            phot_by_obj.setdefault(p.obj_id, []).append(p)
        for obj_id in full_update_obj_ids:
            phot_stat_by_obj[obj_id].full_update(phot_by_obj.get(obj_id, []))
        for p in all_phot:
            session.expunge(p)
    await session.commit()

    if refresh:
        flow = Flow()
        # grab the list of unique obj_ids
        obj_ids = df["obj_id"].unique()
        for obj_id in obj_ids:
            internal_key = await session.scalar(
                sa.select(Obj.internal_key).where(Obj.id == obj_id)
            )
            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE",
                payload={"obj_key": internal_key},
            )

            flow.push(
                "*",
                "skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )

    return ids, upload_id


async def get_group_ids(data, user, session):
    """Resolve and validate the group_ids in a photometry-post payload.

    `session` is an AsyncSession. `user.single_user_group` would be a lazy
    relationship load under async, which raises MissingGreenlet — we look the
    single-user-group id up via an explicit query instead.
    """
    group_ids = data.pop("group_ids", [])
    if isinstance(group_ids, list | tuple):
        try:
            group_ids = {int(group_id) for group_id in group_ids}
        except ValueError:
            raise ValidationError(
                "Invalid format for group_ids parameter. Must be a list of integers."
            )
        groups_result = await session.scalars(
            sa.select(Group).where(Group.id.in_(list(group_ids)))
        )
        groups = groups_result.unique().all()
        available_group_ids = {group.id for group in groups}
        diff_group_ids = group_ids - available_group_ids
        if diff_group_ids:
            raise ValidationError(
                f"Invalid group IDs: {diff_group_ids}. Available group IDs: {available_group_ids}"
            )
    elif group_ids == "all":
        public_group = await session.scalar(
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
    single_user_group_id = await session.scalar(
        sa.select(Group.id).where(
            Group.single_user_group.is_(True), Group.users.any(id=user.id)
        )
    )
    if single_user_group_id is not None and single_user_group_id not in group_ids:
        group_ids.append(single_user_group_id)

    return group_ids


async def get_stream_ids(data, user, session):
    """Resolve and validate stream_ids in a photometry-post payload.
    `session` is an AsyncSession.
    """
    stream_ids = data.pop("stream_ids", [])
    if isinstance(stream_ids, list | tuple):
        try:
            stream_ids = {int(stream_id) for stream_id in stream_ids}
        except ValueError:
            raise ValidationError(
                "Invalid format for stream_ids parameter. Must be a list of integers."
            )
        streams_result = await session.scalars(
            Stream.select(user).where(Stream.id.in_(list(stream_ids)))
        )
        streams = streams_result.unique().all()
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


async def add_external_photometry(
    json, user, session, duplicates="update", refresh=False
):
    """Post external photometry to the database (e.g. from a facility API
    or the TNS retrieval worker).

    Parameters
    ----------
    json : dict
        Photometry payload following PhotMagFlexible or PhotFluxFlexible.
    user : User
        User on whose behalf the photometry is being posted.
    session : AsyncSession
        Required. The caller owns the session lifecycle (open + close + commit).
    duplicates : {"error", "ignore", "update"}
        How to treat rows that conflict on the deduplication index.
    refresh : bool
        Whether to push REFRESH actions over the websocket after the insert.
    """
    if duplicates not in ["error", "ignore", "update"]:
        raise ValueError(
            "duplicates argument can only be one of: error, ignore, update"
        )

    group_ids = await get_group_ids(json, user, session)
    stream_ids = await get_stream_ids(json, user, session)
    df, instrument_cache = await standardize_photometry_data(json, session)

    if len(df.index) > MAX_NUMBER_ROWS:
        raise ValueError(
            f"Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. "
            "Please break up the data into smaller sets and try again"
        )

    username = user.username
    log(f"Pending request from {username} with {len(df.index)} rows")

    try:
        if duplicates in ["ignore", "update"]:
            duplicated_photometry = await find_duplicate_photometry(session, df)
            duplicated_photometry_pdidx = {g[0] for g in duplicated_photometry}
            if len(duplicated_photometry_pdidx) > 0:
                new_photometry_df_idxs = [
                    i for i in list(df.index) if i not in duplicated_photometry_pdidx
                ]
            else:
                new_photometry_df_idxs = list(df.index)

            id_map = {}
            id_map_no_update_needed = {}
            for df_index, duplicate in duplicated_photometry:
                id_map[df_index] = duplicate.id

                if duplicates in ["ignore"]:
                    continue

                duplicate_group_ids = {g.id for g in duplicate.groups}
                duplicate_stream_ids = {s.id for s in duplicate.streams}

                updated = False
                # posting to new groups? Insert with ON CONFLICT DO NOTHING
                # rather than assigning the ORM relationship — concurrent
                # workers race on the (group_id, photometr_id) unique index.
                new_group_ids = set(group_ids) - duplicate_group_ids
                if len(new_group_ids) > 0:
                    now = utcnow_naive()
                    gp_stmt = pg_insert(GroupPhotometry).values(
                        [
                            {
                                "photometr_id": duplicate.id,
                                "group_id": gid,
                                "created_at": now,
                                "modified": now,
                            }
                            for gid in new_group_ids
                        ]
                    )
                    await session.execute(
                        gp_stmt.on_conflict_do_nothing(
                            index_elements=["group_id", "photometr_id"]
                        )
                    )
                    log(f"Adding groups {new_group_ids} to photometry {duplicate.id}")
                    updated = True

                # posting to new streams? Same ON CONFLICT handling.
                if stream_ids:
                    stream_ids_update = set(stream_ids) - duplicate_stream_ids
                    if len(stream_ids_update) > 0:
                        now = utcnow_naive()
                        sp_stmt = pg_insert(StreamPhotometry).values(
                            [
                                {
                                    "photometr_id": duplicate.id,
                                    "stream_id": sid,
                                    "created_at": now,
                                    "modified": now,
                                }
                                for sid in stream_ids_update
                            ]
                        )
                        await session.execute(
                            sp_stmt.on_conflict_do_nothing(
                                index_elements=["stream_id", "photometr_id"]
                            )
                        )
                        log(
                            f"Adding streams {stream_ids_update} to photometry {duplicate.id}"
                        )
                        updated = True

                if updated:
                    id_map_no_update_needed[df_index] = duplicate.id

            if duplicates in ["update"] and len(id_map_no_update_needed) > 0:
                log(
                    f"A total of ({len(id_map_no_update_needed)}) duplicate photometry points did not need to be updated: {id_map_no_update_needed.values()}"
                )
            new_photometry = df.loc[new_photometry_df_idxs]
            log(
                f"Inserting {len(new_photometry.index)} "
                f"(out of {len(df.index)}) new photometry points"
            )
        else:
            new_photometry = df.copy()

        ids, upload_id = [], None
        if len(new_photometry) > 0:
            ids, upload_id = await insert_new_photometry_data(
                new_photometry,
                instrument_cache,
                group_ids,
                stream_ids,
                user,
                session,
                validate=duplicates in ["error"],
                refresh=refresh,
            )

            if duplicates in ["ignore", "update"]:
                for (df_index, _), id in zip(new_photometry.iterrows(), ids):
                    id_map[df_index] = id

        await session.commit()

        if duplicates in ["ignore", "update"]:
            ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]

        if len(new_photometry) > 0:
            log(
                f"Request from {username} with "
                f"{len(new_photometry.index)} rows complete with upload_id {upload_id}."
            )
        else:
            log(
                f"Request from {username} with "
                f"{len(new_photometry.index)} rows complete with no new photometry."
            )
        return ids, upload_id
    except Exception as e:
        await session.rollback()
        log(f"Unable to post photometry: {e}")
        return None, None


async def commit_external_photometry(data, user_id):
    """Sync-to-async bridge for ``add_external_photometry``.

    Opens its own ``async_plain_session_factory()`` session, re-loads the
    User by ID inside that session, calls ``add_external_photometry``, and
    returns the inserted IDs. Intended to be invoked from sync contexts
    (executor-bound workers, top-level service scripts) via
    ``asyncio.run(commit_external_photometry(data, user.id))``.

    Parameters
    ----------
    data : dict
        Same payload shape that ``add_external_photometry`` expects.
    user_id : int
        ID of the user the photometry should be attributed to. The user
        is re-loaded inside the new async session so callers can pass
        only the id.

    Returns
    -------
    ids : list[int] or None
        The IDs returned by ``add_external_photometry``.
    """
    from baselayer.app import models as baselayer_models

    async with baselayer_models.async_plain_session_factory() as async_session:
        user = await async_session.get(User, user_id)
        ids, _ = await add_external_photometry(data, user, async_session)
        return ids


class PhotometryHandler(BaseHandler):
    @permissions(["Upload data"])
    @format_doc(MAX_NUMBER_ROWS=MAX_NUMBER_ROWS)
    async def post(self):
        """
        ---
        summary: Upload photometry
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
        refresh = self.get_query_argument("refresh", default=False)
        refresh = str_to_bool(refresh, default=False)

        async with self.AsyncSession() as session:
            try:
                group_ids = await get_group_ids(
                    self.get_json(), self.associated_user_object, session
                )
            except ValidationError as e:
                return self.error(e.args[0])
            try:
                stream_ids = await get_stream_ids(
                    self.get_json(), self.associated_user_object, session
                )
            except ValidationError as e:
                return self.error(e.args[0])

            try:
                df, instrument_cache = await standardize_photometry_data(
                    self.get_json(), session
                )
            except (ValidationError, RuntimeError) as e:
                return self.error(e.args[0])

            if len(df.index) > MAX_NUMBER_ROWS:
                return self.error(
                    f"Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. "
                    "Please break up the data into smaller sets and try again"
                )

            obj_id = df["obj_id"].unique()[0]
            username = self.associated_user_object.username
            log(
                f"Pending request from {username} for object {obj_id} with {len(df.index)} rows"
            )

            try:
                ids, upload_id = await insert_new_photometry_data(
                    df,
                    instrument_cache,
                    group_ids,
                    stream_ids,
                    self.associated_user_object,
                    session,
                    refresh=refresh,
                )
            except Exception as e:
                await session.rollback()
                if "The following photometry already exists in the database:" in str(e):
                    return self.error(str(e))
                return self.error(traceback.format_exc())

            log(
                f"Request from {username} for object {obj_id} with {len(df.index)} rows complete with upload_id {upload_id}"
            )

            return self.success(data={"ids": ids, "upload_id": upload_id})

    @permissions(["Upload data"])
    async def put(self):
        """
        ---
        summary: Update and/or upload photometry
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
        refresh = self.get_query_argument("refresh", default=False)
        refresh = str_to_bool(refresh, default=False)

        overwrite_flux = self.get_query_argument("overwrite_flux", False)
        overwrite_flux = str_to_bool(overwrite_flux, default=False)

        ignore_flux = self.get_query_argument("duplicate_ignore_flux", False)
        ignore_flux = str_to_bool(ignore_flux, default=False)

        # if ignore_flux is True, verify that the current_user is a super admin
        if ignore_flux and not self.associated_user_object.is_admin:
            return self.error(
                "Ignoring flux/fluxerr when checking for duplicates is reserved to super admin users only"
            )

        async with self.AsyncSession() as session:
            try:
                group_ids = await get_group_ids(
                    self.get_json(), self.associated_user_object, session
                )
            except ValidationError as e:
                return self.error(e.args[0])
            try:
                stream_ids = await get_stream_ids(
                    self.get_json(), self.associated_user_object, session
                )
            except ValidationError as e:
                return self.error(e.args[0])
            try:
                df, instrument_cache = await standardize_photometry_data(
                    self.get_json(), session
                )
            except ValidationError as e:
                return self.error(e.args[0])

            if len(df.index) > MAX_NUMBER_ROWS:
                return self.error(
                    f"Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. "
                    "Please break up the data into smaller sets and try again"
                )

            obj_id = df["obj_id"].unique()[0]
            username = self.associated_user_object.username
            log(
                f"Pending request from {username} for object {obj_id} with {len(df.index)} rows"
            )

            try:
                # indexed obj_id IN fetch + Python matching (replaces a slow
                # VALUES-table join on the dedup index — see find_duplicate_photometry)
                duplicated_photometry = await find_duplicate_photometry(
                    session, df, ignore_flux=ignore_flux
                )

                duplicated_photometry_pdidx = {g[0] for g in duplicated_photometry}
                if len(duplicated_photometry_pdidx) > 0:
                    new_photometry_df_idxs = [
                        i
                        for i in list(df.index)
                        if i not in duplicated_photometry_pdidx
                    ]
                else:
                    new_photometry_df_idxs = list(df.index)

                id_map = {}

                updated_ids = []
                updated_duplicate_values = []
                for df_index, duplicate in duplicated_photometry:
                    id_map[df_index] = duplicate.id
                    duplicate_group_ids = {g.id for g in duplicate.groups}
                    duplicate_stream_ids = {s.id for s in duplicate.streams}

                    # posting to new groups? Insert the new associations with
                    # ON CONFLICT DO NOTHING rather than assigning the ORM
                    # relationship — concurrent workers race on the
                    # (group_id, photometr_id) unique index otherwise.
                    new_group_ids = set(group_ids) - duplicate_group_ids
                    if len(new_group_ids) > 0:
                        now = utcnow_naive()
                        gp_stmt = pg_insert(GroupPhotometry).values(
                            [
                                {
                                    "photometr_id": duplicate.id,
                                    "group_id": gid,
                                    "created_at": now,
                                    "modified": now,
                                }
                                for gid in new_group_ids
                            ]
                        )
                        await session.execute(
                            gp_stmt.on_conflict_do_nothing(
                                index_elements=["group_id", "photometr_id"]
                            )
                        )
                        log(
                            f"Adding groups {new_group_ids} to photometry {duplicate.id}"
                        )

                    # posting to new streams? Same ON CONFLICT handling.
                    if stream_ids:
                        stream_ids_update = set(stream_ids) - duplicate_stream_ids
                        if len(stream_ids_update) > 0:
                            now = utcnow_naive()
                            sp_stmt = pg_insert(StreamPhotometry).values(
                                [
                                    {
                                        "photometr_id": duplicate.id,
                                        "stream_id": sid,
                                        "created_at": now,
                                        "modified": now,
                                    }
                                    for sid in stream_ids_update
                                ]
                            )
                            await session.execute(
                                sp_stmt.on_conflict_do_nothing(
                                    index_elements=["stream_id", "photometr_id"]
                                )
                            )
                            log(
                                f"Adding streams {stream_ids_update} to photometry {duplicate.id}"
                            )

                    # update duplicate's flux and fluxerr if we are ignoring flux deduplication
                    # and both the duplicate and the new datapoint have origins that are not None, '', 'nan', or 'null'
                    if (
                        "origin" in df.columns
                        and ignore_flux
                        and overwrite_flux
                        and str(duplicate.origin).strip().lower()
                        not in ["none", "", "nan", "null"]
                        and str(df.loc[df_index]["origin"]).strip().lower()
                        not in ["none", "", "nan", "null"]
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
                        # Convert numpy scalars to native Python types
                        # to ensure compatibility with psycopg2 and json
                        # (numpy 2.x scalars are no longer subclasses of
                        # Python float/int)
                        duplicate.flux = numpy_to_native(
                            df.loc[df_index]["standardized_flux"]
                        )
                        duplicate.fluxerr = numpy_to_native(
                            df.loc[df_index]["standardized_fluxerr"]
                        )
                        duplicate.filter = df.loc[df_index]["filter"]
                        duplicate.ra = numpy_to_native(df.loc[df_index]["ra"])
                        duplicate.dec = numpy_to_native(df.loc[df_index]["dec"])
                        duplicate.ra_unc = numpy_to_native(df.loc[df_index]["ra_unc"])
                        duplicate.dec_unc = numpy_to_native(df.loc[df_index]["dec_unc"])
                        duplicate.ref_flux = numpy_to_native(
                            df.loc[df_index]["ref_standardized_flux"]
                        )
                        duplicate.ref_fluxerr = numpy_to_native(
                            df.loc[df_index]["ref_standardized_fluxerr"]
                        )
                        duplicate.altdata = json.dumps(
                            df.loc[df_index]["altdata"], cls=NumpyEncoder
                        )
                        duplicate.modified = utcnow_naive()
                        updated_ids.append(duplicate.id)
                        updated_duplicate_values.append(duplicate_value)

                # now safely drop the duplicates:
                new_photometry = df.loc[new_photometry_df_idxs]
                log(
                    f"Inserting {len(new_photometry.index)} "
                    f"(out of {len(df.index)}) new photometry points"
                )
                if ignore_flux and overwrite_flux and len(updated_ids) > 0:
                    log(
                        f"A total of {len(updated_ids)} duplicate photometry points (by obj_id, instrument_id, mjd, origin only, ignoring flux/fluxerr) were updated as requested."
                    )

                # Flush the in-loop duplicate mutations to the DB before
                # downstream work. Under async SQLAlchemy with the verified
                # session wrapper, autoflush on subsequent execute() did not
                # reliably push these UPDATEs, so the explicit flush is
                # required to make ignore_flux+overwrite_flux land.
                if updated_ids:
                    await session.flush()

                if len(new_photometry) > 0:
                    ids, upload_id = await insert_new_photometry_data(
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

                await session.commit()

                # get ids in the correct order
                ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]

                if len(new_photometry) > 0:
                    log(
                        f"Request from {username} for object {obj_id} with "
                        f"{len(new_photometry.index)} rows complete with upload_id {upload_id}."
                    )
                else:
                    log(
                        f"Request from {username} for object {obj_id} with "
                        f"{len(new_photometry.index)} rows complete with no new photometry."
                    )
                return self.success(data={"ids": ids})

            except Exception:
                await session.rollback()
                return self.error(traceback.format_exc())

    @auth_or_token
    def get(self, photometry_id: int):
        with self.Session() as session:
            phot = session.scalars(
                Photometry.select(session.user_or_token).where(
                    Photometry.id == photometry_id
                )
            ).first()

            if phot is None:
                return self.error(
                    f"Cannot find photometry point with ID: {photometry_id}."
                )

            # get the desired output format
            format = self.get_query_argument("format", "mag")
            outsys = self.get_query_argument("magsys", "ab")
            output = serialize(phot, outsys, format)
            return self.success(data=output)

    @permissions(["Upload data"])
    def patch(self, photometry_id: int):
        """
        ---
        summary: Update photometry
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Success'
          400:
            content:
              application/json:
                schema: Error
        """
        try:
            photometry_id = int(photometry_id)
        except ValueError:
            return self.error("Photometry id must be an int.")

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        stream_ids = data.pop("stream_ids", None)
        magsys = data.get("magsys", "ab")

        refresh = self.get_query_argument("refresh", default=False)

        with self.Session() as session:
            photometry = session.scalars(
                Photometry.select(session.user_or_token, mode="update").where(
                    Photometry.id == photometry_id
                )
            ).first()

            if photometry is None:
                # Update access (owner / "Manage photometry" / admin) is stricter
                # than read access, so a point can be visible yet not editable.
                # Distinguish that from a genuinely missing point.
                readable = session.scalars(
                    Photometry.select(session.user_or_token).where(
                        Photometry.id == photometry_id
                    )
                ).first()
                if readable is not None:
                    return self.error(
                        f"You do not have permission to update photometry point "
                        f"{photometry_id}. You must be its owner or have the "
                        f"'Manage photometry' permission."
                    )
                return self.error(
                    f"Cannot find photometry point with ID: {photometry_id}."
                )

            original_user_data = copy.deepcopy(data)

            # PhotometryFlux/PhotometryMag accept null flux/mag/magerr (a
            # non-detection) but reject NaN ("Special numeric values ... are not
            # permitted"). Leave None as-is so clearing magnitude + magnitude
            # error in the edit form converts the point to a non-detection
            # instead of failing schema validation.

            optional_keys = {"ra", "dec", "ra_unc", "dec_unc", "assignment_id"}
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
                        "Invalid input format: Tried to parse "
                        f"{data} as PhotometryFlux, got: "
                        f'"{e1.normalized_messages()}." Tried '
                        f"to parse {data} as PhotometryMag, got:"
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
                if not all(g.id in accessible_group_ids for g in groups):
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
                    "*",
                    "skyportal/REFRESH_SOURCE",
                    payload={"obj_key": internal_key},
                )

                flow.push(
                    "*",
                    "skyportal/REFRESH_SOURCE_PHOTOMETRY",
                    payload={"obj_id": photometry.obj_id, "magsys": magsys},
                )

            return self.success()

    @permissions(["Upload data"])
    def delete(self, photometry_id: int):
        """
        ---
        summary: Delete photometry
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Success'
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
                # Delete access (owner / "Manage photometry" / admin) is stricter
                # than read access, so a point can be visible yet not deletable.
                readable = session.scalars(
                    Photometry.select(session.user_or_token).where(
                        Photometry.id == photometry_id
                    )
                ).first()
                if readable is not None:
                    return self.error(
                        f"You do not have permission to delete photometry point "
                        f"{photometry_id}. You must be its owner or have the "
                        f"'Manage photometry' permission."
                    )
                return self.error(
                    f"Cannot find photometry point with ID: {photometry_id}."
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
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )

            return self.success()


class ObjPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id: str):
        individual_or_series = self.get_query_argument("individualOrSeries", "both")
        phase_fold_data = self.get_query_argument("phaseFoldData", False)
        format = self.get_query_argument("format", "mag")
        outsys = self.get_query_argument("magsys", "ab")
        include_owner_info = self.get_query_argument("includeOwnerInfo", False)
        include_stream_info = self.get_query_argument("includeStreamInfo", False)
        include_validation_info = self.get_query_argument(
            "includeValidationInfo", False
        )
        include_annotation_info = self.get_query_argument(
            "includeAnnotationInfo", False
        )
        include_extinction = self.get_query_argument("includeExtinction", False)
        include_superobjs_photometry = self.get_query_argument(
            "includeSuperObjsPhotometry", False
        )
        deduplicate_photometry = self.get_query_argument("deduplicatePhotometry", False)

        include_owner_info = str_to_bool(include_owner_info, default=False)

        include_stream_info = str_to_bool(include_stream_info, default=False)

        include_validation_info = str_to_bool(include_validation_info, default=False)

        include_annotation_info = str_to_bool(include_annotation_info, default=False)

        include_extinction = str_to_bool(include_extinction, default=False)

        with self.Session() as session:
            obj: Obj = session.scalars(
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
                if format == "plot":
                    options = [
                        load_only(*(getattr(Photometry, c) for c in PHOT_PLOT_COLUMNS))
                    ]
                else:
                    options = [
                        joinedload(Photometry.instrument).load_only(Instrument.name),
                        joinedload(Photometry.groups).load_only(
                            Group.id,
                            Group.name,
                            Group.nickname,
                            Group.single_user_group,
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

                obj_ids = {obj_id}
                if include_superobjs_photometry:
                    super_objs = (
                        session.scalars(
                            sa.select(SuperObj).where(
                                SuperObj.objs.any(Obj.id == obj_id)
                            )
                        )
                        .unique()
                        .all()
                    )
                    for super_obj in super_objs:
                        obj_ids.update({o.id for o in super_obj.objs})

                stmt = (
                    Photometry.select(
                        session.user_or_token,
                        options=options,
                    )
                    .where(
                        Photometry.obj_id.in_(obj_ids)
                        if len(obj_ids) > 1
                        else Photometry.obj_id == obj_id
                    )
                    .distinct()
                )
                photometry = session.scalars(stmt).unique().all()

                # Compute extinction for all filters
                extinction_dict = None
                if (
                    include_extinction
                    and format != "plot"
                    and len(photometry) > 0
                    and nan_to_none(obj.ra) is not None
                    and nan_to_none(obj.dec) is not None
                ):
                    extinction_dict = {}
                    filters = {phot.filter for phot in photometry}
                    for filt in filters:
                        extinction_dict[filt] = calculate_extinction(
                            obj.ra, obj.dec, filt
                        )

                phot_data = [
                    serialize(
                        phot,
                        outsys,
                        format,
                        annotations=include_annotation_info,
                        owner=include_owner_info,
                        stream=include_stream_info,
                        validation=include_validation_info,
                        extinction_dict=extinction_dict,
                    )
                    for phot in photometry
                ]
                if deduplicate_photometry and format != "plot" and len(phot_data) > 0:
                    df_phot = pd.DataFrame.from_records(phot_data)
                    # drop duplicate mjd/filter points, keeping most recent
                    phot_data = (
                        df_phot.sort_values(by="created_at", ascending=False)
                        .drop_duplicates(["mjd", "filter"])
                        .reset_index(drop=True)
                        .to_dict(orient="records")
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
                        orient="records"
                    )

            data = phot_data + series_data

            data.sort(key=lambda x: x["mjd"])

            if phase_fold_data:
                period, modified = None, arrow.Arrow(1, 1, 1)

                annotations = session.scalars(
                    Annotation.select(session.user_or_token).where(
                        Annotation.obj_id == obj_id
                    )
                ).all()
                period_str_options = ["period", "Period", "PERIOD"]
                for an in annotations:
                    if not isinstance(an.data, dict):
                        continue
                    for period_str in period_str_options:
                        if period_str in an.data and arrow.get(an.modified) > modified:
                            period = an.data[period_str]
                            modified = arrow.get(an.modified)
                if period is None:
                    self.error(f"No period for object {obj_id}")
                for ii in range(len(data)):
                    data[ii]["phase"] = np.mod(data[ii]["mjd"], period) / period

            return self.success(data=data)

    @permissions(["Delete bulk photometry"])
    def delete(self, obj_id: str):
        """
        ---
        summary: Delete all photometry for an object
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Success'
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
                return self.error("Invalid object id.")

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
    def delete(self, upload_id: str):
        """
        ---
        summary: Delete bulk-uploaded photometry
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
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          $ref: '#/components/schemas/Success'
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
                return self.error("Invalid bulk upload id.")

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
        magsys = self.get_query_argument("magsys", default="ab")

        if magsys not in ALLOWED_MAGSYSTEMS:
            return self.error("Invalid mag system.")

        format = self.get_query_argument("format", default="mag")
        if format not in ["mag", "flux"]:
            return self.error("Invalid output format.")

        with self.Session() as session:
            try:
                standardized = PhotometryRangeQuery.load(json)
            except ValidationError as e:
                return self.error(f"Invalid request body: {e.normalized_messages()}")

            instrument_ids = standardized["instrument_ids"]
            min_date = standardized["min_date"]
            max_date = standardized["max_date"]

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
                mjd = Time(min_date, format="datetime").mjd
                query = query.where(Photometry.mjd >= mjd)
            if max_date is not None:
                mjd = Time(max_date, format="datetime").mjd
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
        return self.error("This feature is deprecated")


PhotometryHandler.get.__doc__ = f"""
        ---
        summary: Get a photometry point
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
        summary: Get an object's photometry
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
              "plot" returns a slim per-point payload
              (id, obj_id, filter, mjd, origin, mag, magerr, limiting_mag)
              intended for lightcurve plotting; all per-point auxiliary
              joins (groups, annotations, instrument, owner, streams,
              validations) and the ref/tot/extinction blocks are skipped,
              regardless of the corresponding ``include*`` flags.
            schema:
              type: string
              enum:
                - mag
                - flux
                - plot
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
        summary: Retrieve photometry over a date range
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

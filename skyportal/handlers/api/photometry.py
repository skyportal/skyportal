import uuid
import datetime
import json
from io import StringIO

from astropy.time import Time
from astropy.table import Table
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
import sncosmo
from sncosmo.photdata import PhotometricData
import arrow

import sqlalchemy as sa
from sqlalchemy.sql import column, Values
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.env import load_env
from baselayer.log import make_log
from ..base import BaseHandler
from ...models import (
    DBSession,
    Annotation,
    Group,
    Stream,
    Photometry,
    Instrument,
    Obj,
    PHOT_ZP,
    GroupPhotometry,
    StreamPhotometry,
)

from ...models.schema import (
    PhotometryMag,
    PhotometryFlux,
    PhotFluxFlexible,
    PhotMagFlexible,
    PhotometryRangeQuery,
)
from ...enum_types import ALLOWED_MAGSYSTEMS

_, cfg = load_env()


log = make_log('api/photometry')

MAX_NUMBER_ROWS = 10000


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


def serialize(phot, outsys, format):

    return_value = {
        'obj_id': phot.obj_id,
        'ra': phot.ra,
        'dec': phot.dec,
        'filter': phot.filter,
        'mjd': phot.mjd,
        'instrument_id': phot.instrument_id,
        'instrument_name': phot.instrument.name,
        'ra_unc': phot.ra_unc,
        'dec_unc': phot.dec_unc,
        'origin': phot.origin,
        'id': phot.id,
        'groups': phot.groups,
        'altdata': phot.altdata,
    }

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

        if format == 'mag':
            if (
                phot.original_user_data is not None
                and 'limiting_mag' in phot.original_user_data
            ):
                magsys_packet = sncosmo.get_magsystem(phot.original_user_data['magsys'])
                relzp_packet = 2.5 * np.log10(magsys_packet.zpbandflux(filter))
                packet_correction = relzp_out - relzp_packet
                maglimit = phot.original_user_data['limiting_mag']
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
        elif format == 'flux':
            return_value.update(
                {
                    'flux': nan_to_none(phot.flux),
                    'magsys': outsys.name,
                    'zp': corrected_db_zp,
                    'fluxerr': phot.fluxerr,
                }
            )
        else:
            raise ValueError(
                'Invalid output format specified. Must be one of '
                f"['flux', 'mag'], got '{format}'."
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

    if "altdata" in data and not data["altdata"]:
        del data["altdata"]
    if "altdata" in data:
        if isinstance(data["altdata"], dict):
            max_num_elements = max(
                [
                    len(data[key])
                    for key in data
                    if isinstance(data[key], (list, tuple))
                    and key not in ["group_ids", "stream_ids"]
                ]
                + [1]
            )
            data["altdata"] = [data["altdata"]] * max_num_elements

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
        df = pd.DataFrame(data)
    except ValueError as e:
        raise ValidationError(
            'Unable to coerce passed JSON to a series of packets. ' f'Error was: "{e}"'
        )

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

    # convert to microjanskies, AB for DB storage as a vectorized operation
    pdata = PhotometricData(phot_table)
    standardized = pdata.normalized(zp=PHOT_ZP, zpsys='ab')

    df['standardized_flux'] = standardized.flux
    df['standardized_fluxerr'] = standardized.fluxerr

    instrument_cache = {}
    for iid in df['instrument_id'].unique():
        instrument = Instrument.query.get(int(iid))
        if not instrument:
            raise ValidationError(f'Invalid instrument ID: {iid}')
        instrument_cache[iid] = instrument

    for oid in df['obj_id'].unique():
        obj = Obj.query.get(oid)
        if not obj:
            raise ValidationError(f'Invalid object ID: {oid}')

    return df, instrument_cache


def get_values_table_and_condition(df):
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
                    row.origin,
                    float(row.mjd),
                    float(row.standardized_fluxerr),
                    float(row.standardized_flux),
                )
                for row in df.itertuples()
            ]
        )
        .alias("values_table")
    )

    # make sure no duplicate data are posted using the index
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
    df, instrument_cache, group_ids, stream_ids, user, session, validate=True
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

    pkq = f"SELECT nextval('photometry_id_seq') FROM " f"generate_series(1, {len(df)})"

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
            altdata=json.dumps(packet['altdata']),
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

    session.commit()
    return ids, upload_id


def get_group_ids(data, user):
    group_ids = data.pop("group_ids", [])
    if isinstance(group_ids, (list, tuple)):
        for group_id in group_ids:
            try:
                group_id = int(group_id)
            except TypeError:
                raise ValidationError(
                    f"Invalid format for group id {group_id}, must be an integer."
                )
            group = Group.query.get(group_id)
            if group is None:
                raise ValidationError(f'No group with ID {group_id}')
    elif group_ids == 'all':
        public_group = (
            DBSession()
            .execute(
                sa.select(Group).filter(Group.name == cfg["misc"]["public_group_name"])
            )
            .scalars()
            .first()
        )
        group_ids = [public_group.id]
    else:
        raise ValidationError(
            "Invalid group_ids parameter value. Must be a list of IDs "
            "(integers) or the string 'all'."
        )

    # always add the single user group
    group_ids.append(user.single_user_group.id)
    group_ids = list(set(group_ids))
    return group_ids


def get_stream_ids(data, user):
    stream_ids = data.pop("stream_ids", [])
    if isinstance(stream_ids, (list, tuple)):
        for stream_id in stream_ids:
            try:
                stream_id = int(stream_id)
            except TypeError:
                raise ValidationError(
                    f"Invalid format for stream id {stream_id}, must be an integer."
                )
            stream = Stream.get_if_accessible_by(stream_id, user)
            if stream is None:
                raise ValidationError(f'No stream with ID {stream_id}')
    else:
        raise ValidationError(
            "Invalid stream_ids parameter value. Must be a list of IDs (integers)."
        )

    stream_ids = list(set(stream_ids))
    return stream_ids


def add_external_photometry(json, user):
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
    """

    group_ids = get_group_ids(json, user)
    stream_ids = get_stream_ids(json, user)
    df, instrument_cache = standardize_photometry_data(json)

    if len(df.index) > MAX_NUMBER_ROWS:
        raise ValueError(
            f'Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. Please break up the data into smaller sets and try again'
        )

    username = user.username
    log(f'Pending request from {username} with {len(df.index)} rows')

    # This lock ensures that the Photometry table data are not modified in any way
    # between when the query for duplicate photometry is first executed and
    # when the insert statement with the new photometry is performed.
    # From the psql docs: This mode protects a table against concurrent
    # data changes, and is self-exclusive so that only one session can
    # hold it at a time.
    with DBSession() as session:
        try:
            session.execute(
                f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
            )
            ids, upload_id = insert_new_photometry_data(
                df, instrument_cache, group_ids, stream_ids, user, session
            )
            log(
                f'Request from {username} with {len(df.index)} rows complete with upload_id {upload_id}'
            )
        except Exception as e:
            session.rollback()
            log(f"Unable to post photometry: {e}")


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

        try:
            df, instrument_cache = standardize_photometry_data(self.get_json())
        except (ValidationError, RuntimeError) as e:
            return self.error(e.args[0])

        if len(df.index) > MAX_NUMBER_ROWS:
            return self.error(
                f'Maximum number of photometry rows to post exceeded: {len(df.index)} > {MAX_NUMBER_ROWS}. Please break up the data into smaller sets and try again'
            )

        username = self.associated_user_object.username
        log(f'Pending request from {username} with {len(df.index)} rows')

        # This lock ensures that the Photometry table data are not modified in any way
        # between when the query for duplicate photometry is first executed and
        # when the insert statement with the new photometry is performed.
        # From the psql docs: This mode protects a table against concurrent
        # data changes, and is self-exclusive so that only one session can
        # hold it at a time.
        with DBSession() as session:
            try:
                session.execute(
                    f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
                )
                ids, upload_id = insert_new_photometry_data(
                    df,
                    instrument_cache,
                    group_ids,
                    stream_ids,
                    self.associated_user_object,
                    session,
                )
            except Exception as e:
                session.rollback()
                return self.error(e.args[0])

        log(
            f'Request from {username} with {len(df.index)} rows complete with upload_id {upload_id}'
        )

        return self.success(data={'ids': ids, 'upload_id': upload_id})

    @permissions(['Upload data'])
    def put(self):
        """
        ---
        description: Update and/or upload photometry, resolving potential duplicates
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

        try:
            df, instrument_cache = standardize_photometry_data(self.get_json())
        except ValidationError as e:
            return self.error(e.args[0])

        values_table, condition = get_values_table_and_condition(df)

        # This lock ensures that the Photometry table data are not modified
        # in any way between when the query for duplicate photometry is first
        # executed and when the insert statement with the new photometry is
        # performed. From the psql docs: This mode protects a table against
        # concurrent data changes, and is self-exclusive so that only one
        # session can hold it at a time.

        with DBSession() as session:
            try:
                session.execute(
                    f'LOCK TABLE {Photometry.__tablename__} IN SHARE ROW EXCLUSIVE MODE'
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

                # now safely drop the duplicates:
                new_photometry = df.loc[new_photometry_df_idxs]

                if len(new_photometry) > 0:
                    ids, _ = insert_new_photometry_data(
                        new_photometry,
                        instrument_cache,
                        group_ids,
                        stream_ids,
                        self.associated_user_object,
                        session,
                        validate=False,
                    )

                    for (df_index, _), id in zip(new_photometry.iterrows(), ids):
                        id_map[df_index] = id

                # release the lock
                self.verify_and_commit()

            except Exception as e:
                session.rollback()
                return self.error(e.args[0])

        # get ids in the correct order
        ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]
        return self.success(data={'ids': ids})

    @auth_or_token
    def get(self, photometry_id):
        # The full docstring/API spec is below as an f-string

        phot = Photometry.get_if_accessible_by(
            photometry_id, self.current_user, raise_if_none=True
        )

        # get the desired output format
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        output = serialize(phot, outsys, format)
        self.verify_and_commit()
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

        photometry = Photometry.get_if_accessible_by(
            photometry_id, self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        stream_ids = data.pop("stream_ids", None)

        try:
            phot = PhotometryFlux.load(data)
        except ValidationError as e1:
            try:
                phot = PhotometryMag.load(data)
            except ValidationError as e2:
                return self.error(
                    'Invalid input format: Tried to parse '
                    f'{data} as PhotometryFlux, got: '
                    f'"{e1.normalized_messages()}." Tried '
                    f'to parse {data} as PhotometryMag, got:'
                    f' "{e2.normalized_messages()}."'
                )

        phot.original_user_data = data
        phot.id = photometry_id
        DBSession().merge(phot)

        # Update groups, if relevant
        if group_ids is not None:
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot upload photometry to groups you are not a member of."
                )
            photometry.groups = groups

        # Update streams, if relevant
        if stream_ids is not None:
            streams = Stream.get_if_accessible_by(
                stream_ids, self.current_user, raise_if_none=True
            )
            # Add new stream_photometry rows if not already present
            for stream in streams:
                if (
                    StreamPhotometry.query_records_accessible_by(self.current_user)
                    .filter(
                        StreamPhotometry.stream_id == stream.id,
                        StreamPhotometry.photometr_id == photometry_id,
                    )
                    .first()
                    is None
                ):
                    DBSession().add(
                        StreamPhotometry(
                            photometr_id=photometry_id, stream_id=stream.id
                        )
                    )

        self.verify_and_commit()
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
        photometry = Photometry.get_if_accessible_by(
            photometry_id, self.current_user, mode="delete", raise_if_none=True
        )

        DBSession().delete(photometry)
        self.verify_and_commit()

        return self.success()


class ObjPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        phase_fold_data = self.get_query_argument("phaseFoldData", False)

        if Obj.get_if_accessible_by(obj_id, self.current_user) is None:
            raise AccessError(
                f"Insufficient permissions for User {self.current_user.id} to read Obj {obj_id}"
            )
        photometry = Photometry.query_records_accessible_by(self.current_user).filter(
            Photometry.obj_id == obj_id
        )
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')

        self.verify_and_commit()
        data = [serialize(phot, outsys, format) for phot in photometry]

        if phase_fold_data:
            period, modified = None, arrow.Arrow(1, 1, 1)
            annotations = (
                Annotation.query_records_accessible_by(self.current_user)
                .filter(Annotation.obj_id == obj_id)
                .all()
            )
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


class BulkDeletePhotometryHandler(BaseHandler):
    @permissions(["Upload data"])
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
        photometry_to_delete = (
            Photometry.query_records_accessible_by(self.current_user, mode="delete")
            .filter(Photometry.upload_id == upload_id)
            .all()
        )

        n = len(photometry_to_delete)
        if n == 0:
            return self.error('Invalid bulk upload id.')

        for phot in photometry_to_delete:
            DBSession().delete(phot)

        self.verify_and_commit()
        return self.success(f"Deleted {n} photometry points.")


class PhotometryRangeHandler(BaseHandler):
    @auth_or_token
    def get(self):
        """Docstring appears below as an f-string."""

        json = self.get_json()

        try:
            standardized = PhotometryRangeQuery.load(json)
        except ValidationError as e:
            return self.error(f'Invalid request body: {e.normalized_messages()}')

        magsys = self.get_query_argument('magsys', default='ab')

        if magsys not in ALLOWED_MAGSYSTEMS:
            return self.error('Invalid mag system.')

        format = self.get_query_argument('format', default='mag')
        if format not in ['mag', 'flux']:
            return self.error('Invalid output format.')

        instrument_ids = standardized['instrument_ids']
        min_date = standardized['min_date']
        max_date = standardized['max_date']

        gids = [g.id for g in self.current_user.accessible_groups]

        group_phot_subquery = (
            GroupPhotometry.query_records_accessible_by(self.current_user)
            .filter(GroupPhotometry.group_id.in_(gids))
            .subquery()
        )
        query = Photometry.query_records_accessible_by(self.current_user)

        if instrument_ids is not None:
            query = query.filter(Photometry.instrument_id.in_(instrument_ids))
        if min_date is not None:
            mjd = Time(min_date, format='datetime').mjd
            query = query.filter(Photometry.mjd >= mjd)
        if max_date is not None:
            mjd = Time(max_date, format='datetime').mjd
            query = query.filter(Photometry.mjd <= mjd)

        query = query.join(
            group_phot_subquery, Photometry.id == group_phot_subquery.c.photometr_id
        )

        output = [serialize(p, magsys, format) for p in query]
        self.verify_and_commit()
        return self.success(data=output)


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
            name: phaseFoldData
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to phase fold the light curve. Defaults to false.
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

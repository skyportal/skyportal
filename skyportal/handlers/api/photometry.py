import uuid
import math

from astropy.time import Time
from astropy.table import Table
from marshmallow.exceptions import ValidationError
import numpy as np
import pandas as pd
import sncosmo
from sncosmo.photdata import PhotometricData

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FromClause
from sqlalchemy.sql import column
from sqlalchemy.orm import joinedload
from sqlalchemy import and_

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    Photometry,
    Instrument,
    Obj,
    PHOT_ZP,
    GroupPhotometry,
)

from ...schema import (
    PhotometryMag,
    PhotometryFlux,
    PhotFluxFlexible,
    PhotMagFlexible,
    PhotometryRangeQuery,
)
from ...enum_types import ALLOWED_MAGSYSTEMS


_, cfg = load_env()


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
    }

    filter = phot.filter

    magsys_db = sncosmo.get_magsystem('ab')
    outsys = sncosmo.get_magsystem(outsys)

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
                'magerr': phot.e_mag if nan_to_none(phot.e_mag) is not None else None,
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
    return return_value


class PhotometryHandler(BaseHandler):
    def standardize_photometry_data(self):

        data = self.get_json()

        if not isinstance(data, dict):
            raise ValidationError(
                'Top level JSON must be an instance of `dict`, got ' f'{type(data)}.'
            )

        if "altdata" in data and not data["altdata"]:
            del data["altdata"]

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

        if allscalar(data):
            data = [data]

        try:
            df = pd.DataFrame(data)
        except ValueError as e:
            if "altdata" in data and "Mixing dicts with non-Series" in str(e):
                try:
                    data["altdata"] = [
                        {key: value[i] for key, value in data["altdata"].items()}
                        for i in range(
                            len(data["altdata"][list(data["altdata"].keys())[-1]])
                        )
                    ]
                    df = pd.DataFrame(data)
                except ValueError:
                    raise ValidationError(
                        'Unable to coerce passed JSON to a series of packets. '
                        f'Error was: "{e}"'
                    )
            else:
                raise ValidationError(
                    'Unable to coerce passed JSON to a series of packets. '
                    f'Error was: "{e}"'
                )

        # `to_numeric` coerces numbers written as strings to numeric types
        #  (int, float)

        #  errors='ignore' means if something is actually an alphanumeric
        #  string, just leave it alone and dont error out

        #  apply is used to apply it to each column
        # (https://stackoverflow.com/questions/34844711/convert-entire-pandas
        # -dataframe-to-integers-in-pandas-0-17-0/34844867
        df = df.apply(pd.to_numeric, errors='ignore')

        # set origin to '' where it is None.
        df.loc[df['origin'].isna(), 'origin'] = ''

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

            # ensure nothing is null for the required fields
            for field in PhotMagFlexible.required_keys:
                missing = df[field].isna()
                if any(missing):
                    first_offender = np.argwhere(missing)[0, 0]
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

    def get_values_table_and_condition(self, df):
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

        # https://github.com/sqlalchemy/sqlalchemy/wiki/PGValues
        class _photometry_values(FromClause):
            """Render a postgres VALUES statement (in-memory constant table)."""

            named_with_column = True

            def __init__(self, columns, *args, **kw):
                self._column_args = columns
                self.list = args
                self.alias_name = self.name = kw.pop("alias_name", None)

            def _populate_column_collection(self):
                for c in self._column_args:
                    c._make_proxy(self)  # noqa

            @property
            def _from_objects(self):
                return [self]

        # https://github.com/sqlalchemy/sqlalchemy/wiki/PGValues
        @compiles(_photometry_values)
        def _compile_photometry_values(element, compiler, asfrom=False, **kw):
            columns = element.columns

            value_types = {
                'pdidx': 'INTEGER',
                'obj_id': 'CHARACTER VARYING',
                'instrument_id': 'INTEGER',
                'origin': 'CHARACTER VARYING',
                'mjd': 'DOUBLE PRECISION',
                'fluxerr': 'DOUBLE PRECISION',
                'flux': 'DOUBLE PRECISION',
            }

            def coerced_value(elem, column):
                literal_value = compiler.render_literal_value(elem, column.type)
                cast_value = value_types[column.name]
                return f'{literal_value}::{cast_value}'

            v = "VALUES %s" % ", ".join(
                "(%s)"
                % ", ".join(
                    coerced_value(elem, column)
                    if not (isinstance(elem, float) and math.isnan(elem))
                    else "'NaN'::numeric"
                    for elem, column in zip(tup, columns)
                )
                for tup in element.list
            )
            if asfrom:
                if element.alias_name:
                    v = "(%s) AS %s (%s)" % (
                        v,
                        element.alias_name,
                        (", ".join(c.name for c in element.columns)),
                    )
                else:
                    v = "(%s)" % v
            return v

        values_table = _photometry_values(
            (
                column("pdidx", sa.Integer),
                column("obj_id", sa.String),
                column("instrument_id", sa.Integer),
                column("origin", sa.String),
                column("mjd", sa.Float),
                column("fluxerr", sa.Float),
                column("flux", sa.Float),
            ),
            *[
                (
                    idx,
                    row["obj_id"],
                    row["instrument_id"],
                    row["origin"],
                    float(row["mjd"]),
                    float(row["standardized_fluxerr"]),
                    float(row["standardized_flux"]),
                )
                for idx, row in df.iterrows()
            ],
            alias_name="values_table",
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
        self, df, instrument_cache, group_ids, validate=True
    ):
        # check for existing photometry and error if any is found

        if validate:
            values_table, condition = self.get_values_table_and_condition(df)

            duplicated_photometry = (
                DBSession()
                .query(Photometry)
                .join(values_table, condition)
                .options(joinedload(Photometry.groups))
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

        pkq = (
            f"SELECT nextval('photometry_id_seq') FROM "
            f"generate_series(1, {len(df)})"
        )

        proxy = DBSession().execute(pkq)

        # cache this as list for response
        ids = [i[0] for i in proxy]
        df['id'] = ids

        df = df.where(pd.notnull(df), None)
        df.loc[df['standardized_flux'].isna(), 'standardized_flux'] = np.nan

        rows = df.to_dict('records')
        upload_id = str(uuid.uuid4())

        params = []
        for packet in rows:
            if (
                packet["filter"]
                not in instrument_cache[packet['instrument_id']].filters
            ):
                instrument = instrument_cache[packet['instrument_id']]
                raise ValidationError(
                    f"Instrument {instrument.name} has no filter "
                    f"{packet['filter']}."
                )

            flux = packet.pop('standardized_flux')
            fluxerr = packet.pop('standardized_fluxerr')

            # reduce the DB size by ~2x
            keys = ['limiting_mag', 'magsys', 'limiting_mag_nsigma']
            original_user_data = {key: packet[key] for key in keys if key in packet}
            if original_user_data == {}:
                original_user_data = None

            phot = dict(
                id=packet['id'],
                original_user_data=original_user_data,
                upload_id=upload_id,
                flux=flux,
                fluxerr=fluxerr,
                obj_id=packet['obj_id'],
                altdata=packet['altdata'],
                instrument_id=packet['instrument_id'],
                ra_unc=packet['ra_unc'],
                dec_unc=packet['dec_unc'],
                mjd=packet['mjd'],
                filter=packet['filter'],
                ra=packet['ra'],
                dec=packet['dec'],
                origin=packet["origin"],
            )

            params.append(phot)

        #  actually do the insert
        query = Photometry.__table__.insert()
        DBSession().execute(query, params)

        groupquery = GroupPhotometry.__table__.insert()
        params = []
        if group_ids == "all":
            public_group = (
                DBSession()
                .query(Group)
                .filter(Group.name == cfg["misc"]["public_group_name"])
                .first()
            )
            group_ids = [public_group.id]
        for id in ids:
            for group_id in group_ids:
                params.append({'photometr_id': id, 'group_id': group_id})

        DBSession().execute(groupquery, params)
        return ids, upload_id

    def get_group_ids(self):
        data = self.get_json()

        try:
            group_ids = data.pop("group_ids")
        except KeyError:
            raise ValidationError("Missing required field: group_ids")
        user_group_ids = [g.id for g in self.associated_user_object.accessible_groups]
        if isinstance(group_ids, (list, tuple)):
            forbidden_groups = set(group_ids) - set(user_group_ids)
            if len(forbidden_groups) > 0:
                raise ValidationError(
                    f"Invalid group_ids field. User does not have access to group IDs: {list(forbidden_groups)}."
                )
            groups = DBSession().query(Group).filter(Group.id.in_(group_ids)).all()
            if not groups:
                raise ValidationError(
                    "Invalid group_ids field. Specify at least one valid group ID."
                )
        elif group_ids != "all":
            raise ValidationError(
                "Invalid group_ids parameter value. Must be a list of IDs "
                "(integers) or the string 'all'."
            )

        return group_ids

    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload photometry
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

        # The Repeatable Read isolation level only sees data committed before
        # the transaction began; it never sees either uncommitted data or
        # changes committed during transaction execution by concurrent
        # transactions. (However, the query does see the effects of previous
        # updates executed within its own transaction, even though they are
        # not yet committed.) We use it here to ensure internally consistent
        # deduplication queries (i.e., to ensure that SELECT queries against
        # the photometry table do not return different results within this
        # method's transaction due to concurrent inserts or updates.

        DBSession().rollback()
        DBSession().execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        try:
            group_ids = self.get_group_ids()
        except ValidationError as e:
            return self.error(e.args[0])

        try:
            df, instrument_cache = self.standardize_photometry_data()
        except ValidationError as e:
            return self.error(e.args[0])

        try:
            ids, upload_id = self.insert_new_photometry_data(
                df, instrument_cache, group_ids
            )
        except ValidationError as e:
            return self.error(e.args[0])

        DBSession().commit()
        return self.success(data={'ids': ids, 'upload_id': upload_id})

    @permissions(['Upload data'])
    def put(self):
        """
        ---
        description: Update and/or upload photometry, resolving potential duplicates
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

        # The Repeatable Read isolation level only sees data committed before
        # the transaction began; it never sees either uncommitted data or
        # changes committed during transaction execution by concurrent
        # transactions. (However, the query does see the effects of previous
        # updates executed within its own transaction, even though they are
        # not yet committed.) We use it here to ensure internally consistent
        # deduplication queries (i.e., to ensure that SELECT queries against
        # the photometry table do not return different results within this
        # method's transaction due to concurrent inserts or updates.

        DBSession().rollback()
        DBSession().execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        try:
            group_ids = self.get_group_ids()
        except ValidationError as e:
            return self.error(e.args[0])

        try:
            df, instrument_cache = self.standardize_photometry_data()
        except ValidationError as e:
            return self.error(e.args[0])

        values_table, condition = self.get_values_table_and_condition(df)

        new_photometry_query = (
            DBSession()
            .query(values_table.c.pdidx)
            .outerjoin(Photometry, condition)
            .filter(Photometry.id.is_(None))
        )

        new_photometry_df_idxs = [g[0] for g in new_photometry_query]

        id_map = {}

        duplicated_photometry = (
            DBSession()
            .query(values_table.c.pdidx, Photometry)
            .join(Photometry, condition)
            .options(joinedload(Photometry.groups))
        )

        for df_index, duplicate in duplicated_photometry:
            id_map[df_index] = duplicate.id
            duplicate_group_ids = set([g.id for g in duplicate.groups])

            # posting to new groups?
            if len(set(group_ids) - duplicate_group_ids) > 0:
                # select old + new groups
                group_ids_update = set(group_ids).union(duplicate_group_ids)
                groups = (
                    DBSession()
                    .query(Group)
                    .filter(Group.id.in_(group_ids_update))
                    .all()
                )
                # update the corresponding photometry entry in the db
                duplicate.groups = groups

        # now safely drop the duplicates:
        new_photometry = df.loc[new_photometry_df_idxs]

        if len(new_photometry) > 0:
            try:
                ids, _ = self.insert_new_photometry_data(
                    new_photometry, instrument_cache, group_ids, validate=False
                )
            except ValidationError as e:
                return self.error(e.args[0])

            for (df_index, _), id in zip(new_photometry.iterrows(), ids):
                id_map[df_index] = id

        # get ids in the correct order
        ids = [id_map[pdidx] for pdidx, _ in df.iterrows()]

        DBSession().commit()
        return self.success(data={'ids': ids})

    @auth_or_token
    def get(self, photometry_id):
        # The full docstring/API spec is below as an f-string

        phot = Photometry.get_if_owned_by(photometry_id, self.current_user)
        if phot is None:
            return self.error('Invalid photometry ID')

        # get the desired output format
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        output = serialize(phot, outsys, format)
        return self.success(data=output)

    @permissions(['Manage sources'])
    def patch(self, photometry_id):
        """
        ---
        description: Update photometry
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

        # The Repeatable Read isolation level only sees data committed before
        # the transaction began; it never sees either uncommitted data or
        # changes committed during transaction execution by concurrent
        # transactions. (However, the query does see the effects of previous
        # updates executed within its own transaction, even though they are
        # not yet committed.) We use it here to ensure internally consistent
        # deduplication queries (i.e., to ensure that SELECT queries against
        # the photometry table do not return different results within this
        # method's transaction due to concurrent inserts or updates.

        DBSession().rollback()
        DBSession().execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        photometry = Photometry.get_if_owned_by(photometry_id, self.current_user)
        data = self.get_json()
        group_ids = data.pop("group_ids", None)

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
                    "Invalid group_ids field. " "Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot upload photometry to groups you " "are not a member of."
                )
            photometry.groups = groups

        DBSession().commit()
        return self.success()

    @permissions(['Manage sources'])
    def delete(self, photometry_id):
        """
        ---
        description: Delete photometry
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
        _ = Photometry.get_if_owned_by(photometry_id, self.current_user)
        DBSession().query(Photometry).filter(
            Photometry.id == int(photometry_id)
        ).delete()
        DBSession().commit()

        return self.success()


class ObjPhotometryHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object id.')
        photometry = Obj.get_photometry_owned_by_user(obj_id, self.current_user)
        format = self.get_query_argument('format', 'mag')
        outsys = self.get_query_argument('magsys', 'ab')
        return self.success(
            data=[serialize(phot, outsys, format) for phot in photometry]
        )


class BulkDeletePhotometryHandler(BaseHandler):
    @auth_or_token
    def delete(self, upload_id):
        """
        ---
        description: Delete bulk-uploaded photometry set
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
        # Permissions check:
        phot_id = Photometry.query.filter(Photometry.upload_id == upload_id).first().id
        _ = Photometry.get_if_owned_by(phot_id, self.current_user)

        n_deleted = (
            DBSession()
            .query(Photometry)
            .filter(Photometry.upload_id == upload_id)
            .delete()
        )
        DBSession().commit()

        return self.success(f"Deleted {n_deleted} photometry points.")


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

        query = (
            DBSession()
            .query(Photometry)
            .join(GroupPhotometry)
            .filter(GroupPhotometry.group_id.in_(gids))
        )

        if instrument_ids is not None:
            query = query.filter(Photometry.instrument_id.in_(instrument_ids))
        if min_date is not None:
            mjd = Time(min_date, format='datetime').mjd
            query = query.filter(Photometry.mjd >= mjd)
        if max_date is not None:
            mjd = Time(max_date, format='datetime').mjd
            query = query.filter(Photometry.mjd <= mjd)

        output = [serialize(p, magsys, format) for p in query]
        return self.success(data=output)


PhotometryHandler.get.__doc__ = f"""
        ---
        description: Retrieve photometry
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

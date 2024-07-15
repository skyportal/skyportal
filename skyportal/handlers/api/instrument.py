import ast
from io import StringIO

import arrow
import numpy as np
import pandas as pd
import sqlalchemy as sa
from astropy import coordinates
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from healpix_alchemy import Tile
from marshmallow.exceptions import ValidationError
from regions import CircleSkyRegion, PolygonSkyRegion, RectangleSkyRegion, Regions
from sqlalchemy.orm import joinedload, scoped_session, sessionmaker, undefer
from tornado.ioloop import IOLoop

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.env import load_env
from baselayer.log import make_log
from skyportal.utils.calculations import get_airmass

from ...enum_types import ALLOWED_BANDPASSES
from ...models import (
    DBSession,
    GcnEvent,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    InstrumentLog,
    Localization,
    LocalizationTile,
    Photometry,
    Telescope,
)
from ...utils.cache import Cache, array_to_bytes
from ..base import BaseHandler

log = make_log('api/instrument')
env, cfg = load_env()

cache_dir = "cache/localization_instrument_queries"
cache = Cache(
    cache_dir=cache_dir,
    max_items=cfg.get("misc.max_items_in_localization_instrument_query_cache", 100),
    max_age=cfg.get("misc.minutes_to_keep_localization_instrument_query_cache", 24 * 60)
    * 60,  # defaults to 1 day
)

Session = scoped_session(sessionmaker())


class InstrumentHandler(BaseHandler):
    @permissions(['Manage instruments'])
    def post(self):
        # See bottom of this file for redoc docstring -- moved it there so that
        # it could be made an f-string.

        data = self.get_json()
        telescope_id = data.get('telescope_id')
        with self.Session() as session:
            stmt = Telescope.select(session.user_or_token).filter(
                Telescope.id == telescope_id
            )
            telescope = session.scalars(stmt).first()
            if not telescope:
                return self.error(f'No telescope with id {telescope_id}')

            sensitivity_data = data.get("sensitivity_data", None)
            if isinstance(sensitivity_data, str):
                sensitivity_data = ast.literal_eval(
                    sensitivity_data.replace("\'", "\"")
                )
                data['sensitivity_data'] = sensitivity_data

            if sensitivity_data:
                filters = data.get("filters", [])
                if not set(sensitivity_data.keys()).issubset(filters):
                    return self.error(
                        'Sensitivity_data filters must be a subset of the instrument filters'
                    )

            configuration_data = data.get("configuration_data", None)
            if isinstance(configuration_data, str):
                configuration_data = ast.literal_eval(
                    configuration_data.replace("\'", "\"")
                )
                data['configuration_data'] = configuration_data

            references = data.pop("references", None)
            if isinstance(references, str):
                try:
                    references = ast.literal_eval(references.replace("\'", "\""))
                except Exception:
                    pass
            if references is not None:
                try:
                    if isinstance(references, dict):
                        references = pd.DataFrame.from_dict(references)
                    elif isinstance(references, str):
                        references = pd.read_table(StringIO(references), sep=',')
                    else:
                        raise ValueError("references must be a dict or a string")
                except Exception as e:
                    return self.error(f"Could not parse references: {e}")
                # verify that the columns are field, filter (required) and limmag (optional)
                if not {'field', 'filter'}.issubset(references.columns):
                    return self.error(
                        "references must contain at least field and filter columns"
                    )
                if not set(list(references.columns)).issubset(
                    {'field', 'filter', 'limmag'}
                ):
                    return self.error(
                        "references can only contain field, filter, and limmag columns"
                    )
                if not references['field'].dtype == int:
                    return self.error("references field must be an integer")
                if not set(references['filter']).issubset(ALLOWED_BANDPASSES):
                    return self.error(
                        f"references filter must be one of {ALLOWED_BANDPASSES}"
                    )
                if (
                    'limmag' in list(references.columns)
                    and not references['limmag'].dtype == float
                ):
                    return self.error("references limmag must be a float")

            field_data = data.pop("field_data", None)
            field_region = data.pop("field_region", None)

            field_fov_type = data.pop("field_fov_type", None)
            field_fov_attributes = data.pop("field_fov_attributes", None)

            if (field_region is not None) and (field_fov_type is not None):
                return self.error(
                    'must supply only one of field_region or field_fov_type'
                )

            if field_region is not None:
                regions = Regions.parse(field_region, format='ds9')
                data['region'] = regions.serialize(format='ds9')

            if field_fov_type is not None:
                if field_fov_attributes is None:
                    return self.error(
                        'field_fov_attributes required if field_fov_type supplied'
                    )
                if not field_fov_type.lower() in ["circle", "rectangle"]:
                    return self.error('field_fov_type must be circle or rectangle')
                if isinstance(field_fov_attributes, list):
                    field_fov_attributes = [float(x) for x in field_fov_attributes]
                else:
                    field_fov_attributes = [float(field_fov_attributes)]

                center = SkyCoord(0.0, 0.0, unit='deg', frame='icrs')
                if field_fov_type.lower() == "circle":
                    if not len(field_fov_attributes) == 1:
                        return self.error(
                            'If field_fov_type is circle, then should supply only radius for field_fov_attributes'
                        )
                    radius = field_fov_attributes[0]
                    regions = CircleSkyRegion(center=center, radius=radius * u.deg)
                elif field_fov_type.lower() == "rectangle":
                    if not len(field_fov_attributes) == 2:
                        return self.error(
                            'If field_fov_type is rectangle, then should supply width and height for field_fov_attributes'
                        )
                    width, height = field_fov_attributes
                    regions = RectangleSkyRegion(
                        center=center, width=width * u.deg, height=height * u.deg
                    )
                data['region'] = regions.serialize(format='ds9')

            schema = Instrument.__schema__()
            try:
                instrument = schema.load(data)
            except ValidationError as exc:
                return self.error(
                    'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
                )

            stmt = Instrument.select(session.user_or_token).where(
                Instrument.name == data.get('name'),
                Instrument.telescope_id == telescope_id,
            )
            existing_instrument = session.scalars(stmt).first()
            if existing_instrument is not None:
                return self.error(
                    'Instrument with name {} already exists for telescope {}'.format(
                        existing_instrument.name, telescope_id
                    )
                )

            instrument.telescope = telescope
            session.add(instrument)
            session.commit()

            if references is not None:
                if not set(references['filter']).issubset(instrument.filters):
                    return self.error(
                        'Filters in references must be a subset of the instrument filters'
                    )

            if field_data is not None:
                if (field_region is None) and (field_fov_type is None):
                    return self.error(
                        'field_region or field_fov_type is required with field_data'
                    )

                if type(field_data) is str:
                    field_data = load_field_data(field_data)
                    if field_data is None:
                        return self.error('Could not parse the field data table')

                if not {'ID', 'RA', 'Dec'}.issubset(field_data):
                    return self.error("ID, RA, and Dec required in field_data.")

                log(f"Started generating fields for instrument {instrument.id}")
                # run async
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_tiles(
                        instrument.id,
                        instrument.name,
                        regions,
                        field_data,
                        references=references,
                    ),
                )

            self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
            return self.success(data={"id": instrument.id})

    @auth_or_token
    async def get(self, instrument_id=None):
        """
        ---
        single:
          description: Retrieve an instrument
          tags:
            - instruments
          parameters:
            - in: path
              name: instrument_id
              required: true
              schema:
                type: integer
            - in: query
              name: includeGeoJSON
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON. Defaults to
                false.
            - in: query
              name: includeGeoJSONSummary
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON summary bounding box. Defaults to
                false.
            - in: query
              name: includeRegion
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated DS9 region. Defaults to
                false.
            - in: query
              name: localizationDateobs
              schema:
                type: string
              description: |
                Include fields within a given localization.
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
            - in: query
              name: localizationName
              schema:
                type: string
              description: |
                Name of localization / skymap to use.
                Can be found in Localization.localization_name queried from
                /api/localization endpoint or skymap name in GcnEvent page
                table.
            - in: query
              name: localizationCumprob
              schema:
                type: number
              description: |
                Cumulative probability up to which to include fields.
                Defaults to 0.95.
          responses:
            200:
              content:
                application/json:
                  schema: SingleInstrument
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all instruments
          tags:
            - instruments
          parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name (exact match)
            - in: query
              name: includeGeoJSON
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON. Defaults to
                false.
            - in: query
              name: includeGeoJSONSummary
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated GeoJSON summary bounding box. Defaults to
                false.
            - in: query
              name: includeRegion
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to include associated DS9 region. Defaults to
                false.
            - in: query
              name: ignoreCache
              nullable: true
              schema:
                type: boolean
              description: |
                Boolean indicating whether to ignore field caching. Defaults to
                false.
            - in: query
              name: localizationDateobs
              schema:
                type: string
              description: |
                Include fields within a given localization.
                Event time in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Each localization is associated with a specific GCNEvent by
                the date the event happened, and this date is used as a unique
                identifier. It can be therefore found as Localization.dateobs,
                queried from the /api/localization endpoint or dateobs in the
                GcnEvent page table.
            - in: query
              name: localizationName
              schema:
                type: string
              description: |
                Name of localization / skymap to use.
                Can be found in Localization.localization_name queried from
                /api/localization endpoint or skymap name in GcnEvent page
                table.
            - in: query
              name: localizationCumprob
              schema:
                type: number
              description: |
                Cumulative probability up to which to include fields.
                Defaults to 0.95.
            - in: query
              name: airmassTime
              schema:
                type: string
              description: |
                Time to use for airmass calculation in
                ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.sss`).
                Defaults to localizationDateobs if not supplied.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfInstruments
            400:
              content:
                application/json:
                  schema: Error
        """

        localization_dateobs = self.get_query_argument('localizationDateobs', None)
        localization_name = self.get_query_argument('localizationName', None)
        localization_cumprob = self.get_query_argument("localizationCumprob", 0.95)

        includeGeoJSON = self.get_query_argument("includeGeoJSON", False)
        includeGeoJSONSummary = self.get_query_argument("includeGeoJSONSummary", False)
        includeRegion = self.get_query_argument("includeRegion", False)

        airmass_time = self.get_query_argument('airmassTime', None)
        ignore_cache = self.get_query_argument("ignoreCache", False)

        if airmass_time is None:
            if localization_dateobs is not None:
                airmass_time = Time(arrow.get(localization_dateobs).datetime)
        else:
            airmass_time = Time(arrow.get(airmass_time).datetime)

        if includeGeoJSON:
            options = [joinedload(Instrument.fields).undefer(InstrumentField.contour)]
        elif includeGeoJSONSummary:
            options = [
                joinedload(Instrument.fields).undefer(InstrumentField.contour_summary)
            ]
        else:
            options = []
        if includeRegion:
            options.append(undefer(Instrument.region))

        with self.Session() as session:
            if instrument_id is not None:
                stmt = Instrument.select(self.current_user, options=options).where(
                    Instrument.id == int(instrument_id)
                )
                instrument = session.scalars(stmt).first()
                if instrument is None:
                    return self.error(f'No instrument with ID: {instrument_id}')

                data = instrument.to_dict()

                data['status'] = instrument.status

                data['log_exists'] = (
                    session.scalars(
                        InstrumentLog.select(self.current_user).where(
                            InstrumentLog.instrument_id == int(instrument_id)
                        )
                    ).first()
                    is not None
                )

                # optional: slice by GcnEvent localization
                if localization_dateobs is not None:
                    if localization_name is not None:
                        localization = session.scalars(
                            Localization.select(
                                self.current_user,
                            )
                            .where(Localization.dateobs == localization_dateobs)
                            .where(Localization.localization_name == localization_name)
                        ).first()
                        if localization is None:
                            return self.error("Localization not found", status=404)
                    else:
                        event = session.scalars(
                            GcnEvent.select(
                                self.current_user,
                            )
                            .where(GcnEvent.dateobs == localization_dateobs)
                            .options(joinedload(GcnEvent.localizations))
                        ).first()
                        if event is None:
                            return self.error("GCN event not found", status=404)
                        localization = event.localizations[-1]

                    # now get the dateobs in the format YYYY_MM
                    partition_key = arrow.get(localization.dateobs).datetime
                    localizationtile_partition_name = (
                        f'{partition_key.year}_{partition_key.month:02d}'
                    )
                    localizationtilescls = LocalizationTile.partitions.get(
                        localizationtile_partition_name, None
                    )
                    if localizationtilescls is None:
                        localizationtilescls = LocalizationTile.partitions.get(
                            'def', LocalizationTile
                        )
                    else:
                        # check that there is actually a localizationTile with the given localization_id in the partition
                        # if not, use the default partition
                        if not (
                            session.scalars(
                                localizationtilescls.select(self.current_user).where(
                                    localizationtilescls.localization_id
                                    == localization.id
                                )
                            ).first()
                        ):
                            localizationtilescls = LocalizationTile.partitions.get(
                                'def', LocalizationTile
                            )

                    cum_prob = (
                        sa.func.sum(
                            localizationtilescls.probdensity
                            * localizationtilescls.healpix.area
                        )
                        .over(order_by=localizationtilescls.probdensity.desc())
                        .label('cum_prob')
                    )
                    localizationtile_subquery = (
                        sa.select(localizationtilescls.probdensity, cum_prob).filter(
                            localizationtilescls.localization_id == localization.id
                        )
                    ).subquery()

                    min_probdensity = (
                        sa.select(
                            sa.func.min(localizationtile_subquery.columns.probdensity)
                        ).filter(
                            localizationtile_subquery.columns.cum_prob
                            <= localization_cumprob
                        )
                    ).scalar_subquery()

                    query_id = f"{str(localization.id)}_{str(instrument.id)}_{str(localization_cumprob)}"

                    if includeGeoJSON or includeGeoJSONSummary:
                        if includeGeoJSON:
                            undefer_column = InstrumentField.contour
                        elif includeGeoJSONSummary:
                            undefer_column = InstrumentField.contour_summary

                        cache_filename = cache[query_id]
                        if cache_filename is not None and not ignore_cache:
                            field_ids = np.load(cache_filename).tolist()
                            tiles = (
                                session.scalars(
                                    sa.select(InstrumentField)
                                    .filter(
                                        InstrumentField.field_id.in_(field_ids),
                                        InstrumentField.instrument_id == instrument.id,
                                    )
                                    .options(undefer(undefer_column))
                                )
                                .unique()
                                .all()
                            )
                        else:
                            tiles = (
                                session.scalars(
                                    sa.select(InstrumentField)
                                    .filter(
                                        localizationtilescls.localization_id
                                        == localization.id,
                                        localizationtilescls.probdensity
                                        >= min_probdensity,
                                        InstrumentFieldTile.instrument_id
                                        == instrument.id,
                                        InstrumentFieldTile.instrument_field_id
                                        == InstrumentField.id,
                                        InstrumentFieldTile.healpix.overlaps(
                                            localizationtilescls.healpix
                                        ),
                                    )
                                    .options(undefer(undefer_column))
                                )
                                .unique()
                                .all()
                            )
                            if len(tiles) > 0:
                                cache[query_id] = array_to_bytes(
                                    [tile.field_id for tile in tiles]
                                )
                    else:
                        cache_filename = cache[query_id]
                        if cache_filename is not None and not ignore_cache:
                            field_ids = np.load(cache_filename).tolist()
                            tiles = (
                                session.scalars(
                                    sa.select(InstrumentField).filter(
                                        InstrumentField.field_id.in_(field_ids)
                                    )
                                )
                                .unique()
                                .all()
                            )
                        else:
                            tiles = (
                                (
                                    session.scalars(
                                        sa.select(InstrumentField).filter(
                                            localizationtilescls.localization_id
                                            == localization.id,
                                            localizationtilescls.probdensity
                                            >= min_probdensity,
                                            InstrumentFieldTile.instrument_id
                                            == instrument.id,
                                            InstrumentFieldTile.instrument_field_id
                                            == InstrumentField.id,
                                            InstrumentFieldTile.healpix.overlaps(
                                                localizationtilescls.healpix
                                            ),
                                        )
                                    )
                                )
                                .unique()
                                .all()
                            )
                            if len(tiles) > 0:
                                cache[query_id] = array_to_bytes(
                                    [tile.field_id for tile in tiles]
                                )

                    fields = [tile.to_dict() for tile in tiles]
                    observer = instrument.telescope.observer
                    if observer is None:
                        airmass_bulk = (
                            np.ones((len(fields), len(airmass_time))) * np.inf
                        )
                    else:
                        airmass_bulk = get_airmass(
                            fields,
                            time=np.array([airmass_time]),
                            observer=observer,
                        ).flatten()

                    data['fields'] = [
                        {**field, 'airmass': airmass}
                        for field, airmass in zip(fields, airmass_bulk)
                    ]

                return self.success(data=data)

            inst_name = self.get_query_argument("name", None)
            if includeRegion:
                stmt = Instrument.select(self.current_user).options(
                    undefer(Instrument.region)
                )
            else:
                stmt = Instrument.select(self.current_user)
            if inst_name is not None:
                stmt = stmt.filter(Instrument.name == inst_name)
            instruments = session.scalars(stmt).all()

            data = [
                {
                    **instrument.to_dict(),
                    'telescope': instrument.telescope.to_dict(),
                    'number_of_fields': instrument.number_of_fields,
                    'region_summary': instrument.region_summary,
                    'log_exists': session.scalars(
                        InstrumentLog.select(self.current_user).where(
                            InstrumentLog.instrument_id == instrument.id
                        )
                    ).first()
                    is not None,
                }
                for instrument in instruments
            ]
            return self.success(data=data)

    @permissions(['Manage instruments'])
    def put(self, instrument_id):
        """
        ---
        description: Update instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: InstrumentNoID
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
        data = self.get_json()
        data['id'] = int(instrument_id)
        with self.Session() as session:
            # permission check
            stmt = Instrument.select(session.user_or_token, mode="update").where(
                Instrument.id == int(instrument_id)
            )
            instrument = session.scalars(stmt).first()
            if instrument is None:
                return self.error(f'Missing instrument with ID {instrument_id}')

            filters = data.get('filters', None)
            if filters is not None:
                if not set(list(instrument.filters)).issubset(set(filters)):
                    new_filters = list(
                        set(list(instrument.filters)).difference(set(filters))
                    )
                    for filt in new_filters:
                        stmt = Photometry.select(session.user_or_token).where(
                            Photometry.filter == filt,
                            Photometry.instrument_id == instrument.id,
                        )
                        count_stmt = sa.select(sa.func.count()).select_from(
                            stmt.distinct()
                        )
                        total_photometry = session.execute(count_stmt).scalar()
                        if total_photometry > 0:
                            return self.error(
                                f'Cannot remove filter {filt} from instrument {instrument.name}: {total_photometry} photometry points must be first deleted.'
                            )

            sensitivity_data = data.get('sensitivity_data', None)
            if isinstance(sensitivity_data, str):
                sensitivity_data = ast.literal_eval(
                    sensitivity_data.replace("\'", "\"")
                )
                data['sensitivity_data'] = sensitivity_data

            configuration_data = data.get("configuration_data", None)
            if isinstance(configuration_data, str):
                configuration_data = ast.literal_eval(
                    configuration_data.replace("\'", "\"")
                )
                data['configuration_data'] = configuration_data

            references = data.pop("references", None)
            if isinstance(references, str):
                try:
                    references = ast.literal_eval(references.replace("\'", "\""))
                except Exception:
                    pass
            if references is not None:
                try:
                    if isinstance(references, dict):
                        references = pd.DataFrame.from_dict(references)
                    elif isinstance(references, str):
                        references = pd.read_table(StringIO(references), sep=',')
                    else:
                        raise ValueError("references must be a dict or a string")
                except Exception as e:
                    return self.error(f"Could not parse references: {e}")
                # verify that the columns are field, filter (required) and limmag (optional)
                if not {'field', 'filter'}.issubset(references.columns):
                    return self.error(
                        "references must contain at least field and filter columns"
                    )
                if not set(list(references.columns)).issubset(
                    {'field', 'filter', 'limmag'}
                ):
                    return self.error(
                        "references can only contain field, filter, and limmag columns"
                    )
                if not references['field'].dtype == int:
                    return self.error("references field must be an integer")
                if not set(references['filter']).issubset(ALLOWED_BANDPASSES):
                    return self.error(
                        f"references filter must be one of {ALLOWED_BANDPASSES}"
                    )
                if (
                    'limmag' in list(references.columns)
                    and not references['limmag'].dtype == float
                ):
                    return self.error("references limmag must be a float")

            field_data = data.pop("field_data", None)
            field_region = data.pop("field_region", None)

            field_fov_type = data.pop("field_fov_type", None)
            field_fov_attributes = data.pop("field_fov_attributes", None)

            if (field_region is not None) and (field_fov_type is not None):
                return self.error(
                    'must supply only one of field_region or field_fov_type'
                )

            if field_region is not None:
                regions = Regions.parse(field_region, format='ds9')
                data['region'] = regions.serialize(format='ds9')
            elif instrument.has_region:
                regions = Regions.parse(instrument.region, format='ds9')
            else:
                regions = None

            if field_fov_type is not None:
                if field_fov_attributes is None:
                    return self.error(
                        'field_fov_attributes required if field_fov_type supplied'
                    )
                if not field_fov_type.lower() in ["circle", "rectangle"]:
                    return self.error('field_fov_type must be circle or rectangle')
                if isinstance(field_fov_attributes, list):
                    field_fov_attributes = [float(x) for x in field_fov_attributes]
                else:
                    field_fov_attributes = [float(field_fov_attributes)]

                center = SkyCoord(0.0, 0.0, unit='deg', frame='icrs')
                if field_fov_type.lower() == "circle":
                    if not len(field_fov_attributes) == 1:
                        return self.error(
                            'If field_fov_type is circle, then should supply only radius for field_fov_attributes'
                        )
                    radius = field_fov_attributes[0]
                    regions = CircleSkyRegion(center=center, radius=radius * u.deg)
                elif field_fov_type.lower() == "rectangle":
                    if not len(field_fov_attributes) == 2:
                        return self.error(
                            'If field_fov_type is rectangle, then should supply width and height for field_fov_attributes'
                        )
                    width, height = field_fov_attributes
                    regions = RectangleSkyRegion(
                        center=center, width=width * u.deg, height=height * u.deg
                    )
                data['region'] = regions.serialize(format='ds9')

            schema = Instrument.__schema__()
            try:
                schema.load(data, partial=True)
            except ValidationError as e:
                return self.error(
                    'Invalid/missing parameters: ' f'{e.normalized_messages()}'
                )

            for k in data:
                if k not in ['sensitivity_data', 'configuration_data']:
                    setattr(instrument, k, data[k])

            if references is not None:
                if not set(references['filter']).issubset(instrument.filters):
                    return self.error(
                        'Filters in references must be a subset of the instrument filters'
                    )

            if sensitivity_data:
                if not set(sensitivity_data.keys()).issubset(instrument.filters):
                    return self.error(
                        'Filter names must be present in both sensitivity_data property and filters property'
                    )
                instrument.sensitivity_data = sensitivity_data

            if configuration_data:
                instrument.configuration_data = configuration_data

            # temporary, to migrate old instruments
            if instrument.region is not None or field_region is not None:
                instrument.has_region = True
            if (
                len(instrument.fields) > 0
            ):  # here we dont validate field_data, as the addition of fields is done later and might fail
                instrument.has_fields = True

            session.commit()

            if (field_data is not None) or (references is not None):
                if field_data is not None:
                    if (
                        (field_region is None)
                        and (field_fov_type is None)
                        and (regions is None)
                    ):
                        return self.error(
                            'field_region or field_fov_type or existing region is required with field_data'
                        )

                    if type(field_data) is str:
                        field_data = load_field_data(field_data)
                        if field_data is None:
                            return self.error('Could not parse the field data table')

                    if not {'ID', 'RA', 'Dec'}.issubset(field_data):
                        return self.error("ID, RA, and Dec required in field_data.")

                log(f"Started generating fields for instrument {instrument.id}")
                # run async
                IOLoop.current().run_in_executor(
                    None,
                    lambda: add_tiles(
                        instrument.id,
                        instrument.name,
                        regions,
                        field_data,
                        references=references,
                        modify=True,
                    ),
                )

            self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
            return self.success()

    @permissions(['Delete instrument'])
    def delete(self, instrument_id):
        """
        ---
        description: Delete an instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
            required: true
            schema:
              type: integer
          - in: query
            name: fieldsOnly
            nullable: true
            schema:
              type: boolean
            description: |
              Boolean indicating whether to just delete the associated fields.
              Defaults to false.
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
            stmt = Instrument.select(session.user_or_token, mode="delete").where(
                Instrument.id == int(instrument_id)
            )
            instrument = session.scalars(stmt).first()
            if instrument is None:
                return self.error(f'Missing instrument with ID {instrument_id}')

            session.delete(instrument)
            session.commit()

        self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
        return self.success()


InstrumentHandler.post.__doc__ = f"""
        ---
        description: Add a new instrument
        tags:
          - instruments
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                - $ref: "#/components/schemas/InstrumentNoID"
                - type: object
                  properties:
                    filters:
                      type: array
                      items:
                        type: string
                        enum: {list(ALLOWED_BANDPASSES)}
                      description: >-
                        List of filters on the instrument. If the instrument
                        has no filters (e.g., because it is a spectrograph),
                        leave blank or pass the empty list.
                      default: []
                    sensitivity_data:
                      type: object
                      properties:
                        filter_name:
                          type: object
                          enum: {list(ALLOWED_BANDPASSES)}
                          properties:
                            limiting_magnitude:
                              type: float
                            magsys:
                              type: string
                            exposure_time:
                              type: float
                              description: |
                                Exposure time in seconds.
                      description: |
                        List of filters and associated limiting magnitude and exposure time.
                        Sensitivity_data filters must be a subset of the instrument filters.
                        Limiting magnitude assumed to be AB magnitude.
                    configuration_data:
                      type: object
                      properties:
                        filter_name:
                          type: object
                          properties:
                            filt_change_time:
                              type: float
                              description: |
                                Time in seconds to change filters
                            readout:
                              type: float
                              description: |
                                Time in seconds to readout camera
                            overhead_per_exposure:
                              type: float
                              description: |
                                Non-readout overheads, e.g. instrument settling times, in seconds.
                            slew_rate:
                              type: float
                              description: |
                                Slew rate for the telescope in deg/s.
                      description: |
                        Instrument configuration properties such as instrument overhead, filter change time, readout, etc.
                    field_data:
                      type: dict
                      items:
                        type: array
                      description: |
                        List of ID, RA, and Dec for each field.
                    field_region:
                      type: str
                      description: |
                        Serialized version of a regions.Region describing
                        the shape of the instrument field. Note: should
                        only include field_region or field_fov_type.
                    references:
                      type: dict
                      items:
                        type: array
                      description: |
                        List of filter, and limiting magnitude for each reference.
                    field_fov_type:
                      type: str
                      description: |
                        Option for instrument field shape. Must be either
                        circle or rectangle. Note: should only
                        include field_region or field_fov_type.
                    field_fov_attributes:
                      type: list
                      description: |
                        Option for instrument field shape parameters.
                        Single float radius in degrees in case of circle or
                        list of two floats (height and width) in case of
                        a rectangle.
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
                            id:
                              type: integer
                              description: New instrument ID
          400:
            content:
              application/json:
                schema: Error
        """


def load_field_data(field_data):
    delimiters = [",", " "]
    loaded = False
    for delimiter in delimiters:
        try:
            field_data_table = pd.read_table(StringIO(field_data), sep=delimiter)
            if {'ID', 'RA', 'Dec'}.issubset(field_data_table.columns.tolist()):
                loaded = True
            else:
                field_data_table = pd.read_table(
                    StringIO(field_data),
                    sep=delimiter,
                    names=["ID", "RA", "Dec"],
                )
                loaded = True
            if loaded:
                break
        except TypeError:
            pass

    if not loaded:
        return None
    else:
        return field_data_table.to_dict(orient='list')


def add_tiles(
    instrument_id,
    instrument_name,
    regions,
    field_data,
    references=None,
    modify=False,
    session=None,
):
    field_ids = []
    if session is None:
        if Session.registry.has():
            session = Session()
        else:
            session = Session(bind=DBSession.session_factory.kw["bind"])

    try:
        if references is not None:
            reference_filters = {}
            reference_filter_mags = {}
            for name, group in references.groupby('field'):
                reference_filters[name] = group['filter'].tolist()
                if 'limmag' in list(references.columns):
                    reference_filter_mags[name] = group['limmag'].tolist()

        # if we are only adding/modifying references, no need to modify anything else
        if field_data is None and references is not None:
            fields = (
                session.scalars(
                    sa.select(InstrumentField).where(
                        InstrumentField.instrument_id == instrument_id
                    )
                )
                .unique()
                .all()
            )
            for field in fields:
                if field.field_id in reference_filters:
                    setattr(
                        field, 'reference_filters', reference_filters[field.field_id]
                    )
                    if field.field_id in reference_filter_mags:
                        setattr(
                            field,
                            'reference_filter_mags',
                            reference_filter_mags[field.field_id],
                        )
                    session.add(field)
            session.commit()
            return

        # Loop over the telescope tiles and create fields for each
        skyoffset_frames = coordinates.SkyCoord(
            field_data['RA'], field_data['Dec'], unit=u.deg
        ).skyoffset_frame()

        # code expects to loop over regions
        if type(regions) in [RectangleSkyRegion, CircleSkyRegion, PolygonSkyRegion]:
            regions = [regions]

        ra, dec = [], []
        needs_summary = False
        for ii, reg in enumerate(regions):
            if isinstance(reg, RectangleSkyRegion):
                height = reg.height.value
                width = reg.width.value

                geometry = np.array(
                    [
                        (-width / 2.0, -height / 2.0),
                        (width / 2.0, -height / 2.0),
                        (width / 2.0, height / 2.0),
                        (-width / 2.0, height / 2.0),
                        (-width / 2.0, -height / 2.0),
                    ]
                )
                ra_tmp = geometry[:, 0]
                dec_tmp = geometry[:, 1]
            elif isinstance(reg, CircleSkyRegion):
                radius = reg.radius.value
                N = 10
                phi = np.linspace(0, 2 * np.pi, N)
                ra_tmp = radius * np.cos(phi)
                dec_tmp = radius * np.sin(phi)
            elif isinstance(reg, PolygonSkyRegion):
                ra_tmp = reg.vertices.ra
                dec_tmp = reg.vertices.dec
                needs_summary = True

            ra.append(ra_tmp)
            dec.append(dec_tmp)
        coords = np.stack([np.array(ra), np.array(dec)])

        # Copy the tile coordinates such that there is one per field
        # in the grid
        coords_icrs = coordinates.SkyCoord(
            *np.tile(coords[:, np.newaxis, ...], (len(field_data['RA']), 1, 1)),
            unit=u.deg,
            frame=skyoffset_frames[:, np.newaxis, np.newaxis],
        ).transform_to(coordinates.ICRS)

        if 'ID' in field_data:
            ids = field_data['ID']
        else:
            ids = [-1] * len(field_data['RA'])

        for ii, (field_id, ra, dec, coords) in enumerate(
            zip(ids, field_data['RA'], field_data['Dec'], coords_icrs)
        ):
            if field_id == -1:
                field = InstrumentField.query.filter(
                    InstrumentField.instrument_id == instrument_id,
                    InstrumentField.ra == ra,
                    InstrumentField.dec == dec,
                ).first()
                if field is not None:
                    field_ids.append(field.field_id)
                    continue

            # compute full contour
            geometry = []
            for coord in coords:
                tab = list(
                    zip(
                        (*coord.ra.deg, coord.ra.deg[0]),
                        (*coord.dec.deg, coord.dec.deg[0]),
                    )
                )
                geometry.append(tab)

            contour = {
                'properties': {
                    'instrument': instrument_name,
                    'field_id': int(field_id),
                    'ra': ra,
                    'dec': dec,
                },
                'type': 'FeatureCollection',
                'features': [
                    {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'MultiLineString',
                            'coordinates': geometry,
                        },
                    },
                ],
            }
            if field_id == -1:
                del contour['properties']['field_id']

            if needs_summary:
                # compute summary (bounding-box) contour
                geometry = []
                min_ra, max_ra = np.min(coords[0].ra.deg), np.max(coords[0].ra.deg)
                min_dec, max_dec = np.min(coords[0].dec.deg), np.max(coords[0].dec.deg)
                for coord in coords:
                    min_ra = min(min_ra, np.min(coord.ra.deg))
                    max_ra = max(max_ra, np.max(coord.ra.deg))
                    min_dec = min(min_dec, np.min(coord.dec.deg))
                    max_dec = max(max_dec, np.max(coord.dec.deg))
                geometry_summary = [
                    (min_ra, min_dec),
                    (max_ra, min_dec),
                    (max_ra, max_dec),
                    (min_ra, max_dec),
                    (min_ra, min_dec),
                ]

                contour_summary = {
                    'properties': {
                        'instrument': instrument_name,
                        'field_id': int(field_id),
                        'ra': ra,
                        'dec': dec,
                    },
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': geometry_summary,
                            },
                        },
                    ],
                }
                if field_id == -1:
                    del contour_summary['properties']['field_id']
            else:
                contour_summary = contour

            if field_id == -1:
                max_field_id = session.execute(
                    sa.select(sa.func.max(InstrumentField.field_id)).where(
                        InstrumentField.instrument_id == instrument_id,
                    )
                ).scalar_one()
                if max_field_id is None:
                    max_field_id = 0

                field = InstrumentField(
                    instrument_id=instrument_id,
                    contour=contour,
                    contour_summary=contour_summary,
                    ra=ra,
                    dec=dec,
                    field_id=max_field_id + 1,
                )
                session.add(field)
                session.commit()
            else:
                create_field = True
                if modify:
                    field = session.scalars(
                        sa.select(InstrumentField).where(
                            InstrumentField.instrument_id == instrument_id,
                            InstrumentField.field_id == int(field_id),
                        )
                    ).first()

                    if field is not None:
                        session.execute(
                            sa.delete(InstrumentFieldTile).where(
                                InstrumentFieldTile.instrument_id == instrument_id,
                                InstrumentFieldTile.instrument_field_id == field.id,
                            )
                        )
                        session.commit()

                        create_field = False

                if create_field:
                    field = InstrumentField(
                        instrument_id=instrument_id,
                        field_id=int(field_id),
                        contour=contour,
                        contour_summary=contour_summary,
                        ra=ra,
                        dec=dec,
                    )

                    session.add(field)
                    session.commit()
                else:
                    # we update the contour and contour_summary
                    setattr(field, 'contour', contour)
                    setattr(field, 'contour_summary', contour_summary)
                    session.add(field)
                    session.commit()

                if references is not None and field_id in reference_filters:
                    setattr(field, 'reference_filters', reference_filters[field_id])
                    if 'limmag' in list(references.columns):
                        setattr(
                            field,
                            'reference_filter_mags',
                            reference_filter_mags[field_id],
                        )
                    session.add(field)
                    session.commit()

            field_ids.append(field.field_id)

            tiles = []
            for coord in coords:
                for hpx in Tile.tiles_from_polygon_skycoord(coord):
                    tiles.append(
                        InstrumentFieldTile(
                            instrument_id=instrument_id,
                            instrument_field_id=field.id,
                            healpix=hpx,
                        )
                    )
            session.add_all(tiles)
            session.commit()

        instrument = session.scalars(
            sa.select(Instrument).where(
                Instrument.id == instrument_id,
            )
        ).first()
        if instrument is not None and len(instrument.fields) > 0:
            instrument.has_fields = True
        else:
            instrument.has_fields = False
        session.commit()

        log(f"Successfully generated fields for instrument {instrument_id}")
    except Exception as e:
        log(f"Unable to generate fields for instrument {instrument_id}: {e}")
    finally:
        Session.remove()
        return field_ids


class InstrumentFieldHandler(BaseHandler):
    @permissions(['Delete instrument'])
    def delete(self, instrument_id):
        """
        ---
        description: Delete fields associated with an instrument
        tags:
          - instruments
        parameters:
          - in: path
            name: instrument_id
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
            stmt = Instrument.select(session.user_or_token, mode="delete").where(
                Instrument.id == int(instrument_id)
            )
            instrument = session.scalars(stmt).first()
            if instrument is None:
                return self.error(f'Missing instrument with ID {instrument_id}')

            session.execute(
                sa.delete(InstrumentField).where(
                    InstrumentFieldTile.instrument_id == instrument.id,
                )
            )

            instrument = session.scalars(
                sa.select(Instrument).where(
                    Instrument.id == instrument_id,
                )
            ).first()
            if instrument is not None and len(instrument.fields) > 0:
                instrument.has_fields = True
            else:
                instrument.has_fields = False
            session.commit()

        self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
        return self.success()

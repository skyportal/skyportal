from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
from sqlalchemy.orm import joinedload, undefer
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa
from tornado.ioloop import IOLoop

from healpix_alchemy import Tile
from regions import Regions, CircleSkyRegion, RectangleSkyRegion, PolygonSkyRegion
from astropy import coordinates
from astropy.coordinates import SkyCoord
from astropy import units as u
import numpy as np
import pandas as pd
from io import StringIO

from ..base import BaseHandler
from ...models import (
    DBSession,
    GcnEvent,
    Instrument,
    InstrumentField,
    InstrumentFieldTile,
    Localization,
    LocalizationTile,
    Telescope,
)
from ...enum_types import ALLOWED_BANDPASSES

log = make_log('api/instrument')

Session = scoped_session(sessionmaker(bind=DBSession.session_factory.kw["bind"]))


class InstrumentHandler(BaseHandler):
    @permissions(['System admin'])
    def post(self):
        # See bottom of this file for redoc docstring -- moved it there so that
        # it could be made an f-string.

        data = self.get_json()
        telescope_id = data.get('telescope_id')
        telescope = Telescope.get_if_accessible_by(
            telescope_id, self.current_user, raise_if_none=True, mode="read"
        )

        field_data = data.pop("field_data", None)
        field_region = data.pop("field_region", None)

        field_fov_type = data.pop("field_fov_type", None)
        field_fov_attributes = data.pop("field_fov_attributes", None)

        if (field_region is not None) and (field_fov_type is not None):
            return self.error('must supply only one of field_region or field_fov_type')

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

        existing_instrument = (
            Instrument.query_records_accessible_by(
                self.current_user,
            )
            .filter(
                Instrument.name == data.get('name'),
                Instrument.telescope_id == telescope_id,
            )
            .first()
        )
        if existing_instrument is None:
            instrument.telescope = telescope
            DBSession().add(instrument)
            DBSession().commit()
        else:
            instrument = existing_instrument

        if field_data is not None:
            if (field_region is None) and (field_fov_type is None):
                return self.error(
                    'field_region or field_fov_type is required with field_data'
                )

            if type(field_data) is str:
                field_data = pd.read_table(StringIO(field_data), sep=",").to_dict(
                    orient='list'
                )

            if not {'ID', 'RA', 'Dec'}.issubset(field_data):
                return self.error("ID, RA, and Dec required in field_data.")

            log(f"Started generating fields for instrument {instrument.id}")
            # run async
            IOLoop.current().run_in_executor(
                None,
                lambda: add_tiles(instrument.id, instrument.name, regions, field_data),
            )

        self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
        return self.success(data={"id": instrument.id})

    @auth_or_token
    def get(self, instrument_id=None):
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

        if instrument_id is not None:
            instrument = Instrument.get_if_accessible_by(
                int(instrument_id),
                self.current_user,
                raise_if_none=True,
                mode="read",
                options=options,
            )
            data = instrument.to_dict()

            # optional: slice by GcnEvent localization
            if localization_dateobs is not None:
                if localization_name is not None:
                    localization = (
                        Localization.query_records_accessible_by(self.current_user)
                        .filter(
                            Localization.dateobs == localization_dateobs,
                            Localization.localization_name == localization_name,
                        )
                        .first()
                    )
                    if localization is None:
                        return self.error("Localization not found", status=404)
                else:
                    event = (
                        GcnEvent.query_records_accessible_by(
                            self.current_user,
                            options=[
                                joinedload(GcnEvent.localizations),
                            ],
                        )
                        .filter(GcnEvent.dateobs == localization_dateobs)
                        .first()
                    )
                    if event is None:
                        return self.error("GCN event not found", status=404)
                    localization = event.localizations[-1]

                cum_prob = (
                    sa.func.sum(
                        LocalizationTile.probdensity * LocalizationTile.healpix.area
                    )
                    .over(order_by=LocalizationTile.probdensity.desc())
                    .label('cum_prob')
                )
                localizationtile_subquery = (
                    sa.select(LocalizationTile.probdensity, cum_prob).filter(
                        LocalizationTile.localization_id == localization.id
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

                if includeGeoJSON or includeGeoJSONSummary:
                    if includeGeoJSON:
                        undefer_column = 'contour'
                    elif includeGeoJSONSummary:
                        undefer_column = 'contour_summary'
                    tiles = (
                        DBSession()
                        .execute(
                            sa.select(InstrumentField)
                            .filter(
                                LocalizationTile.localization_id == localization.id,
                                LocalizationTile.probdensity >= min_probdensity,
                                InstrumentFieldTile.instrument_id == instrument.id,
                                InstrumentFieldTile.instrument_field_id
                                == InstrumentField.id,
                                InstrumentFieldTile.healpix.overlaps(
                                    LocalizationTile.healpix
                                ),
                            )
                            .options(undefer(undefer_column))
                        )
                        .unique()
                        .all()
                    )
                else:
                    tiles = (
                        (
                            DBSession().execute(
                                sa.select(InstrumentField).filter(
                                    LocalizationTile.localization_id == localization.id,
                                    LocalizationTile.probdensity >= min_probdensity,
                                    InstrumentFieldTile.instrument_id == instrument.id,
                                    InstrumentFieldTile.instrument_field_id
                                    == InstrumentField.id,
                                    InstrumentFieldTile.healpix.overlaps(
                                        LocalizationTile.healpix
                                    ),
                                )
                            )
                        )
                        .unique()
                        .all()
                    )
                data['fields'] = [tile.to_dict() for tile, in tiles]

            return self.success(data=data)

        inst_name = self.get_query_argument("name", None)
        if includeRegion:
            options = [undefer(Instrument.region)]
        else:
            options = []
        query = Instrument.query_records_accessible_by(
            self.current_user, mode="read", options=options
        )
        if inst_name is not None:
            query = query.filter(Instrument.name == inst_name)
        instruments = query.all()
        data = [instrument.to_dict() for instrument in instruments]

        # optional: slice by GcnEvent localization
        if localization_dateobs is not None:
            if localization_name is not None:
                localization = (
                    Localization.query_records_accessible_by(self.current_user)
                    .filter(
                        Localization.dateobs == localization_dateobs,
                        Localization.localization_name == localization_name,
                    )
                    .first()
                )
                if localization is None:
                    return self.error("Localization not found", status=404)
            else:
                event = (
                    GcnEvent.query_records_accessible_by(
                        self.current_user,
                        options=[
                            joinedload(GcnEvent.localizations),
                        ],
                    )
                    .filter(GcnEvent.dateobs == localization_dateobs)
                    .first()
                )
                if event is None:
                    return self.error("GCN event not found", status=404)
                localization = event.localizations[-1]

            cum_prob = (
                sa.func.sum(
                    LocalizationTile.probdensity * LocalizationTile.healpix.area
                )
                .over(order_by=LocalizationTile.probdensity.desc())
                .label('cum_prob')
            )
            localizationtile_subquery = (
                sa.select(LocalizationTile.probdensity, cum_prob).filter(
                    LocalizationTile.localization_id == localization.id
                )
            ).subquery()

            min_probdensity = (
                sa.select(
                    sa.func.min(localizationtile_subquery.columns.probdensity)
                ).filter(
                    localizationtile_subquery.columns.cum_prob <= localization_cumprob
                )
            ).scalar_subquery()

            for ii, instrument in enumerate(instruments):
                if includeGeoJSON or includeGeoJSONSummary:
                    if includeGeoJSON:
                        undefer_column = 'contour'
                    elif includeGeoJSONSummary:
                        undefer_column = 'contour_summary'
                    tiles = (
                        DBSession()
                        .execute(
                            sa.select(InstrumentField)
                            .filter(
                                LocalizationTile.localization_id == localization.id,
                                LocalizationTile.probdensity >= min_probdensity,
                                InstrumentFieldTile.instrument_id == instrument.id,
                                InstrumentFieldTile.instrument_field_id
                                == InstrumentField.id,
                                InstrumentFieldTile.healpix.overlaps(
                                    LocalizationTile.healpix
                                ),
                            )
                            .options(undefer(undefer_column))
                        )
                        .unique()
                        .all()
                    )
                else:
                    tiles = (
                        (
                            DBSession().execute(
                                sa.select(InstrumentField).filter(
                                    LocalizationTile.localization_id == localization.id,
                                    LocalizationTile.probdensity >= min_probdensity,
                                    InstrumentFieldTile.instrument_id == instrument.id,
                                    InstrumentFieldTile.instrument_field_id
                                    == InstrumentField.id,
                                    InstrumentFieldTile.healpix.overlaps(
                                        LocalizationTile.healpix
                                    ),
                                )
                            )
                        )
                        .unique()
                        .all()
                    )
                data[ii]['fields'] = [tile.to_dict() for tile, in tiles]

        self.verify_and_commit()
        return self.success(data=data)

    @permissions(['System admin'])
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

        # permission check
        instrument = Instrument.get_if_accessible_by(
            int(instrument_id), self.current_user, mode='update'
        )
        if instrument is None:
            return self.error(f'Missing instrument with ID {instrument_id}')

        field_data = data.pop("field_data", None)
        field_region = data.pop("field_region", None)

        field_fov_type = data.pop("field_fov_type", None)
        field_fov_attributes = data.pop("field_fov_attributes", None)

        if (field_region is not None) and (field_fov_type is not None):
            return self.error('must supply only one of field_region or field_fov_type')

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
            schema.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        self.verify_and_commit()

        if field_data is not None:
            if (field_region is None) and (field_fov_type is None):
                return self.error(
                    'field_region or field_fov_type is required with field_data'
                )

            if type(field_data) is str:
                field_data = pd.read_table(StringIO(field_data), sep=",").to_dict(
                    orient='list'
                )

            if not {'ID', 'RA', 'Dec'}.issubset(field_data):
                return self.error("ID, RA, and Dec required in field_data.")

            log(f"Started generating fields for instrument {instrument.id}")
            # run async
            IOLoop.current().run_in_executor(
                None,
                lambda: add_tiles(instrument.id, instrument.name, regions, field_data),
            )

        self.push_all(action="skyportal/REFRESH_INSTRUMENTS")
        return self.success()

    @permissions(['System admin'])
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
        instrument = Instrument.get_if_accessible_by(
            int(instrument_id), self.current_user, raise_if_none=True, mode='update'
        )
        DBSession().delete(instrument)
        self.verify_and_commit()

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


def add_tiles(instrument_id, instrument_name, regions, field_data, session=Session()):
    field_ids = []

    try:
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
            if type(reg) == RectangleSkyRegion:
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
            elif type(reg) == CircleSkyRegion:
                radius = reg.radius.value
                N = 10
                phi = np.linspace(0, 2 * np.pi, N)
                ra_tmp = radius * np.cos(phi)
                dec_tmp = radius * np.sin(phi)
            elif type(reg) == PolygonSkyRegion:
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
            else:
                contour_summary = contour
            if field_id == -1:
                del contour_summary['properties']['field_id']

            if field_id == -1:
                field = InstrumentField(
                    instrument_id=instrument_id,
                    contour=contour,
                    contour_summary=contour_summary,
                    ra=ra,
                    dec=dec,
                )
            else:
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
        log(f"Successfully generated fields for instrument {instrument_id}")
    except Exception as e:
        log(f"Unable to generate fields for instrument {instrument_id}: {e}")
    finally:
        Session.remove()
        return field_ids

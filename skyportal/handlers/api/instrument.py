from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
from sqlalchemy.orm import joinedload, undefer
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy as sa
from tornado.ioloop import IOLoop

from healpix_alchemy import Tile
from regions import Regions
from astropy import coordinates
from astropy import units as u
import numpy as np

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
            if field_region is None:
                return self.error('`field_region` is required with field_data')
            regions = Regions.parse(field_region, format='ds9')

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
              name: localizationDateobs
              schema:
                type: string
              description: |
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
        if includeGeoJSON:
            options = [joinedload(Instrument.fields).undefer(InstrumentField.contour)]
        elif includeGeoJSONSummary:
            options = [
                joinedload(Instrument.fields).undefer(InstrumentField.contour_summary)
            ]
        else:
            options = []

        print(
            localization_dateobs,
            localization_name,
            localization_cumprob,
            includeGeoJSON,
            includeGeoJSONSummary,
            instrument_id,
            options,
        )

        if instrument_id is not None:
            if includeGeoJSON:
                options = [
                    joinedload(Instrument.fields).undefer(InstrumentField.contour)
                ]
            elif includeGeoJSONSummary:
                options = [
                    joinedload(Instrument.fields).undefer(
                        InstrumentField.contour_summary
                    )
                ]
            else:
                options = []

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
        query = Instrument.query_records_accessible_by(self.current_user, mode="read")
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

        print(data)

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
        _ = Instrument.get_if_accessible_by(
            int(instrument_id), self.current_user, raise_if_none=True, mode='update'
        )

        schema = Instrument.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        self.verify_and_commit()

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


def add_tiles(instrument_id, instrument_name, regions, field_data):
    session = Session()
    try:
        # Loop over the telescope tiles and create fields for each
        skyoffset_frames = coordinates.SkyCoord(
            field_data['RA'], field_data['Dec'], unit=u.deg
        ).skyoffset_frame()

        ra = np.array([reg.vertices.ra for reg in regions])
        dec = np.array([reg.vertices.dec for reg in regions])
        coords = np.stack([ra, dec])

        # Copy the tile coordinates such that there is one per field
        # in the grid
        coords_icrs = coordinates.SkyCoord(
            *np.tile(coords[:, np.newaxis, ...], (len(field_data['RA']), 1, 1)),
            unit=u.deg,
            frame=skyoffset_frames[:, np.newaxis, np.newaxis],
        ).transform_to(coordinates.ICRS)

        for ii, (field_id, ra, dec, coords) in enumerate(
            zip(field_data['ID'], field_data['RA'], field_data['Dec'], coords_icrs)
        ):

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
                            'type': 'MultiLineString',
                            'coordinates': geometry_summary,
                        },
                    },
                ],
            }

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
        return log(f"Successfully generated fields for instrument {instrument_id}")
    except Exception as e:
        return log(f"Unable to generate fields for instrument {instrument_id}: {e}")
    finally:
        Session.remove()

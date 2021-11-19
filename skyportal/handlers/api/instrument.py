from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from baselayer.log import make_log
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker, scoped_session
from tornado.ioloop import IOLoop

from healpix_alchemy import Tile
from regions import Regions
from astropy import coordinates
from astropy import units as u
import numpy as np

from ..base import BaseHandler
from ...models import (
    DBSession,
    Instrument,
    Telescope,
    InstrumentField,
    InstrumentFieldTile,
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

            # run async
            IOLoop.current().run_in_executor(
                None,
                lambda: add_tiles(instrument.id, instrument.name, regions, field_data),
            )

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
        if instrument_id is not None:
            instrument = Instrument.get_if_accessible_by(
                int(instrument_id),
                self.current_user,
                raise_if_none=True,
                mode="read",
                options=[joinedload(Instrument.fields)],
            )
            return self.success(data=instrument)

        inst_name = self.get_query_argument("name", None)
        query = Instrument.query_records_accessible_by(
            self.current_user,
            mode="read",
            options=[
                joinedload(Instrument.fields),
            ],
        )
        if inst_name is not None:
            query = query.filter(Instrument.name == inst_name)
        instruments = query.all()
        self.verify_and_commit()
        return self.success(data=instruments)

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
            log(f'Loaded field {field_id} for instrument {instrument_id}')

            contour = {
                'properties': {
                    'instrument': instrument_name,
                    'field_id': int(field_id),
                    'ra': ra,
                    'dec': dec,
                },
            }

            field = InstrumentField(
                instrument_id=instrument_id, field_id=int(field_id), contour=contour
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

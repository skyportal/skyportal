import functools
from marshmallow.exceptions import ValidationError
from sqlalchemy.orm import joinedload
from baselayer.app.access import permissions, auth_or_token
from tornado.ioloop import IOLoop

from ..base import BaseHandler
from ...models import DBSession, Instrument, InstrumentField, Telescope
from ...enum_types import ALLOWED_BANDPASSES
from ...utils.instrument import get_mocs


class InstrumentHandler(BaseHandler):
    @permissions(['System admin'])
    async def post(self):
        # See bottom of this file for redoc docstring -- moved it there so that
        # it could be made an f-string.

        data = self.get_json()
        telescope_id = data.get('telescope_id')
        telescope = Telescope.get_if_accessible_by(
            telescope_id, self.current_user, raise_if_none=True, mode="read"
        )

        field_data = data.pop("field_data", None)
        field_of_view_shape = data.pop("field_of_view_shape", None)
        field_of_view_size = data.pop("field_of_view_size", None)

        schema = Instrument.__schema__()
        try:
            instrument = schema.load(data)
        except ValidationError as exc:
            return self.error(
                'Invalid/missing parameters: ' f'{exc.normalized_messages()}'
            )
        instrument.telescope = telescope

        DBSession().add(instrument)
        self.verify_and_commit()

        if field_data is not None:
            if field_of_view_shape is None:
                return self.error('field_of_view_shape is required with field_data')
            elif field_of_view_shape in ['square', 'circle']:
                if field_of_view_size is None:
                    return self.error(
                        f'field_of_view_size is required for field_of_view_shape={field_of_view_shape}'
                    )
            elif field_of_view_shape == "ZTF":
                pass
            else:
                return self.error('field_of_view_shape must be square, circle, or ZTF')
            fields_func = functools.partial(
                add_instrument_tiles,
                instrument.id,
                self,
                field_data,
                field_of_view_shape,
                field_of_view_size,
            )
            IOLoop.current().run_in_executor(None, fields_func)

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
                options=[joinedload(Instrument.fields), joinedload(Instrument.tiles)],
            )
            return self.success(data=instrument)

        inst_name = self.get_query_argument("name", None)
        query = Instrument.query_records_accessible_by(
            self.current_user,
            mode="read",
            options=[joinedload(Instrument.fields), joinedload(Instrument.tiles)],
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


def add_instrument_tiles(
    instrument_id, request_handler, field_data, field_of_view_shape, field_of_view_size
):
    try:
        tile_args = {'instrument_id': int(instrument_id)}
        mocs = get_mocs(field_data, field_of_view_shape, field_of_view_size)
        fields = [
            InstrumentField.from_moc(moc, field_id=int(field_id), tile_args=tile_args)
            for field_id, moc in zip(field_data['ID'], mocs)
        ]
        for field in fields:
            field.instrument_id = int(instrument_id)
            DBSession().add(field)
        request_handler.verify_and_commit()
    except Exception as e:
        return request_handler.error(f"Unable to generate MOC tiles: {e}")
    finally:
        DBSession.remove()

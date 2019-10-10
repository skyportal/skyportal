from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Instrument, Telescope


class InstrumentHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Create instruments
        parameters:
          - in: path
            name: instrument
            schema: Instrument
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - Success
                    - type: object
                      properties:
                        id:
                          type: integer
                          description: New instrument ID
        """
        data = self.get_json()
        telescope_id = data.pop('telescope_id')
        telescope = Telescope.query.get(telescope_id)
        if not telescope:
            return self.error('Invalid telescope ID.')

        schema = Instrument.__schema__()
        try:
            instrument = schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        instrument.telescope = telescope
        DBSession.add(instrument)
        DBSession().commit()

        return self.success(data={"id": instrument.id})

    @auth_or_token
    def get(self, instrument_id):
        info = {}
        info['instrument'] = Instrument.query.get(int(instrument_id))

        if info['instrument'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load instrument {instrument_id}",
                              data={"instrument_id": instrument_id})

    @permissions(['Manage sources'])
    def put(self, instrument_id):
        data = self.get_json()
        data['id'] = int(instrument_id)

        schema = Instrument.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, instrument_id):
        DBSession.query(Instrument).filter(Instrument.id == int(instrument_id)).delete()
        DBSession().commit()

        return self.success()

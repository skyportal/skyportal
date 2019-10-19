import tornado.web
from sqlalchemy.orm import joinedload
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from .base import BaseHandler
from ..models import DBSession, Spectrum, Comment, Instrument, Source


class SpectrumHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload spectrum
        parameters:
          - in: path
            name: spectrum
            schema: Spectrum
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
                          description: New spectrum ID
        """
        data = self.get_json()
        source_id = data.pop('source_id')
        instrument_id = data.pop('instrument_id')
        source = Source.query.get(source_id)
        instrument = Instrument.query.get(instrument_id)

        schema = Spectrum.__schema__()
        try:
            spec = schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        spec.source = source
        spec.instrument = instrument
        DBSession().add(spec)
        DBSession().commit()

        return self.success(data={"id": spec.id})

    @auth_or_token
    def get(self, spectrum_id):
        """
        ---
        description: Retrieve a spectrum
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleSpectrum
          400:
            content:
              application/json:
                schema: Error
        """
        info = {}
        info['spectrum'] = Spectrum.query.get(spectrum_id)

        if info['spectrum'] is not None:
            return self.success(data=info)
        else:
            return self.error(f"Could not load spectrum {spectrum_id}",
                              data={"spectrum_id": spectrum_id})

    @permissions(['Manage sources'])
    def put(self, spectrum_id):
        """
        ---
        description: Update spectrum
        parameters:
          - in: path
            name: spectrum
            schema: Spectrum
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
        data['id'] = spectrum_id

        schema = Spectrum.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')
        DBSession().commit()

        return self.success()

    @permissions(['Manage sources'])
    def delete(self, spectrum_id):
        """
        ---
        description: Delete a spectrum
        parameters:
          - in: path
            name: spectrum_id
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
        s = Spectrum.query.get(spectrum_id)
        DBSession().delete(s)
        DBSession().commit()

        return self.success()

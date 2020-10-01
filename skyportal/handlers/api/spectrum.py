import io
from pathlib import Path

from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Group,
    Instrument,
    Obj,
    Source,
    Spectrum,
    FollowupRequest,
)
from ...schema import SpectrumAsciiFilePostJSON


class SpectrumHandler(BaseHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload spectrum
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/SpectrumNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: Group IDs that spectrum will be associated with
                    required:
                      - group_ids
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
                              description: New spectrum ID
          400:
            content:
              application/json:
                schema: Error
        """
        data = self.get_json()
        instrument_id = data.get('instrument_id')
        if isinstance(instrument_id, list):
            if not all(instrument == instrument_id[0] for instrument in instrument_id):
                return self.error('Can only upload data for one instrument at a time')
            else:
                instrument_id = instrument_id[0]
        try:
            group_ids = data.pop("group_ids")
        except KeyError:
            return self.error("Missing required field: group_ids")
        groups = Group.query.filter(Group.id.in_(group_ids)).all()

        instrument = Instrument.query.get(instrument_id)

        schema = Spectrum.__schema__()
        try:
            spec = schema.load(data)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        spec.instrument = instrument
        spec.groups = groups
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
        spectrum = Spectrum.query.get(spectrum_id)

        if spectrum is not None:
            # Permissions check
            _ = Source.get_obj_if_owned_by(spectrum.obj_id, self.current_user)
            return self.success(data=spectrum)
        else:
            return self.error(f"Could not load spectrum with ID {spectrum_id}")

    @permissions(['Manage sources'])
    def put(self, spectrum_id):
        """
        ---
        description: Update spectrum
        parameters:
          - in: path
            name: spectrum_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema: SpectrumNoID
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
        spectrum = Spectrum.query.get(spectrum_id)
        # Permissions check
        _ = Source.get_obj_if_owned_by(spectrum.obj_id, self.current_user)
        data = self.get_json()
        data['id'] = spectrum_id

        schema = Spectrum.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
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
        spectrum = Spectrum.query.get(spectrum_id)
        # Permissions check
        _ = Source.get_obj_if_owned_by(spectrum.obj_id, self.current_user)
        DBSession().delete(spectrum)
        DBSession().commit()

        return self.success()


class ASCIIHandler:
    def spec_from_ascii_request(self):
        """Helper method to read in Spectrum objects from ASCII POST."""
        json = self.get_json()

        try:
            json = SpectrumAsciiFilePostJSON.load(json)
        except ValidationError as e:
            raise ValidationError(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )

        obj = Source.get_obj_if_owned_by(json['obj_id'], self.current_user)
        if obj is None:
            raise ValidationError('Invalid Obj id.')

        instrument = Instrument.query.get(json['instrument_id'])
        if instrument is None:
            raise ValidationError('Invalid instrument id.')

        groups = []
        group_ids = json.pop('group_ids')
        for group_id in group_ids:
            group = Group.query.get(group_id)
            if group is None:
                return self.error(f'Invalid group id: {group_id}.')
            groups.append(group)

        followup_request_id = json.pop('followup_request_id')
        if followup_request_id is not None:
            followup_request = FollowupRequest.get_if_owned_by(
                self.current_user, followup_request_id
            )

            if followup_request is None:
                return self.error('Invalid Followup Request ID.')
            for group in followup_request.target_groups:
                groups.append(group)

        # keep only unique groups - must be a list for sqlalchemy
        groups = list(set(groups))

        filename = json.pop('filename')
        ascii = json.pop('ascii')

        # maximum size 10MB - above this don't parse. Assuming ~1 byte / char
        if len(ascii) > 1e7:
            raise ValueError('File must be smaller than 200,000,000 characters.')

        # pass ascii in as a file-like object
        file = io.BytesIO(ascii.encode('ascii'))
        spec = Spectrum.from_ascii(file, **json)

        spec.original_file_filename = Path(filename).name
        spec.original_file_string = ascii

        spec.groups = groups
        return spec


class SpectrumASCIIFileHandler(BaseHandler, ASCIIHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Upload spectrum from ASCII file
        requestBody:
          content:
            application/json:
              schema: SpectrumAsciiFilePostJSON
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
                              description: New spectrum ID
          400:
            content:
              application/json:
                schema: Error
        """

        try:
            spec = self.spec_from_ascii_request()
        except Exception as e:
            return self.error(f'Error parsing spectrum: {e.args[0]}')
        DBSession().add(spec)
        DBSession().commit()
        return self.success(data={'id': spec.id})


class SpectrumASCIIFileParser(BaseHandler, ASCIIHandler):
    @permissions(['Upload data'])
    def post(self):
        """
        ---
        description: Parse spectrum from ASCII file
        requestBody:
          content:
            application/json:
              schema: SpectrumAsciiFilePostJSON
        responses:
          200:
            content:
              application/json:
                schema: SpectrumNoID
          400:
            content:
              application/json:
                schema: Error
        """

        spec = self.spec_from_ascii_request()
        return self.success(data=spec)


class ObjSpectraHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve all spectra associated with an Object
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
            description: ID of the object to retrieve spectra for
        responses:
          200:
            content:
              application/json:
                schema: ArrayOfSpectrums
          400:
            content:
              application/json:
                schema: Error
        """

        obj = Obj.query.get(obj_id)
        if obj is None:
            return self.error('Invalid object ID.')
        spectra = Obj.get_spectra_owned_by(obj_id, self.current_user)
        return_values = []
        for spec in spectra:
            spec_dict = spec.to_dict()
            spec_dict["instrument_name"] = spec.instrument.name
            spec_dict["groups"] = spec.groups
            return_values.append(spec_dict)
        return self.success(data=return_values)

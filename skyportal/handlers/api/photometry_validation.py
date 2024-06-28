from marshmallow import Schema, fields, validates_schema
from marshmallow.exceptions import ValidationError

from baselayer.app.env import load_env
from baselayer.app.access import permissions
from ..base import BaseHandler

from ...models import Photometry, PhotometryValidation

_, cfg = load_env()

USE_PHOTOMETRY_VALIDATION = cfg.get("misc.photometry_validation", False)


class Validator(Schema):
    method = fields.Str(required=True)
    photometry_id = fields.Integer()
    validated = fields.Boolean(
        truthy=['true', 'True', 'validated', True],
        falsy=['false', 'False', 'rejected', False],
        required=False,
    )
    explanation = fields.String(required=False)
    notes = fields.String(required=False)

    @validates_schema
    def validate_requires(self, data, **kwargs):
        if 'method' not in data:
            raise ValidationError('method is required')
        if data['method'] not in ['POST', 'PATCH', 'DELETE']:
            raise ValidationError('method must be one of POST, PATCH or DELETE')
        if data['method'] in ['PATCH', 'DELETE', 'POST']:
            if 'photometry_id' not in data:
                raise ValidationError('Missing required fields')
            if data['photometry_id'] is None:
                raise ValidationError('Missing required fields')


class PhotometryValidationHandler(BaseHandler):
    @permissions(['Manage sources'])
    async def post(self, photometry_id):
        """
        ---
        description: Validate or reject a photometric point based on data quality (e.g. examining quality of the image and/or reduction)
        tags:
          - photometryvalidations
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: int
            description: Photometry ID
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  validated:
                    type: boolean
                    description: Whether the source is validated (True) or rejected (False)
                required:
                  - validated
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
                              type: int
                              description: The id of the photomety_validation
          400:
            content:
              application/json:
                schema: Error

        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error('Photometry validation is not enabled.')

        data = self.get_json()

        validated = data.get('validated')
        explanation = data.get('explanation')
        notes = data.get('notes')

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'POST',
            'photometry_id': photometry_id,
        }
        if validated is not None:
            params_to_be_validated["validated"] = validated

        if explanation is not None:
            params_to_be_validated["explanation"] = explanation
        if notes is not None:
            params_to_be_validated["notes"] = notes

        try:
            validator = validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        validated = validator.get('validated', None)
        with self.Session() as session:
            phot = session.scalars(
                Photometry.select(session.user_or_token).where(
                    Photometry.id == photometry_id
                )
            ).first()

            if phot is None:
                return self.error(
                    f'Cannot find photometry point with ID: {photometry_id}.'
                )

            stmt = PhotometryValidation.select(session.user_or_token).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = session.scalars(stmt).first()
            if photometry_validation:
                # if the status and explanation are the same, do nothing
                if (
                    photometry_validation.validated == validated
                    and photometry_validation.explanation == explanation
                    and photometry_validation.notes == notes
                ):
                    # Everything already up-to-date!
                    return self.success(data={'id': photometry_validation.id})
                # otherwise, update the status and explanation
                else:
                    photometry_validation.validated = validated
                    photometry_validation.validator_id = self.associated_user_object.id
                    if explanation is not None:
                        photometry_validation.explanation = explanation
                    if notes is not None:
                        photometry_validation.notes = notes
                    session.commit()
            else:
                photometry_validation = PhotometryValidation(
                    photometry_id=photometry_id,
                    validated=validated,
                    validator_id=self.associated_user_object.id,
                )
                if explanation is not None:
                    photometry_validation.explanation = explanation
                if notes is not None:
                    photometry_validation.notes = notes
                session.add(photometry_validation)
                session.commit()

            self.push_all(
                action='skyportal/REFRESH_SOURCE_PHOTOMETRY',
                payload={'obj_id': phot.obj.id},
            )
            return self.success(data={'id': photometry_validation.id})

    @permissions(['Manage sources'])
    def patch(self, photometry_id):
        """
        ---
        description: Update the validated or rejected status of a source in a GCN
        tags:
          - photometryvalidations
        parameters:
          - in: path
            name: photometry_id
            required: true
            schema:
              type: int
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  validated:
                    type: boolean
                    description: Whether the photometry is validated (True) or rejected (False)
                required:
                  - validated

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
                              type: int
                              description: The id of the modified photometry_validation
          400:
            content:
              application/json:
                schema: Error
        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error('Photometry validation is not enabled.')

        data = self.get_json()
        validated = data.get('validated')
        explanation = data.get('explanation')
        notes = data.get('notes')

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'PATCH',
            'photometry_id': photometry_id,
        }

        if validated is not None:
            params_to_be_validated["validated"] = validated
        if explanation is not None:
            params_to_be_validated["explanation"] = explanation
        if notes is not None:
            params_to_be_validated["notes"] = notes

        try:
            validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        with self.Session() as session:
            stmt = PhotometryValidation.select(
                session.user_or_token, mode="update"
            ).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = session.scalars(stmt).first()

            if not photometry_validation:
                return self.error("Photometry is not validated/rejected")

            photometry_validation.validated = validated
            photometry_validation.validator_id = self.associated_user_object.id
            if explanation is not None:
                photometry_validation.explanation = explanation
            if notes is not None:
                photometry_validation.notes = notes
            session.commit()

            self.push_all(
                action='skyportal/REFRESH_SOURCE_PHOTOMETRY',
                payload={'obj_id': photometry_validation.photometry.obj.id},
            )
            return self.success(data={'id': photometry_validation.id})

    @permissions(['Manage sources'])
    def delete(self, photometry_id):
        """
        ---
        description: |
          Deletes the validated or rejected status of a photometric point.
          Its status can be considered as 'undefined'.
        tags:
          - photometryvalidations
        parameters:
          - in: path
            name: photometric_id
            required: true
            schema:
              type: int
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
                              type: int
                              description: The id of the deleted photometry_validation
          400:
            content:
              application/json:
                schema: Error
        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error('Photometry validation is not enabled.')

        validator_instance = Validator()
        params_to_be_validated = {
            'method': 'DELETE',
            'photometry_id': photometry_id,
        }
        try:
            validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f'Error parsing query params: {e.args[0]}.')

        with self.Session() as session:
            stmt = PhotometryValidation.select(
                session.user_or_token, mode="delete"
            ).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = session.scalars(stmt).first()

            if not photometry_validation:
                return self.error("Photometry is not validated/rejected")

            obj_id = photometry_validation.photometry.obj.id
            photometry_validation_id = photometry_validation.id

            session.delete(photometry_validation)
            session.commit()

            self.push_all(
                action='skyportal/REFRESH_SOURCE_PHOTOMETRY',
                payload={'obj_id': obj_id},
            )
            return self.success(data={'id': photometry_validation_id})

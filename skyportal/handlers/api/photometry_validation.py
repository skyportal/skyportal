from typing import Annotated

import sqlalchemy as sa
from marshmallow import Schema, fields, validates_schema
from marshmallow.exceptions import ValidationError
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from skyportal_py_models.photometry import PhotometryValidationResponse

from baselayer.app.access import permissions
from baselayer.app.env import load_env

from ...models import Photometry, PhotometryValidation
from ..base import BaseHandler

_, cfg = load_env()

USE_PHOTOMETRY_VALIDATION = cfg.get("misc.photometry_validation", False)


def _coerce_validated(value):
    # Mirror the marshmallow Validator's truthy/falsy coercion so the wire
    # contract is unchanged: the status strings "validated"/"rejected" are
    # accepted in addition to booleans (pydantic's native bool validation
    # handles "true"/"false" and actual booleans).
    if value == "validated":
        return True
    if value == "rejected":
        return False
    return value


ValidatedField = Annotated[bool | None, BeforeValidator(_coerce_validated)]


class PhotometryValidationPostBody(BaseModel):
    """Request body for validating/rejecting a photometry point."""

    model_config = ConfigDict(extra="forbid")

    validated: ValidatedField = Field(
        default=None,
        description="Whether the photometry is validated (True) or rejected "
        "(False). The strings 'validated'/'rejected' are also accepted; null "
        "leaves the status ambiguous.",
    )
    explanation: str | None = Field(
        default=None,
        description="Explanation for the validation/rejection decision.",
    )
    notes: str | None = Field(
        default=None, description="Free-form notes about the validation."
    )
    magsys: str | None = Field(
        default=None,
        description="Magnitude system used for the frontend photometry refresh.",
    )


class Validator(Schema):
    method = fields.Str(required=True)
    photometry_id = fields.Integer()
    validated = fields.Boolean(
        truthy=["true", "True", "validated", True],
        falsy=["false", "False", "rejected", False],
        required=False,
    )
    explanation = fields.String(required=False)
    notes = fields.String(required=False)

    @validates_schema
    def validate_requires(self, data, **kwargs):
        if "method" not in data:
            raise ValidationError("method is required")
        if data["method"] not in ["POST", "PATCH", "DELETE"]:
            raise ValidationError("method must be one of POST, PATCH or DELETE")
        if data["method"] in ["PATCH", "DELETE", "POST"]:
            if "photometry_id" not in data:
                raise ValidationError("Missing required fields")
            if data["photometry_id"] is None:
                raise ValidationError("Missing required fields")


class PhotometryValidationHandler(BaseHandler):
    @permissions(["Manage sources"])
    async def post(
        self, photometry_id: int, *, body: PhotometryValidationPostBody = None
    ) -> PhotometryValidationResponse:
        """
        ---
        summary: Validate/Reject a photometry point
        description: Validate or reject a photometric point based on data quality (e.g. examining quality of the image and/or reduction)
        tags:
          - photometry
        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error("Photometry validation is not enabled.")

        body = self.parse_body(PhotometryValidationPostBody)

        validated = body.validated
        explanation = body.explanation
        notes = body.notes
        magsys = body.magsys

        validator_instance = Validator()
        params_to_be_validated = {
            "method": "POST",
            "photometry_id": photometry_id,
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
            return self.error(f"Error parsing query params: {e.args[0]}.")

        validated = validator.get("validated", None)
        async with self.AsyncSession() as session:
            phot = await session.scalar(
                Photometry.select(session.user_or_token).where(
                    Photometry.id == photometry_id
                )
            )

            if phot is None:
                return self.error(
                    f"Cannot find photometry point with ID: {photometry_id}."
                )

            stmt = PhotometryValidation.select(session.user_or_token).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = await session.scalar(stmt)
            if photometry_validation:
                # if the status and explanation are the same, do nothing
                if (
                    photometry_validation.validated == validated
                    and photometry_validation.explanation == explanation
                    and photometry_validation.notes == notes
                ):
                    # Everything already up-to-date!
                    return self.success(data={"id": photometry_validation.id})
                # otherwise, update the status and explanation
                else:
                    photometry_validation.validated = validated
                    photometry_validation.validator_id = self.associated_user_object.id
                    if explanation is not None:
                        photometry_validation.explanation = explanation
                    if notes is not None:
                        photometry_validation.notes = notes
                    await session.commit()
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
                await session.commit()

            # Use the FK directly to avoid a lazy load on phot.obj.
            self.push_all(
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": phot.obj_id, "magsys": magsys},
            )
            return self.success(data={"id": photometry_validation.id})

    @permissions(["Manage sources"])
    async def patch(
        self, photometry_id: int, *, body: PhotometryValidationPostBody = None
    ) -> PhotometryValidationResponse:
        """
        ---
        summary: Update the validated/rejected status of a photometry point
        description: Update the validated or rejected status of a source in a GCN
        tags:
          - photometry
        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error("Photometry validation is not enabled.")

        body = self.parse_body(PhotometryValidationPostBody)
        validated = body.validated
        explanation = body.explanation
        notes = body.notes
        magsys = body.magsys

        validator_instance = Validator()
        params_to_be_validated = {
            "method": "PATCH",
            "photometry_id": photometry_id,
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
            return self.error(f"Error parsing query params: {e.args[0]}.")

        async with self.AsyncSession() as session:
            stmt = PhotometryValidation.select(
                session.user_or_token, mode="update"
            ).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = await session.scalar(stmt)

            if not photometry_validation:
                return self.error("Photometry is not validated/rejected")

            photometry_validation.validated = validated
            photometry_validation.validator_id = self.associated_user_object.id
            if explanation is not None:
                photometry_validation.explanation = explanation
            if notes is not None:
                photometry_validation.notes = notes
            await session.commit()

            # Resolve the obj_id from the Photometry FK without triggering
            # a lazy load on photometry_validation.photometry.obj.
            phot_obj_id = await session.scalar(
                sa.select(Photometry.obj_id).where(
                    Photometry.id == photometry_validation.photometry_id
                )
            )
            self.push_all(
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": phot_obj_id, "magsys": magsys},
            )
            return self.success(data={"id": photometry_validation.id})

    @permissions(["Manage sources"])
    async def delete(self, photometry_id: int):
        """
        ---
        summary: Delete the validated/rejected status of a photometry point
        description: |
          Deletes the validated or rejected status of a photometric point.
          Its status can be considered as 'undefined'.
        tags:
          - photometry
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
                              description: The id of the deleted photometry_validation
          400:
            content:
              application/json:
                schema: Error
        """
        if not USE_PHOTOMETRY_VALIDATION:
            return self.error("Photometry validation is not enabled.")

        validator_instance = Validator()
        params_to_be_validated = {
            "method": "DELETE",
            "photometry_id": photometry_id,
        }
        try:
            validator_instance.load(params_to_be_validated)
        except ValidationError as e:
            return self.error(f"Error parsing query params: {e.args[0]}.")

        async with self.AsyncSession() as session:
            stmt = PhotometryValidation.select(
                session.user_or_token, mode="delete"
            ).where(
                PhotometryValidation.photometry_id == photometry_id,
            )
            photometry_validation = await session.scalar(stmt)

            if not photometry_validation:
                return self.error("Photometry is not validated/rejected")

            obj_id = await session.scalar(
                sa.select(Photometry.obj_id).where(
                    Photometry.id == photometry_validation.photometry_id
                )
            )
            photometry_validation_id = photometry_validation.id

            await session.delete(photometry_validation)
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE_PHOTOMETRY",
                payload={"obj_id": obj_id},
            )
            return self.success(data={"id": photometry_validation_id})

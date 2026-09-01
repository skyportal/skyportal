import time
from typing import Annotated

from marshmallow.exceptions import ValidationError
from pydantic import Field
from skyportal_py_models.annotations import (
    AnnotationPostBody,
    AnnotationPostResponse,
    AnnotationPutBody,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from baselayer.app.access import auth_or_token, permissions
from baselayer.log import make_log

from ...models import (
    Annotation,
    AnnotationOnPhotometry,
    AnnotationOnSpectrum,
    Group,
    Obj,
    Photometry,
    Spectrum,
)
from ...utils.sizeof import SIZE_WARNING_THRESHOLD, sizeof
from ..base import BaseHandler

AssociatedResourceType = Annotated[
    str,
    Field(
        description='What underlying data the annotation is on: must be one of "sources", "spectra", or "photometry."'
    ),
]
ResourceId = Annotated[
    str,
    Field(
        description="The ID of the underlying data. This would be a string for an object ID, or an integer for other data types, e.g., a spectrum."
    ),
]

log = make_log("api/annotation")


def _coerce_resource_id(associated_resource_type, resource_id):
    """Cast the resource_id from the URL path to the appropriate type for the
    target column. obj_id is a string; spectrum_id and photometry_id are
    integers (psycopg3 requires strict binding).
    """
    if associated_resource_type.lower() == "sources":
        return resource_id
    try:
        return int(resource_id)
    except (TypeError, ValueError):
        return None


class AnnotationHandler(BaseHandler):
    def get_associated_resource(self, associated_resource_type):
        associated_resource_type = associated_resource_type.lower()
        associated_resource_types = {
            "sources": {
                "class": Annotation,
                "id_attr": "obj_id",
                "obj_associated": True,
            },
            "spectra": {
                "class": AnnotationOnSpectrum,
                "id_attr": "spectrum_id",
                "obj_associated": True,
            },
            "photometry": {
                "class": AnnotationOnPhotometry,
                "id_attr": "photometry_id",
                "obj_associated": True,
            },
        }
        if associated_resource_type not in associated_resource_types:
            return self.error(
                f'Unsupported associated resource type "{associated_resource_type}".'
            )

        return associated_resource_types[associated_resource_type]

    @auth_or_token
    async def get(
        self,
        associated_resource_type: AssociatedResourceType,
        resource_id: ResourceId,
        annotation_id: int | None = None,
    ):
        """
        ---
        single:
          summary: Get an annotation
          description: Retrieve an annotation
          tags:
            - annotations
            - sources
            - spectra
          responses:
            200:
              content:
                application/json:
                  schema: SingleAnnotation
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          summary: Get all annotations
          description: Retrieve all annotations associated with specified resource
          tags:
            - annotations
            - sources
            - spectra
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfAnnotations
            400:
              content:
                application/json:
                  schema: Error
        """

        start = time.time()

        associated_resource = self.get_associated_resource(associated_resource_type)

        coerced_resource_id = _coerce_resource_id(associated_resource_type, resource_id)
        if coerced_resource_id is None:
            return self.error(f"Invalid resource_id: {resource_id}")

        async with self.AsyncSession() as session:
            if annotation_id is None:
                result = await session.scalars(
                    associated_resource["class"]
                    .select(self.current_user)
                    .options(selectinload(associated_resource["class"].groups))
                    .where(
                        getattr(
                            associated_resource["class"],
                            associated_resource["id_attr"],
                        )
                        == coerced_resource_id
                    )
                )
                annotations = result.unique().all()
                query_output = [a.to_dict() for a in annotations]
                query_size = sizeof(query_output)
                if query_size >= SIZE_WARNING_THRESHOLD:
                    end = time.time()
                    duration = end - start
                    log(
                        f"User {self.associated_user_object.id} annotation query returned {query_size} bytes in {duration} seconds"
                    )
                return self.success(data=query_output)

            try:
                annotation_id = int(annotation_id)
            except (TypeError, ValueError):
                return self.error(
                    "Must provide a valid (scalar integer) annotation ID."
                )

            annotation = await session.scalar(
                associated_resource["class"]
                .select(self.current_user)
                .options(selectinload(associated_resource["class"].groups))
                .where(associated_resource["class"].id == annotation_id)
            )
            if annotation is None:
                return self.error(
                    "Could not find any accessible annotations.", status=403
                )

            if str(getattr(annotation, associated_resource["id_attr"])) != resource_id:
                return self.error(
                    f"Annotation resource ID does not match resource ID given in path ({resource_id})"
                )

            query_output = annotation.to_dict()
            query_size = sizeof(query_output)
            if query_size >= SIZE_WARNING_THRESHOLD:
                end = time.time()
                duration = end - start
                log(
                    f"User {self.associated_user_object.id} annotation query returned {query_size} bytes in {duration} seconds"
                )

            return self.success(data=query_output)

    @permissions(["Annotate"])
    async def post(
        self,
        associated_resource_type: AssociatedResourceType,
        resource_id: ResourceId,
        *,
        body: AnnotationPostBody = None,
    ) -> AnnotationPostResponse:
        """
        ---
        summary: Post an annotation
        description: Post an annotation
        tags:
          - annotations
        """
        body = self.parse_body(AnnotationPostBody)
        origin = body.origin
        annotation_data = body.data
        group_ids = body.group_ids or [
            g.id for g in self.current_user.accessible_groups
        ]
        data = {"origin": origin, "data": annotation_data}

        async with self.AsyncSession() as session:
            author_id = self.associated_user_object.id
            groups_result = await session.scalars(
                Group.select(self.current_user).where(Group.id.in_(group_ids))
            )
            groups = list(groups_result.all())
            if {g.id for g in groups} != set(group_ids):
                return self.error(
                    f"Cannot find one or more groups with IDs: {group_ids}."
                )

            if associated_resource_type.lower() == "sources":
                data["obj_id"] = resource_id
                schema = Annotation.__schema__(exclude=["author_id"])
                try:
                    schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )

                annotation = Annotation(
                    data=annotation_data,
                    obj_id=resource_id,
                    origin=origin,
                    author_id=author_id,
                    groups=groups,
                )
            elif associated_resource_type.lower() == "spectra":
                try:
                    spectrum_id = int(resource_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid spectrum id: {resource_id}")
                spectrum = await session.scalar(
                    Spectrum.select(session.user_or_token).where(
                        Spectrum.id == spectrum_id
                    )
                )
                if not spectrum:
                    return self.error(
                        f"Could not access spectrum {resource_id}.", status=403
                    )
                data["spectrum_id"] = spectrum_id
                data["obj_id"] = spectrum.obj_id
                schema = AnnotationOnSpectrum.__schema__(exclude=["author_id"])
                try:
                    schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )

                annotation = AnnotationOnSpectrum(
                    data=annotation_data,
                    spectrum_id=spectrum_id,
                    obj_id=spectrum.obj_id,
                    origin=origin,
                    author_id=author_id,
                    groups=groups,
                )
            elif associated_resource_type.lower() == "photometry":
                try:
                    photometry_id = int(resource_id)
                except (TypeError, ValueError):
                    return self.error(f"Invalid photometry id: {resource_id}")
                photometry = await session.scalar(
                    Photometry.select(session.user_or_token).where(
                        Photometry.id == photometry_id
                    )
                )
                if not photometry:
                    return self.error(
                        f"Could not access photometry {resource_id}.", status=403
                    )
                data["photometry_id"] = photometry_id
                data["obj_id"] = photometry.obj_id
                schema = AnnotationOnPhotometry.__schema__(exclude=["author_id"])
                try:
                    schema.load(data)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )

                annotation = AnnotationOnPhotometry(
                    data=annotation_data,
                    photometry_id=photometry_id,
                    obj_id=photometry.obj_id,
                    origin=origin,
                    author_id=author_id,
                    groups=groups,
                )
            else:
                return self.error(
                    f'Unknown resource type "{associated_resource_type}".'
                )

            session.add(annotation)

            try:
                await session.commit()
            except IntegrityError as e:
                if 'is not present in table "objs"' in str(e).lower():
                    return self.error(f"Obj {resource_id} not found", status=404)
                return self.error(f"Annotation already exists: {str(e)}")

            if isinstance(
                annotation, Annotation | AnnotationOnSpectrum
            ):  # annotation on object or object related data
                obj = await session.scalar(
                    Obj.select(session.user_or_token).where(Obj.id == annotation.obj_id)
                )
                if obj is not None:
                    self.push_all(
                        action="skyportal/REFRESH_SOURCE",
                        payload={"obj_key": obj.internal_key},
                    )
                    if isinstance(annotation, AnnotationOnSpectrum):
                        self.push_all(
                            action="skyportal/REFRESH_SOURCE_SPECTRA",
                            payload={"obj_internal_key": obj.internal_key},
                        )
            return self.success(data={"annotation_id": annotation.id})

    @permissions(["Annotate"])
    async def put(
        self,
        associated_resource_type: AssociatedResourceType,
        resource_id: ResourceId,
        annotation_id: int,
        *,
        body: AnnotationPutBody = None,
    ):
        """
        ---
        summary: Update an annotation
        description: Update an annotation
        tags:
          - annotations
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
        body = self.parse_body(AnnotationPutBody)

        try:
            annotation_id = int(annotation_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) annotation ID. ")

        associated_resource = self.get_associated_resource(associated_resource_type)

        async with self.AsyncSession() as session:
            a = await session.scalar(
                associated_resource["class"]
                .select(self.current_user, mode="update")
                .options(selectinload(associated_resource["class"].groups))
                .where(associated_resource["class"].id == annotation_id)
            )
            if a is None:
                return self.error(
                    "Could not find any accessible annotations.", status=403
                )

            group_ids = body.group_ids

            if body.data is not None:
                a.data = body.data

            if body.origin is not None:
                a.origin = body.origin

            if group_ids is not None:
                groups_result = await session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                )
                groups = groups_result.all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f"Cannot find one or more groups with IDs: {group_ids}."
                    )
                a.groups = list(groups)

            if str(getattr(a, associated_resource["id_attr"])) != resource_id:
                return self.error(
                    f"Annotation resource ID does not match resource ID given in path ({resource_id})"
                )

            session.add(a)
            await session.commit()

            if associated_resource[
                "obj_associated"
            ]:  # annotation on object, or object related resources
                obj = await session.scalar(
                    Obj.select(session.user_or_token).where(Obj.id == a.obj_id)
                )
                if obj is not None:
                    self.push_all(
                        action="skyportal/REFRESH_SOURCE",
                        payload={"obj_key": obj.internal_key},
                    )
                    if isinstance(a, AnnotationOnSpectrum):
                        self.push_all(
                            action="skyportal/REFRESH_SOURCE_SPECTRA",
                            payload={"obj_internal_key": obj.internal_key},
                        )

            return self.success()

    @permissions(["Annotate"])
    async def delete(
        self,
        associated_resource_type: AssociatedResourceType,
        resource_id: ResourceId,
        annotation_id: int,
    ):
        """
        ---
        summary: Delete an annotation
        description: Delete an annotation
        tags:
          - annotations
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        try:
            annotation_id = int(annotation_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid annotation ID. ")

        associated_resource = self.get_associated_resource(associated_resource_type)

        async with self.AsyncSession() as session:
            a = await session.scalar(
                associated_resource["class"]
                .select(self.current_user, mode="delete")
                .where(associated_resource["class"].id == annotation_id)
            )

            if a is None:
                return self.error(
                    "Could not find any accessible annotations.", status=403
                )

            if str(getattr(a, associated_resource["id_attr"])) != resource_id:
                return self.error(
                    f"Annotation resource ID does not match resource ID given in path ({resource_id})"
                )

            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == a.obj_id)
            )
            obj_key = obj.internal_key if obj is not None else None
            is_spectrum_annotation = isinstance(a, AnnotationOnSpectrum)

            await session.delete(a)
            await session.commit()

            if associated_resource["obj_associated"] and obj_key is not None:
                # annotation on object, or object related resources
                self.push_all(
                    action="skyportal/REFRESH_SOURCE", payload={"obj_key": obj_key}
                )

            if is_spectrum_annotation and obj_key is not None:
                self.push_all(
                    action="skyportal/REFRESH_SOURCE_SPECTRA",
                    payload={"obj_internal_key": obj_key},
                )

            return self.success()

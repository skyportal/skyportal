import re
from typing import Mapping
from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError

from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Annotation, Spectrum, AnnotationOnSpectrum, Group


class AnnotationHandler(BaseHandler):
    def get_associated_resource(self, associated_resource_type):
        associated_resource_type = associated_resource_type.lower()
        associated_resource_types = {
            "sources": {
                "class": Annotation,
                "id_attr": 'obj_id',
                "obj_associated": True,
            },
            "spectra": {
                "class": AnnotationOnSpectrum,
                "id_attr": 'spectrum_id',
                "obj_associated": True,
            },
        }
        if associated_resource_type not in associated_resource_types:
            return self.error(
                f'Unsupported associated resource type "{associated_resource_type}".'
            )

        return associated_resource_types[associated_resource_type]

    @auth_or_token
    def get(self, associated_resource_type, resource_id, annotation_id=None):
        """
        ---
        single:
          description: Retrieve an annotation
          tags:
            - annotations
            - sources
            - spectra
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources, spectra]
              description: |
                 What underlying data the annotation is on:
                 must be one of either "sources" or "spectra".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
              description: |
                 The ID of the underlying data.
                 This would be a string for a source ID
                 or an integer for other data types like spectra.
            - in: path
              name: annotation_id
              required: true
              schema:
                type: integer
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
          description: Retrieve all annotations associated with specified resource
          tags:
            - annotations
            - sources
            - spectra
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources, spectra]
              description: |
                 What underlying data the annotation is on:
                 must be one of either "sources" or "spectra".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
              description: |
                The ID of the underlying data.
                This would be a string for a source ID
                or an integer for other data types like spectra.
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
        associated_resource = self.get_associated_resource(associated_resource_type)

        if annotation_id is None:
            annotations = (
                associated_resource['class']
                .query_records_accessible_by(self.current_user)
                .filter(
                    getattr(
                        associated_resource['class'], associated_resource['id_attr']
                    )
                    == resource_id
                )
                .all()
            )
            self.verify_and_commit()
            return self.success(data=annotations)

        try:
            annotation_id = int(annotation_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) annotation ID.")

        try:
            annotation = associated_resource['class'].get_if_accessible_by(
                annotation_id, self.current_user, raise_if_none=True
            )
        except AccessError:
            return self.error('Could not find any accessible annotations.', status=403)

        if str(getattr(annotation, associated_resource['id_attr'])) != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        return self.success(data=annotation)

    @permissions(['Annotate'])
    def post(self, associated_resource_type, resource_id):
        """
        ---
        description: Post an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               must be one of either "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for an object ID,
               or an integer for other data types,
               e.g., a spectrum.
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  origin:
                     type: string
                     description: |
                        String describing the source of this information.
                        Only one Annotation per origin is allowed, although
                        each Annotation can have multiple fields.
                        To add/change data, use the update method instead
                        of trying to post another Annotation from this origin.
                        Origin must be a non-empty string starting with an
                        alphanumeric character or underscore.
                        (it must match the regex: /^\\w+/)

                  data:
                    type: object
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view annotation. Defaults to all of requesting user's
                      groups.

                required:
                  - origin
                  - data
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
                            annotation_id:
                              type: integer
                              description: New annotation ID
        """
        data = self.get_json()
        origin = data.get("origin")

        if origin is None:
            return self.error("origin must be specified")

        if not re.search(r'^\w+', origin):
            return self.error("Input `origin` must begin with alphanumeric/underscore")

        annotation_data = data.get("data")

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)

        if not isinstance(annotation_data, Mapping):
            return self.error(
                "Invalid data: the annotation data must be an object with at least one {key: value} pair"
            )

        author = self.associated_user_object

        if associated_resource_type.lower() == "sources":
            obj_id = resource_id
            data['obj_id'] = obj_id
            schema = Annotation.__schema__(exclude=["author_id"])
            try:
                schema.load(data)
            except ValidationError as e:
                return self.error(
                    f'Invalid/missing parameters: {e.normalized_messages()}'
                )

            annotation = Annotation(
                data=annotation_data,
                obj_id=obj_id,
                origin=origin,
                author=author,
                groups=groups,
            )
        elif associated_resource_type.lower() == "spectra":
            spectrum_id = resource_id
            try:
                spectrum = Spectrum.get_if_accessible_by(
                    spectrum_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    f'Could not access spectrum {spectrum_id}.', status=403
                )
            data['spectrum_id'] = spectrum_id
            data['obj_id'] = spectrum.obj_id
            schema = AnnotationOnSpectrum.__schema__(exclude=["author_id"])
            try:
                schema.load(data)
            except ValidationError as e:
                return self.error(
                    f'Invalid/missing parameters: {e.normalized_messages()}'
                )

            annotation = AnnotationOnSpectrum(
                data=annotation_data,
                spectrum_id=spectrum_id,
                obj_id=spectrum.obj_id,
                origin=origin,
                author=author,
                groups=groups,
            )
        else:
            return self.error(f'Unknown resource type "{associated_resource_type}".')

        DBSession().add(annotation)
        try:
            self.verify_and_commit()
        except IntegrityError as e:
            return self.error(f'Annotation already exists: {str(e)}')

        if isinstance(
            annotation, (Annotation, AnnotationOnSpectrum)
        ):  # annotation on object or object related data
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': annotation.obj.internal_key},
            )
        if isinstance(annotation, AnnotationOnSpectrum):
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': annotation.obj.internal_key},
            )
        return self.success(data={'annotation_id': annotation.id})

    @permissions(['Annotate'])
    def put(self, associated_resource_type, resource_id, annotation_id):
        """
        ---
        description: Update an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               must be one of either "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for a source ID
               or an integer for other data types like spectrum.
          - in: path
            name: annotation_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/AnnotationNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of group IDs corresponding to which groups should be
                          able to view the annotation.
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

        try:
            annotation_id = int(annotation_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) annotation ID. ")

        associated_resource = self.get_associated_resource(associated_resource_type)

        schema = associated_resource['class'].__schema__()
        try:
            a = associated_resource['class'].get_if_accessible_by(
                annotation_id, self.current_user, mode="update", raise_if_none=True
            )
        except AccessError:
            return self.error('Could not find any accessible annotations.', status=403)

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = annotation_id

        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        if group_ids is not None:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)
            a.groups = groups

        if str(getattr(a, associated_resource['id_attr'])) != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if associated_resource[
            'obj_associated'
        ]:  # annotation on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': a.obj.internal_key},
            )
        if isinstance(a, AnnotationOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': a.obj.internal_key},
            )

        return self.success()

    @permissions(['Annotate'])
    def delete(self, associated_resource_type, resource_id, annotation_id):
        """
        ---
        description: Delete an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               must be one of either "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for a source ID
               or an integer for a spectrum.
          - in: path
            name: annotation_id
            required: true
            schema:
              type: integer
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

        try:
            a = associated_resource['class'].get_if_accessible_by(
                annotation_id, self.current_user, mode="delete", raise_if_none=True
            )
        except AccessError:
            return self.error('Could not find any accessible annotations.', status=403)

        if str(getattr(a, associated_resource['id_attr'])) != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        obj_key = a.obj.internal_key

        DBSession().delete(a)
        self.verify_and_commit()

        if associated_resource[
            'obj_associated'
        ]:  # annotation on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key}
            )

        if isinstance(a, AnnotationOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': obj_key},
            )

        return self.success()

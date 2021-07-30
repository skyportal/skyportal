import re
from typing import Mapping
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Annotation, AnnotationOnSpectrum, Group


class AnnotationHandler(BaseHandler):
    @auth_or_token
    def get(self, annotation_id, associated_resource_type=None):
        """
        ---
        description: Retrieve an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: annotation_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               an "object" (default), or a "spectrum".
        responses:
          200:
            content:
              application/json:
                schema: SingleAnnotation
          400:
            content:
              application/json:
                schema: Error
        """
        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object (default)
            annotation = Annotation.get_if_accessible_by(
                annotation_id, self.current_user, raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            annotation = AnnotationOnSpectrum.get_if_accessible_by(
                annotation_id, self.current_user, raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        return self.success(data=annotation)

    @permissions(['Annotate'])
    def post(self):
        """
        ---
        description: Post an annotation
        tags:
          - annotations
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: string
                  spectrum_id:
                    type: integer
                    description: |
                      ID of spectrum that this annotation should be
                      attached to. Leave empty to post an annotation
                      on the object instead.
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
                  - obj_id
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

        spectrum_id = data.get("spectrum_id", None)

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )

        schema = Annotation.__schema__(exclude=["author_id"])
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        obj_id = data.get("obj_id", None)
        origin = data.get("origin")

        if not re.search(r'^\w+', origin):
            return self.error("Input `origin` must begin with alphanumeric/underscore")

        annotation_data = data.get("data")

        if not isinstance(annotation_data, Mapping):
            return self.error(
                "Invalid data: the annotation data must be an object with at least one {key: value} pair"
            )

        author = self.associated_user_object
        if spectrum_id is not None:
            annotation = AnnotationOnSpectrum(
                specrum_id=spectrum_id,
                data=annotation_data,
                obj_id=obj_id,
                origin=origin,
                author=author,
                groups=groups,
            )
        else:
            if obj_id is None:
                return self.error("Missing required field `obj_id`")
            annotation = Annotation(
                data=annotation_data,
                obj_id=obj_id,
                origin=origin,
                author=author,
                groups=groups,
            )

        DBSession().add(annotation)
        self.verify_and_commit()

        if spectrum_id is not None:
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_id': obj_id},
            )
        else:
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': annotation.obj.internal_key},
            )

        return self.success(data={'annotation_id': annotation.id})

    @permissions(['Annotate'])
    def put(self, annotation_id, associated_resource_type=None):
        """
        ---
        description: Update an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: annotation_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               an "object" (default), or a "spectrum".
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
        if associated_resource_type is None:
            associated_resource_type = 'object'

        a = Annotation.get_if_accessible_by(
            annotation_id, self.current_user, mode="update", raise_if_none=True
        )

        if associated_resource_type.lower() == "object":  # comment on object
            schema = Annotation.__schema__()
            a = Annotation.get_if_accessible_by(
                annotation_id, self.current_user, mode="update", raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            schema = AnnotationOnSpectrum.__schema__()
            a = AnnotationOnSpectrum.get_if_accessible_by(
                annotation_id, self.current_user, mode="update", raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = annotation_id

        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        if group_ids is not None:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )
            a.groups = groups

        self.verify_and_commit()

        if associated_resource_type.lower() == "object":  # comment on object
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': a.obj.internal_key},
            )
        elif associated_resource_type.lower() == "spectrum":  # comment on a spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_id': a.obj.id},
            )

        return self.success()

    @permissions(['Annotate'])
    def delete(self, annotation_id, associated_resource_type=None):
        """
        ---
        description: Delete an annotation
        tags:
          - annotations
        parameters:
          - in: path
            name: annotation_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the annotation is on:
               an "object" (default), or a "spectrum".
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object
            a = Annotation.get_if_accessible_by(
                annotation_id, self.current_user, mode="delete", raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            a = AnnotationOnSpectrum.get_if_accessible_by(
                annotation_id, self.current_user, mode="delete", raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        obj_key = a.obj.internal_key
        obj_id = a.obj.id

        DBSession().delete(a)
        self.verify_and_commit()

        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key})

        if associated_resource_type.lower() == "object":
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_key},
            )
        elif associated_resource_type.lower() == "spectrum":
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_id': obj_id},
            )

        return self.success()


class ObjAnnotationHandler(BaseHandler):
    @auth_or_token
    def get(self, obj_id):
        """
        ---
        description: Retrieve object's annotations
        tags:
          - annotations
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
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

        annotations = (
            Annotation.query_records_accessible_by(self.current_user)
            .filter(Annotation.obj_id == obj_id)
            .all()
        )
        self.verify_and_commit()
        return self.success(data=annotations)

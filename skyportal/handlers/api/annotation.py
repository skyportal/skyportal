import re
from typing import Mapping
from marshmallow.exceptions import ValidationError
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Annotation, Group


class AnnotationHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, annotation_id):
        """
        ---
        description: Retrieve an annotation
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
               currently only "sources" is supported.
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for a source ID
               or an integer for other data types like spectrum.
               The annotation ID must correspond to an annotation on the
               underlying object given by this field.
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
        """

        try:
            annotation_id = int(annotation_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) annotation ID. ")

        if associated_resource_type.lower() == "sources":
            try:
                annotation = Annotation.get_if_accessible_by(
                    annotation_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible annotations.')
            annotation_resource_id_str = str(annotation.obj_id)
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        if annotation_resource_id_str != resource_id:
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
               currently only "sources" is supported.
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for an object ID
               or an integer for other data types like spectrum.
               The object pointed to by this input must be a valid
               object or other data type (like spectrum) that
               can be annotated on by the user/token.
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
        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.')
        schema = Annotation.__schema__(exclude=["author_id"])
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        origin = data.get("origin")

        if not re.search(r'^\w+', origin):
            return self.error("Input `origin` must begin with alphanumeric/underscore")

        annotation_data = data.get("data")

        if not isinstance(annotation_data, Mapping):
            return self.error(
                "Invalid data: the annotation data must be an object with at least one {key: value} pair"
            )

        author = self.associated_user_object
        if associated_resource_type.lower() == "sources":
            obj_id = resource_id
            annotation = Annotation(
                data=annotation_data,
                obj_id=obj_id,
                origin=origin,
                author=author,
                groups=groups,
            )
            annotation_resource_id_str = str(annotation.obj_id)
        else:
            return self.error(f'Unknown resource type "{associated_resource_type}".')

        if annotation_resource_id_str != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        DBSession().add(annotation)
        self.verify_and_commit()

        if obj_id is not None:
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': annotation.obj.internal_key},
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
               currently only "sources" is supported.
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for a source ID
               or an integer for other data types like spectrum.
               The annotation ID must correspond to an annotation on the
               underlying object given by this field.
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

        if associated_resource_type.lower() == "sources":
            schema = Annotation.__schema__()
            try:
                a = Annotation.get_if_accessible_by(
                    annotation_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible annotations.')
            annotation_resource_id_str = str(a.obj_id)

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
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.')
            a.groups = groups

        if annotation_resource_id_str != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if a.obj.id:  # comment on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': a.obj.internal_key},
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
               currently only "sources" is supported.
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
            description: |
               The ID of the underlying data.
               This would be a string for a source ID
               or an integer for other data types like spectrum.
               The annotation ID must correspond to an annotation on the
               underlying object given by this field.
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

        if associated_resource_type.lower() == "sources":
            try:
                a = Annotation.get_if_accessible_by(
                    annotation_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible annotations.')
            annotation_resource_id_str = str(a.obj_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        obj_key = a.obj.internal_key
        # some other logic should come here if annotation is not
        # associated with an object

        if annotation_resource_id_str != resource_id:
            return self.error(
                f'Annotation resource ID does not match resource ID given in path ({resource_id})'
            )

        DBSession().delete(a)
        self.verify_and_commit()

        if a.obj.id:  # annotation on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key}
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

import re
from typing import Mapping
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Annotation, Group


class AnnotationHandler(BaseHandler):
    @auth_or_token
    def get(self, annotation_id):
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
        annotation = Annotation.get_if_accessible_by(
            annotation_id, self.current_user, raise_if_none=True
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
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )

        schema = Annotation.__schema__(exclude=["author_id"])
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        obj_id = data.get("obj_id")
        origin = data.get("origin")

        if not re.search(r'^\w+', origin):
            return self.error("Input `origin` must begin with alphanumeric/underscore")

        annotation_data = data.get("data")

        if not isinstance(annotation_data, Mapping):
            return self.error(
                "Invalid data: the annotation data must be an object with at least one {key: value} pair"
            )

        author = self.associated_user_object
        annotation = Annotation(
            data=annotation_data,
            obj_id=obj_id,
            origin=origin,
            author=author,
            groups=groups,
        )

        DBSession().add(annotation)
        self.verify_and_commit()
        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': annotation.obj.internal_key},
        )
        return self.success(data={'annotation_id': annotation.id})

    @permissions(['Annotate'])
    def put(self, annotation_id):
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
        a = Annotation.get_if_accessible_by(
            annotation_id, self.current_user, mode="update", raise_if_none=True
        )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = annotation_id

        schema = Annotation.__schema__()
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
        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': a.obj.internal_key}
        )
        return self.success()

    @permissions(['Annotate'])
    def delete(self, annotation_id):
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
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        a = Annotation.get_if_accessible_by(
            annotation_id, self.current_user, mode="delete", raise_if_none=True
        )
        obj_key = a.obj.internal_key
        DBSession().delete(a)
        self.verify_and_commit()
        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key})
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

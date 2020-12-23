import re
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token, AccessError
from ..base import BaseHandler
from ...models import DBSession, Annotation, Group


class AnnotationHandler(BaseHandler):
    @auth_or_token
    def get(self, annotation_id):
        """
        ---
        description: Retrieve an annotation
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
        annotation = Annotation.get_if_accessible_by(annotation_id, self.current_user)
        if annotation is None:
            return self.error('Invalid annotation ID.')
        return self.success(data=annotation)

    @permissions(['Annotate'])
    def post(self):
        """
        ---
        description: Post an annotation
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

        author = self.associated_user_object
        annotation = Annotation(
            data=annotation_data, obj_id=obj_id, origin=origin, author=author,
        )

        groups = [self.associated_user_object.single_user_group]
        if group_ids is not None:
            try:
                _groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError as e:
                return self.error(f'{e}')
            groups.extend(_groups)

        annotation.groups = groups
        DBSession().add(annotation)
        obj = annotation.obj

        try:
            self.finalize_transaction()
        except AccessError as e:
            return self.error(f'{e}')

        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj.internal_key},
        )
        return self.success(data={'annotation_id': annotation.id})

    @permissions(['Annotate'])
    def put(self, annotation_id):
        """
        ---
        description: Update an annotation
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
        a = Annotation.query.get(annotation_id)
        if a is None:
            return self.error('Invalid annotation ID.')

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = annotation_id

        schema = Annotation.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        if group_ids is not None:
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError as e:
                return self.error(f'{e}')

            # merge update groups (dont delete groups)
            a.groups = list(set(a.groups) | set(groups))

        try:
            self.finalize_transaction()
        except AccessError as e:
            return self.error(f'{e}')
        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': a.obj.internal_key}
        )
        return self.success()

    @permissions(['Annotate'])
    def delete(self, annotation_id):
        """
        ---
        description: Delete an annotation
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
        a = Annotation.query.get(annotation_id)
        if a is None:
            return self.error("Invalid annotation ID")
        obj_key = a.obj.internal_key
        DBSession().delete(a)

        try:
            self.finalize_transaction()
        except AccessError as e:
            return self.error(f'{e}')

        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key})
        return self.success()

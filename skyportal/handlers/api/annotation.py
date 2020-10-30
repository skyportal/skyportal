import re
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Annotation, Group, Candidate, Filter


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
        annotation = Annotation.get_if_owned_by(annotation_id, self.current_user)
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

        # Ensure user/token has access to parent source
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]

        if not group_ids:
            group_ids = user_accessible_group_ids
        group_ids = [int(id) for id in group_ids]
        group_ids = set(group_ids).intersection(user_accessible_group_ids)
        if not group_ids:
            return self.error(
                f"Invalid group IDs field ({group_ids}): "
                "You must provide one or more valid group IDs."
            )

        # Only post to groups source/candidate is actually associated with
        candidate_group_ids = [
            f.group_id
            for f in (
                DBSession()
                .query(Filter)
                .join(Candidate)
                .filter(Filter.id.in_(user_accessible_filter_ids))
                .filter(Candidate.obj_id == obj_id)
                .all()
            )
        ]
        source_group_ids = [
            source.group_id
            for source in DBSession()
            .query(Source)
            .filter(Source.obj_id == obj_id)
            .all()
        ]
        group_ids = set(group_ids).intersection(candidate_group_ids + source_group_ids)
        if not group_ids:
            return self.error("Obj is not associated with any of the specified groups.")

        groups = Group.query.filter(Group.id.in_(group_ids)).all()

        author = self.associated_user_object
        annotation = Annotation(
            data=annotation_data,
            obj_id=obj_id,
            origin=origin,
            author=author,
            groups=groups,
        )

        DBSession().add(annotation)
        DBSession().commit()

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
        a = Annotation.get_if_owned_by(annotation_id, self.current_user)
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
        DBSession().flush()
        if group_ids is not None:
            a = Annotation.get_if_owned_by(annotation_id, self.current_user)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot associate an annotation with groups you are not a member of."
                )
            a.groups = groups
        DBSession().commit()
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
        user = self.associated_user_object
        a = Annotation.query.get(annotation_id)
        if a is None:
            return self.error("Invalid annotation ID")
        obj_key = a.obj.internal_key
        if (
            "System admin" in user.permissions or "Manage groups" in user.permissions
        ) or (a.author == user):
            Annotation.query.filter_by(id=annotation_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key})
        return self.success()

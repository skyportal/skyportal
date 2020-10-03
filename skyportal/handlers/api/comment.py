import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment, Group, Candidate, Filter
from .candidate import update_redshift_history_if_relevant


class CommentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id):
        """
        ---
        description: Retrieve a comment
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: SingleComment
          400:
            content:
              application/json:
                schema: Error
        """
        comment = Comment.get_if_owned_by(comment_id, self.current_user)
        if comment is None:
            return self.error('Invalid comment ID.')
        return self.success(data=comment)

    @permissions(['Comment'])
    def post(self):
        """
        ---
        description: Post a comment
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  obj_id:
                    type: string
                  text:
                    type: string
                  group_ids:
                    type: array
                    items:
                      type: integer
                    description: |
                      List of group IDs corresponding to which groups should be
                      able to view comment. Defaults to all of requesting user's
                      groups.
                  attachment:
                    type: object
                    properties:
                      body:
                        type: string
                        format: byte
                        description: base64-encoded file contents
                      name:
                        type: string
                required:
                  - obj_id
                  - text
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
                            comment_id:
                              type: integer
                              description: New comment ID
        """
        data = self.get_json()
        obj_id = data.get("obj_id")
        if obj_id is None:
            return self.error("Missing required field `obj_id`")
        comment_text = data.get("text")
        # Ensure user/token has access to parent source
        obj = Source.get_obj_if_owned_by(obj_id, self.current_user)
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        user_accessible_filter_ids = [
            filtr.id
            for g in self.current_user.accessible_groups
            for filtr in g.filters
            if g.filters is not None
        ]
        group_ids = [int(id) for id in data.pop("group_ids", user_accessible_group_ids)]
        group_ids = set(group_ids).intersection(user_accessible_group_ids)
        if not group_ids:
            return self.error(
                f"Invalid group IDs field ({group_ids}): "
                "You must provide one or more valid group IDs."
            )

        # Only post to groups source/candidate is actually associated with
        if DBSession().query(Candidate).filter(Candidate.obj_id == obj_id).all():
            candidate_group_ids = [
                f.group_id
                for f in (
                    DBSession()
                    .query(Filter)
                    .filter(Filter.id.in_(user_accessible_filter_ids))
                    .filter(
                        Filter.id.in_(
                            DBSession()
                            .query(Candidate.filter_id)
                            .filter(Candidate.obj_id == obj_id)
                        )
                    )
                    .all()
                )
            ]
        else:
            candidate_group_ids = []
        matching_sources = (
            DBSession().query(Source).filter(Source.obj_id == obj_id).all()
        )
        if matching_sources:
            source_group_ids = [source.group_id for source in matching_sources]
        else:
            source_group_ids = []
        group_ids = set(group_ids).intersection(candidate_group_ids + source_group_ids)
        if not group_ids:
            return self.error("Obj is not associated with any of the specified groups.")

        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if 'attachment' in data and 'body' in data['attachment']:
            attachment_bytes = str.encode(
                data['attachment']['body'].split('base64,')[-1]
            )
            attachment_name = data['attachment']['name']
        else:
            attachment_bytes, attachment_name = None, None

        author = self.associated_user_object
        comment = Comment(
            text=comment_text,
            obj_id=obj_id,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
            author=author,
            groups=groups,
        )

        DBSession().add(comment)
        if comment_text.startswith("z="):
            try:
                redshift = float(comment_text.strip().split("z=")[1])
            except ValueError:
                return self.error(
                    "Invalid redshift value provided; unable to cast to float"
                )
            obj.redshift = redshift
            update_redshift_history_if_relevant(
                {"redshift": redshift}, obj, self.associated_user_object
            )
        DBSession().commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE',
            payload={'obj_key': comment.obj.internal_key},
        )
        return self.success(data={'comment_id': comment.id})

    @permissions(['Comment'])
    def put(self, comment_id):
        """
        ---
        description: Update a comment
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/CommentNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of group IDs corresponding to which groups should be
                          able to view comment.
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
        c = Comment.get_if_owned_by(comment_id, self.current_user)
        if c is None:
            return self.error('Invalid comment ID.')

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = comment_id

        schema = Comment.__schema__()
        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')
        DBSession().flush()
        if group_ids is not None:
            c = Comment.get_if_owned_by(comment_id, self.current_user)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot associate comment with groups you are not a member of."
                )
            c.groups = groups
        DBSession().commit()
        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_key': c.obj.internal_key}
        )
        return self.success()

    @permissions(['Comment'])
    def delete(self, comment_id):
        """
        ---
        description: Delete a comment
        parameters:
          - in: path
            name: comment_id
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
        c = Comment.query.get(comment_id)
        if c is None:
            return self.error("Invalid comment ID")
        obj_key = c.obj.internal_key
        if (
            "System admin" in user.permissions or "Manage groups" in user.permissions
        ) or (c.author == user):
            Comment.query.filter_by(id=comment_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_key': obj_key})
        return self.success()


class CommentAttachmentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id):
        """
        ---
        description: Download comment attachment
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application:
                schema:
                  type: string
                  format: base64
                  description: base64-encoded contents of attachment
        """
        comment = Comment.get_if_owned_by(comment_id, self.current_user)
        if comment is None:
            return self.error('Invalid comment ID.')
        self.set_header(
            "Content-Disposition", "attachment; " f"filename={comment.attachment_name}"
        )
        self.set_header("Content-type", "application/octet-stream")
        self.write(base64.b64decode(comment.attachment_bytes))

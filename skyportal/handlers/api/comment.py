import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment, Group


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
        obj_id = data['obj_id']
        # Ensure user/token has access to parent source
        _ = Source.get_obj_if_owned_by(obj_id, self.current_user)
        user_group_ids = [g.id for g in self.current_user.groups]
        user_accessible_group_ids = [g.id for g in self.current_user.accessible_groups]
        group_ids = data.pop("group_ids", user_group_ids)
        group_ids = [gid for gid in group_ids if gid in user_accessible_group_ids]
        if not group_ids:
            return self.error(
                f"Invalid group IDs field ({group_ids}): "
                "You must provide one or more valid group IDs."
            )
        groups = Group.query.filter(Group.id.in_(group_ids)).all()
        if 'attachment' in data and 'body' in data['attachment']:
            attachment_bytes = str.encode(
                data['attachment']['body'].split('base64,')[-1]
            )
            attachment_name = data['attachment']['name']
        else:
            attachment_bytes, attachment_name = None, None

        author = self.associated_user_object.username
        comment = Comment(
            text=data['text'],
            obj_id=obj_id,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
            author=author,
            groups=groups,
        )

        DBSession().add(comment)
        DBSession().commit()

        self.push_all(
            action='skyportal/REFRESH_SOURCE', payload={'obj_id': comment.obj_id}
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
            return self.error(
                'Invalid/missing parameters: ' f'{e.normalized_messages()}'
            )
        DBSession().flush()
        if group_ids is not None:
            c = Comment.get_if_owned_by(comment_id, self.current_user)
            groups = Group.query.filter(Group.id.in_(group_ids)).all()
            if not groups:
                return self.error(
                    "Invalid group_ids field. " "Specify at least one valid group ID."
                )
            if not all(
                [group in self.current_user.accessible_groups for group in groups]
            ):
                return self.error(
                    "Cannot associate comment with groups you are " "not a member of."
                )
            c.groups = groups
        DBSession().commit()
        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_id': c.obj_id})
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
        user = self.associated_user_object.username
        acls = [acl.id for acl in self.current_user.acls]
        c = Comment.query.get(comment_id)
        if c is None:
            return self.error("Invalid comment ID")
        obj_id = c.obj_id
        author = c.author
        if ("System admin" in acls or "Manage groups" in acls) or (user == author):
            Comment.query.filter_by(id=comment_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(action='skyportal/REFRESH_SOURCE', payload={'obj_id': obj_id})
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

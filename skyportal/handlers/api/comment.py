import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import DBSession, Source, Comment


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
        comment = Comment.query.get(comment_id)
        if comment is None:
            return self.error('Invalid comment ID.')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(comment.obj_id, self.current_user)
        if comment is not None:
            return self.success(data=comment)
        return self.error('Invalid comment ID.')

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
        _ = Source.get_if_owned_by(obj_id, self.current_user)
        if 'attachment' in data and 'body' in data['attachment']:
            attachment_bytes = str.encode(data['attachment']['body']
                                          .split('base64,')[-1])
            attachment_name = data['attachment']['name']
        else:
            attachment_bytes, attachment_name = None, None

        author = (self.current_user.username if hasattr(self.current_user, 'username')
                  else self.current_user.name)
        comment = Comment(text=data['text'],
                          obj_id=obj_id, attachment_bytes=attachment_bytes,
                          attachment_name=attachment_name,
                          author=author)

        DBSession().add(comment)
        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': comment.obj_id})
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
              schema: CommentNoID
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
        c = Comment.query.get(comment_id)
        if c is None:
            return self.error('Invalid comment ID.')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(c.obj_id, self.current_user)

        data = self.get_json()
        data['id'] = comment_id

        schema = Comment.__schema__()
        try:
            schema.load(data)
        except ValidationError as e:
            return self.error('Invalid/missing parameters: '
                              f'{e.normalized_messages()}')

        DBSession().commit()

        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': c.obj_id})
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
        user = (self.current_user.username if hasattr(self.current_user, 'username') else self.current_user.name)
        roles = (self.current_user.roles if hasattr(self.current_user, 'roles') else '')
        c = Comment.query.get(comment_id)
        if c is None:
            return self.error("Invalid comment ID")
        obj_id = c.obj_id
        author = c.author
        if ("Super admin" in [role.id for role in roles]) or (user == author):
            Comment.query.filter_by(id=comment_id).delete()
            DBSession().commit()
        else:
            return self.error('Insufficient user permissions.')
        self.push_all(action='skyportal/REFRESH_SOURCE',
                      payload={'obj_id': obj_id})
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
        comment = Comment.query.get(comment_id)
        if comment is None:
            return self.error('Invalid comment ID.')
        # Ensure user/token has access to parent source
        _ = Source.get_if_owned_by(comment.obj_id, self.current_user)
        self.set_header(
            "Content-Disposition", "attachment; "
            f"filename={comment.attachment_name}")
        self.set_header("Content-type", "application/octet-stream")
        self.write(base64.b64decode(comment.attachment_bytes))

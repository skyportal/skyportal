import string
import base64
from distutils.util import strtobool
from marshmallow.exceptions import ValidationError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Comment,
    CommentOnSpectrum,
    Group,
    User,
    UserNotification,
)


def users_mentioned(text):
    punctuation = string.punctuation.replace("-", "").replace("@", "")
    usernames = []
    for word in text.replace(",", " ").split():
        word = word.strip(punctuation)
        if word.startswith("@"):
            usernames.append(word.replace("@", ""))
    users = User.query.filter(User.username.in_(usernames)).all()
    return users


class CommentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id, associated_resource_type=None):
        """
        ---
        description: Retrieve a comment
        tags:
          - comments
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the comment is on:
               an "object" (default), or a "spectrum".
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

        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object (default)
            comment = Comment.get_if_accessible_by(
                comment_id, self.current_user, raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            comment = CommentOnSpectrum.get_if_accessible_by(
                comment_id, self.current_user, raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        return self.success(data=comment)

    @permissions(['Comment'])
    def post(self):
        """
        ---
        description: Post a comment
        tags:
          - comments
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
                      ID of spectrum that this comment should be
                      attached to. Leave empty to post a comment
                      on the object instead.
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
        obj_id = data.get("obj_id", None)

        comment_text = data.get("text")

        spectrum_id = data.get("spectrum_id", None)

        group_ids = data.pop('group_ids', None)
        if not group_ids:
            groups = self.current_user.accessible_groups
        else:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )

        if 'attachment' in data:
            if (
                isinstance(data['attachment'], dict)
                and 'body' in data['attachment']
                and 'name' in data['attachment']
            ):
                attachment_bytes = str.encode(
                    data['attachment']['body'].split('base64,')[-1]
                )
                attachment_name = data['attachment']['name']
            else:
                return self.error("Malformed comment attachment")
        else:
            attachment_bytes, attachment_name = None, None

        author = self.associated_user_object
        if spectrum_id is not None:
            comment = CommentOnSpectrum(
                text=comment_text,
                spectrum_id=spectrum_id,
                obj_id=obj_id,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
                author=author,
                groups=groups,
            )
        else:  # the default is to post a comment directly on the object
            if obj_id is None:
                return self.error("Missing required field `obj_id`")
            comment = Comment(
                text=comment_text,
                obj_id=obj_id,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
                author=author,
                groups=groups,
            )
        users_mentioned_in_comment = users_mentioned(comment_text)
        if users_mentioned_in_comment:
            for user_mentioned in users_mentioned_in_comment:
                DBSession().add(
                    UserNotification(
                        user=user_mentioned,
                        text=f"*@{self.current_user.username}* mentioned you in a comment on *{obj_id}*",
                        url=f"/source/{obj_id}",
                    )
                )

        DBSession().add(comment)
        self.verify_and_commit()
        if users_mentioned_in_comment:
            for user_mentioned in users_mentioned_in_comment:
                self.flow.push(user_mentioned.id, "skyportal/FETCH_NOTIFICATIONS", {})

        if spectrum_id is not None:
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_id': obj_id},
            )
        else:
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': comment.obj.internal_key},
            )

        return self.success(data={'comment_id': comment.id})

    @permissions(['Comment'])
    def put(self, comment_id, associated_resource_type=None):
        """
        ---
        description: Update a comment
        tags:
          - comments
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the comment is on:
               an "object" (default), or a "spectrum".
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

        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object
            schema = Comment.__schema__()
            c = Comment.get_if_accessible_by(
                comment_id, self.current_user, mode="update", raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            schema = CommentOnSpectrum.__schema__()
            c = CommentOnSpectrum.get_if_accessible_by(
                comment_id, self.current_user, mode="update", raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = comment_id
        attachment_bytes = data.pop('attachment_bytes', None)

        try:
            schema.load(data, partial=True)
        except ValidationError as e:
            return self.error(f'Invalid/missing parameters: {e.normalized_messages()}')

        if attachment_bytes is not None:
            attachment_bytes = str.encode(attachment_bytes.split('base64,')[-1])
            c.attachment_bytes = attachment_bytes

        bytes_is_none = c.attachment_bytes is None
        name_is_none = c.attachment_name is None

        if bytes_is_none ^ name_is_none:
            return self.error(
                'This update leaves one of attachment name or '
                'attachment bytes null. Both fields must be '
                'filled, or both must be null.'
            )

        if group_ids is not None:
            groups = Group.get_if_accessible_by(
                group_ids, self.current_user, raise_if_none=True
            )
            c.groups = groups

        self.verify_and_commit()

        if associated_resource_type.lower() == "object":  # comment on object
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': c.obj.internal_key},
            )
        elif associated_resource_type.lower() == "spectrum":  # comment on a spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_id': c.obj.id},
            )

        return self.success()

    @permissions(['Comment'])
    def delete(self, comment_id, associated_resource_type=None):
        """
        ---
        description: Delete a comment
        tags:
          - comments
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the comment is on:
               an "object" (default), or a "spectrum".
        responses:
          200:
            content:
              application/json:
                schema: Success
        """

        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object
            c = Comment.get_if_accessible_by(
                comment_id, self.current_user, mode="delete", raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            c = CommentOnSpectrum.get_if_accessible_by(
                comment_id, self.current_user, mode="delete", raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        obj_key = c.obj.internal_key
        obj_id = c.obj.id
        DBSession().delete(c)
        self.verify_and_commit()

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


class CommentAttachmentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id, associated_resource_type=None):
        """
        ---
        description: Download comment attachment
        tags:
          - comments
        parameters:
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
          - in: path
            name: associated_resource_type
            required: false
            schema:
              type: string
            description: |
               What underlying data the comment is on:
               an "object" (default), or a "spectrum".
          - in: query
            name: download
            nullable: True
            schema:
              type: boolean
              description: If true, download the attachment; else return file data as text. True by default.
        responses:
          200:
            content:
              application:
                schema:
                  type: string
                  format: base64
                  description: base64-encoded contents of attachment
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
                              description: Comment ID attachment came from
                            attachment:
                              type: string
                              description: The attachment file contents decoded as a string

        """
        download = strtobool(self.get_query_argument('download', "True").lower())

        if associated_resource_type is None:
            associated_resource_type = 'object'

        if associated_resource_type.lower() == "object":  # comment on object
            comment = Comment.get_if_accessible_by(
                comment_id, self.current_user, raise_if_none=True
            )
        elif associated_resource_type.lower() == "spectrum":
            comment = CommentOnSpectrum.get_if_accessible_by(
                comment_id, self.current_user, raise_if_none=True
            )
        # add more options using elif
        else:
            return self.error(
                f'Unsupported input "{associated_resource_type}" given as "associated_resource_type" argument.'
            )

        self.verify_and_commit()

        if download:
            self.set_header(
                "Content-Disposition",
                "attachment; " f"filename={comment.attachment_name}",
            )
            self.set_header("Content-type", "application/octet-stream")
            self.write(base64.b64decode(comment.attachment_bytes))
        else:
            return self.success(
                data={
                    "commentId": int(comment_id),
                    "attachment": base64.b64decode(comment.attachment_bytes).decode(),
                }
            )

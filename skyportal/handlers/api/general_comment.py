import string
import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Comment,
    CommentOnSpectrum,
    CommentOnGCN,
    GeneralComment,
    Group,
    User,
    UserNotification,
    Token,
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


class GeneralCommentHandler(BaseHandler):
    @auth_or_token
    def get(self, comment_id=None):
        """
        ---
        single:
          description: Retrieve a comment
          tags:
            - comments
            - sources
            - spectra
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
              description: |
                 What underlying data the comment is on:
                 "sources" or "spectra" or "gcn_event".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
                enum: [sources, spectra, gcn_event]
              description: |
                 The ID of the source, spectrum, or gcn_event
                 that the comment is posted to.
                 This would be a string for a source ID
                 or an integer for a spectrum or gcn_event
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
        multiple:
          description: Retrieve all comments associated with specified resource
          tags:
            - comments
            - spectra
            - sources
            - gcn_event
            - general_comments
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources]
              description: |
                 What underlying data the comment is on, e.g., "sources"
                 or "spectra" or "gcn_event".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
              description: |
                 The ID of the underlying data.
                 This would be a string for a source ID
                 or an integer for other data types like spectrum or gcn_event.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfComments
            400:
              content:
                application/json:
                  schema: Error
        """
        if comment_id is None:
            comments = GeneralComment.query_records_accessible_by(
                self.current_user
            ).all()

            self.verify_and_commit()
            return self.success(data=comments)

        try:
            comment_id = int(comment_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) comment ID. ")

        try:
            comment = GeneralComment.get_if_accessible_by(
                comment_id, self.current_user, raise_if_none=True
            )
        except AccessError:
            return self.error('Could not find any accessible comments.', status=403)

        if not comment.attachment_bytes:
            return self.success(data=comment)
        else:
            return self.success(
                data={
                    "commentId": int(comment_id),
                    "text": comment.text,
                    "attachment": base64.b64decode(comment.attachment_bytes).decode(),
                    "attachment_name": str(comment.attachment_name),
                }
            )

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

        comment_text = data.get("text")

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
        is_bot_request = isinstance(self.current_user, Token)

        comment = GeneralComment(
            text=comment_text,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
            author=author,
            groups=groups,
            bot=is_bot_request,
        )

        users_mentioned_in_comment = users_mentioned(comment_text)

        for user in users_mentioned_in_comment:
            DBSession().add(
                UserNotification(
                    user=user,
                    text=f"*@{self.current_user.username}* mentionned you on a general comment. *{comment.text}*",
                    notification_type="comment",
                    url=f"/comments/{comment.id}",
                )
            )

        DBSession().add(comment)
        self.verify_and_commit()
        if users_mentioned_in_comment:
            for user_mentioned in users_mentioned_in_comment:
                self.flow.push(user_mentioned.id, "skyportal/FETCH_NOTIFICATIONS", {})

        # add comment to all users
        self.push_all(action='skyportal/FETCH_NEWSFEED', payload={})

        return self.success(data={'comment_id': comment.id})

    @permissions(['Comment'])
    def put(self, associated_resource_type, resource_id, comment_id):
        """
        ---
        description: Update a comment
        tags:
          - comments
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum, gcn_event]
            description: |
               What underlying data the comment is on:
               "sources" or "spectra" or "gcn_event".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event]
            description: |
               The ID of the source or spectrum
               that the comment is posted to.
               This would be a string for an object ID
               or an integer for a spectrum or gcn_event.
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

        try:
            comment_id = int(comment_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) comment ID. ")

        if associated_resource_type.lower() == "sources":
            schema = Comment.__schema__()
            try:
                c = Comment.get_if_accessible_by(
                    comment_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible comments.', status=403)
            comment_resource_id_str = str(c.obj_id)

        elif associated_resource_type.lower() == "spectra":
            schema = CommentOnSpectrum.__schema__()
            try:
                c = CommentOnSpectrum.get_if_accessible_by(
                    comment_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible comments.', status=403)
            comment_resource_id_str = str(c.spectrum_id)

        elif associated_resource_type.lower() == "gcn_event":
            schema = CommentOnGCN.__schema__()
            try:
                c = CommentOnGCN.get_if_accessible_by(
                    comment_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible comments.', status=403)
            comment_resource_id_str = str(c.gcn_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
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
            try:
                groups = Group.get_if_accessible_by(
                    group_ids, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)
            c.groups = groups

        if comment_resource_id_str != resource_id:
            return self.error(
                f'Comment resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if hasattr(c, 'obj'):  # comment on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': c.obj.internal_key},
            )
        if isinstance(c, CommentOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': c.obj.internal_key},
            )
        elif isinstance(c, CommentOnGCN):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_GCN',
                payload={'obj_internal_key': c.obj.internal_key},
            )

        return self.success()

    @permissions(['Comment'])
    def delete(self, comment_id=None):
        """
        ---
        description: Delete a comment
        tags:
          - comments
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the comment is on:
               "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event]
            description: |
               The ID of the source or spectrum
               that the comment is posted to.
               This would be a string for a source ID
               or an integer for a spectrum or gcn_event.
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
        try:
            comment_id = int(comment_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) comment ID.")

        try:
            c = GeneralComment.get_if_accessible_by(
                comment_id, self.current_user, mode="delete", raise_if_none=True
            )
        except AccessError:
            return self.error('Could not find any accessible comments.', status=403)

        DBSession().delete(c)
        self.verify_and_commit()

        if isinstance(c, GeneralComment):  # also update the news feed
            self.push_all(
                action='skyportal/FETCH_NEWSFEED',
                payload={},
            )

        return self.success()

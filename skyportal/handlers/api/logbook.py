import string
import base64
from distutils.util import strtobool
from marshmallow.exceptions import ValidationError
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import permissions, auth_or_token
from ..base import BaseHandler
from ...models import (
    DBSession,
    Logbook,
    LogbookOnSpectrum,
    Spectrum,
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


class LogbookHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, logbook_id=None):
        """
        ---
        single:
          description: Retrieve a logbook
          tags:
            - logbooks
            - sources
            - spectra
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
              description: |
                 What underlying data the logbook is on:
                 "sources" or "spectra".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
                enum: [sources, spectra]
              description: |
                 The ID of the source or spectrum
                 that the logbook is posted to.
                 This would be a string for a source ID
                 or an integer for a spectrum.
            - in: path
              name: logbook_id
              required: true
              schema:
                type: integer

          responses:
            200:
              content:
                application/json:
                  schema: SingleLogbook
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all logbooks associated with specified resource
          tags:
            - logbooks
            - spectra
            - sources
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources]
              description: |
                 What underlying data the logbook is on, e.g., "sources"
                 or "spectra".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
              description: |
                 The ID of the underlying data.
                 This would be a string for a source ID
                 or an integer for other data types like spectrum.
          responses:
            200:
              content:
                application/json:
                  schema: ArrayOfLogbooks
            400:
              content:
                application/json:
                  schema: Error
        """
        if logbook_id is None:
            if associated_resource_type.lower() == "sources":
                logbooks = (
                    logbook.query_records_accessible_by(self.current_user)
                    .filter(Logbook.obj_id == resource_id)
                    .all()
                )
            elif associated_resource_type.lower() == "spectra":
                logbooks = (
                    LogbookOnSpectrum.query_records_accessible_by(self.current_user)
                    .filter(LogbookOnSpectrum.spectrum_id == resource_id)
                    .all()
                )
            else:
                return self.error(
                    f'Unsupported associated resource type "{associated_resource_type}".'
                )
            self.verify_and_commit()
            return self.success(data=logbooks)

        try:
            logbook_id = int(logbook_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) logbook ID. ")

        # the default is to logbook on an object
        if associated_resource_type.lower() == "sources":
            try:
                logbook = logbook.get_if_accessible_by(
                    logbook_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(logbook.obj_id)

        elif associated_resource_type.lower() == "spectra":
            try:
                logbook = LogbookOnSpectrum.get_if_accessible_by(
                    logbook_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(logbook.spectrum_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        if logbook_resource_id_str != resource_id:
            return self.error(
                f'Logbook resource ID does not match resource ID given in path ({resource_id})'
            )
        return self.success(data=logbook)

    @permissions(['Logbook'])
    def post(self, associated_resource_type, resource_id):
        """
        ---
        description: Post a Logbook
        tags:
          - logbooks
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum]
            description: |
               What underlying data the logbook is on:
               "source" or "spectrum".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra]
            description: |
               The ID of the source or spectrum
               that the logbook is posted to.
               This would be a string for a source ID
               or an integer for a spectrum.
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
                      able to view logbook. Defaults to all of requesting user's
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
                            logbook_id:
                              type: integer
                              description: New logbook ID
        """
        data = self.get_json()

        logbook_text = data.get("text")

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
                return self.error("Malformed logbook attachment")
        else:
            attachment_bytes, attachment_name = None, None

        author = self.associated_user_object
        is_bot_request = isinstance(self.current_user, Token)

        if associated_resource_type.lower() == "sources":
            obj_id = resource_id
            logbook = Logbook(
                text=logbook_text,
                obj_id=obj_id,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
                author=author,
                groups=groups,
                bot=is_bot_request,
            )
        elif associated_resource_type.lower() == "spectra":
            spectrum_id = resource_id
            try:
                spectrum = Spectrum.get_if_accessible_by(
                    spectrum_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    f'Could not access spectrum {spectrum_id}.', status=403
                )
            logbook = LogbookOnSpectrum(
                text=logbook_text,
                spectrum_id=spectrum_id,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
                author=author,
                groups=groups,
                bot=is_bot_request,
                obj_id=spectrum.obj_id,
            )
        else:
            return self.error(f'Unknown resource type "{associated_resource_type}".')

        users_mentioned_in_logbook = users_mentioned(logbook_text)
        if users_mentioned_in_logbook:
            for user_mentioned in users_mentioned_in_logbook:
                DBSession().add(
                    UserNotification(
                        user=user_mentioned,
                        text=f"*@{self.current_user.username}* mentioned you in a logbook on *{obj_id}*",
                        url=f"/source/{obj_id}",
                    )
                )

        DBSession().add(logbook)
        self.verify_and_commit()
        if users_mentioned_in_logbook:
            for user_mentioned in users_mentioned_in_logbook:
                self.flow.push(user_mentioned.id, "skyportal/FETCH_NOTIFICATIONS", {})

        if logbook.obj.id:  # logbook on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': logbook.obj.internal_key},
            )

        if isinstance(logbook, LogbookOnSpectrum):
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': logbook.obj.internal_key},
            )

        return self.success(data={'logbook_id': logbook.id})

    @permissions(['Logbook'])
    def put(self, associated_resource_type, resource_id, logbook_id):
        """
        ---
        description: Update a logbook
        tags:
          - logbooks
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum]
            description: |
               What underlying data the logbook is on:
               "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra]
            description: |
               The ID of the source or spectrum
               that the logbook is posted to.
               This would be a string for an object ID
               or an integer for a spectrum.
          - in: path
            name: logbook_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/LogbookNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of group IDs corresponding to which groups should be
                          able to view logbook.
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
            logbook_id = int(logbook_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) logbook ID. ")

        if associated_resource_type.lower() == "sources":
            schema = Logbook.__schema__()
            try:
                c = Logbook.get_if_accessible_by(
                    logbook_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(c.obj_id)

        elif associated_resource_type.lower() == "spectra":
            schema = LogbookOnSpectrum.__schema__()
            try:
                c = LogbookOnSpectrum.get_if_accessible_by(
                    logbook_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(c.spectrum_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = logbook_id
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

        if logbook_resource_id_str != resource_id:
            return self.error(
                f'Logbook resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if c.obj.id:  # logbook on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': c.obj.internal_key},
            )
        if isinstance(c, LogbookOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': c.obj.internal_key},
            )

        return self.success()

    @permissions(['Logbook'])
    def delete(self, associated_resource_type, resource_id, logbook_id):
        """
        ---
        description: Delete a logbook
        tags:
          - logbooks
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the logbook is on:
               "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra]
            description: |
               The ID of the source or spectrum
               that the logbook is posted to.
               This would be a string for a source ID
               or an integer for a spectrum.
          - in: path
            name: logbook_id
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
            logbook_id = int(logbook_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) logbook ID.")

        if associated_resource_type.lower() == "sources":
            try:
                c = Logbook.get_if_accessible_by(
                    logbook_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(c.obj_id)
        elif associated_resource_type.lower() == "spectra":
            try:
                c = LogbookOnSpectrum.get_if_accessible_by(
                    logbook_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(c.spectrum_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        obj_key = c.obj.internal_key

        if logbook_resource_id_str != resource_id:
            return self.error(
                f'Logbook resource ID does not match resource ID given in path ({resource_id})'
            )

        DBSession().delete(c)
        self.verify_and_commit()

        if c.obj.id:  # logbook on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_key},
            )
        if isinstance(c, LogbookOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': obj_key},
            )

        return self.success()


class LogbookAttachmentHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, logbook_id):
        """
        ---
        description: Download logbook attachment
        tags:
          - logbooks
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum]
            description: |
               What underlying data the logbook is on:
               "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra]
            description: |
               The ID of the source or spectrum
               that the logbook is posted to.
               This would be a string for a source ID
               or an integer for a spectrum.
          - in: path
            name: logbook_id
            required: true
            schema:
              type: integer
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
                            logbook_id:
                              type: integer
                              description: Logbook ID attachment came from
                            attachment:
                              type: string
                              description: The attachment file contents decoded as a string

        """

        try:
            logbook_id = int(logbook_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) logbook ID. ")

        download = strtobool(self.get_query_argument('download', "True").lower())

        if associated_resource_type.lower() == "sources":
            try:
                logbook = Logbook.get_if_accessible_by(
                    logbook_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(logbook.obj_id)

        elif associated_resource_type.lower() == "spectra":
            try:
                logbook = LogbookOnSpectrum.get_if_accessible_by(
                    logbook_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error('Could not find any accessible logbooks.', status=403)
            logbook_resource_id_str = str(logbook.spectrum_id)
        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        if logbook_resource_id_str != resource_id:
            return self.error(
                f'Logbook resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if not logbook.attachment_bytes:
            return self.error('Logbook has no attachment')

        if download:
            self.set_header(
                "Content-Disposition",
                "attachment; " f"filename={logbook.attachment_name}",
            )
            self.set_header("Content-type", "application/octet-stream")
            self.write(base64.b64decode(logbook.attachment_bytes))
        else:
            return self.success(
                data={
                    "logbookId": int(logbook_id),
                    "attachment": base64.b64decode(logbook.attachment_bytes).decode(),
                }
            )

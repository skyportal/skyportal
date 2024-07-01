import string
import base64
from marshmallow.exceptions import ValidationError
import os
import sqlalchemy as sa
import time
import unicodedata

from baselayer.app.access import permissions, auth_or_token
from baselayer.app.env import load_env
from baselayer.log import make_log

from ..base import BaseHandler
from ...utils.sizeof import sizeof, SIZE_WARNING_THRESHOLD
from ...utils.fits_display import get_fits_preview
from ...models import (
    Comment,
    CommentOnSpectrum,
    CommentOnGCN,
    CommentOnEarthquake,
    CommentOnShift,
    EarthquakeEvent,
    Spectrum,
    GcnEvent,
    Instrument,
    Shift,
    Group,
    User,
    UserNotification,
    Token,
)

_, cfg = load_env()

log = make_log('api/comment')

MAX_COMMENTS_NO_RESOURCE_ID = 1000

AUDIO_EXTENSION_TO_CONTENT_TYPE = {
    'aac': 'audio/aac',
    'mp3': 'audio/mpeg',
    'oga': 'audio/ogg',
    'wav': 'audio/wav',
}

VIDEO_EXTENSION_TO_CONTENT_TYPE = {
    'mp4': 'video/mp4',
    'ogg': 'video/ogg',
    'ogv': 'video/ogg',
    'webm': 'video/webm',
}

IMAGE_EXTENSION_TO_CONTENT_TYPE = {
    'apng': 'image/apng',
    'avif': 'image/avif',
    'bmp': 'image/bmp',
    'gif': 'image/gif',
    'ico': 'image/x-icon',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpeg',
    'png': 'image/png',
    'svg': 'image/svg+xml',
    'webp': 'image/webp',
}

TEXT_EXTENSION_TO_CONTENT_TYPE = {
    'txt': 'text/plain',
    'log': 'text/plain',
    'logs': 'text/plain',
    'csv': 'text/csv',
    'htm': 'text/html',
    'html': 'text/html',
    'js': 'text/javascript',
    'mjs': 'text/javascript',
    'json': 'application/json',
    'xml': 'application/xml',
    'pdf': 'application/pdf',
}

EXTENSION_TO_CONTENT_TYPE = {
    **AUDIO_EXTENSION_TO_CONTENT_TYPE,
    **VIDEO_EXTENSION_TO_CONTENT_TYPE,
    **IMAGE_EXTENSION_TO_CONTENT_TYPE,
    **TEXT_EXTENSION_TO_CONTENT_TYPE,
}


def users_mentioned(text, session):
    punctuation = string.punctuation.replace("-", "").replace("@", "")
    usernames = []
    for word in text.replace(",", " ").split():
        word = word.strip(punctuation)
        if word.startswith("@"):
            usernames.append(word.replace("@", ""))
    users = session.scalars(
        User.select(session.user_or_token).where(
            User.username.in_(usernames),
            User.preferences["notifications"]["mention"]["active"]
            .astext.cast(sa.Boolean)
            .is_(True),
        )
    ).all()

    return users


def instruments_mentioned(text, session):
    punctuation = string.punctuation.replace("-", "").replace("#", "")
    instruments = []
    for word in text.replace(",", " ").split():
        word = word.strip(punctuation)
        if word.startswith("#"):
            instruments.append(word.replace("#", ""))

    instruments = session.scalars(
        Instrument.select(session.user_or_token).where(
            Instrument.name.in_(instruments),
        )
    ).all()

    usernames = []
    for instrument in instruments:
        allocations = instrument.allocations
        for allocation in allocations:
            allocation_users = [
                user.user.username for user in allocation.allocation_users
            ]
            usernames = usernames + allocation_users
    usernames = list(set(usernames))

    users = session.scalars(
        User.select(session.user_or_token).where(
            User.username.in_(usernames),
            User.preferences["notifications"]["mention"]["active"]
            .astext.cast(sa.Boolean)
            .is_(True),
        )
    ).all()

    return users


class CommentHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id=None, comment_id=None):
        """
        ---
        single:
          description: Retrieve a comment
          tags:
            - comments
            - sources
            - spectra
            - shifts
            - earthquakes
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
              description: |
                 What underlying data the comment is on:
                 "sources" or "spectra" or "gcn_event" or "earthquake" or "shift".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
                enum: [sources, spectra, gcn_event]
              description: |
                 The ID of the source, spectrum, gcn_event, earthquake, or shift
                 that the comment is posted to.
                 This would be a string for a source ID
                 or an integer for a spectrum, gcn_event, earthquake, or shift.
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
            - gcn_events
            - earthquakes
            - shifts
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources]
              description: |
                 What underlying data the comment is on, e.g., "sources"
                 or "spectra" or "gcn_event" or "earthquake" or "shift".
            - in: path
              name: resource_id
              required: false
              schema:
                type: string
              description: |
                 The ID of the underlying data.
                 This would be a string for a source ID
                 or an integer for other data types like spectrum, gcn_event, earthquake, or shift.
            - in: query
              name: text
              schema:
                type: string
              description: |
                Filter comments by partial text match.
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

        text = self.get_query_argument("text", None)
        pageNumber = self.get_query_argument("pageNumber", None)
        numPerPage = self.get_query_argument("numPerPage", None)

        start = time.time()

        with self.Session() as session:
            if comment_id is None:
                if resource_id is None and (text is None or str(text).strip() == ""):
                    return self.error(
                        "Please provide a resource_id or text to search for."
                    )
                table, resource_id_col = None, None
                if associated_resource_type.lower() == "sources":
                    table, resource_id_col = Comment, "obj_id"
                elif associated_resource_type.lower() == "spectra":
                    table, resource_id_col = CommentOnSpectrum, "spectrum_id"
                elif associated_resource_type.lower() == "gcn_event":
                    table, resource_id_col = CommentOnGCN, "gcn_id"
                elif associated_resource_type.lower() == "earthquake":
                    table, resource_id_col = CommentOnEarthquake, "earthquake_id"
                elif associated_resource_type.lower() == "shift":
                    table, resource_id_col = CommentOnShift, "shift_id"
                else:
                    return self.error(
                        f'Unsupported associated resource type "{associated_resource_type}".'
                    )

                stmt = table.select(session.user_or_token)
                if resource_id is not None:
                    stmt = stmt.where(getattr(table, resource_id_col) == resource_id)
                if text is not None:
                    pageNumber = 1 if pageNumber is None else int(pageNumber)
                    if pageNumber < 1:
                        return self.error("Page number must be greater than 0.")
                    numPerPage = 25 if numPerPage is None else int(numPerPage)
                    if numPerPage < 1:
                        return self.error("Number per page must be greater than 0.")
                    if numPerPage > MAX_COMMENTS_NO_RESOURCE_ID:
                        return self.error(
                            f"Number per page must be less than {MAX_COMMENTS_NO_RESOURCE_ID}."
                        )
                    stmt = stmt.where(
                        table.text.ilike(f"%{str(text).lower()}%")
                    ).order_by(table.created_at.desc())

                comments = session.scalars(stmt).unique().all()

                if associated_resource_type in [
                    "sources",
                    "spectra",
                    "earthquake",
                    "shift",
                ]:
                    query_output = [
                        {
                            **c.to_dict(),
                            'resourceType': associated_resource_type.lower(),
                        }
                        for c in comments
                    ]
                elif associated_resource_type == "gcn_event":
                    query_output = [
                        {
                            **c.to_dict(),
                            'resourceType': 'gcn_event',
                            'dateobs': c.gcn.dateobs,
                        }
                        for c in comments
                    ]
                else:
                    return self.error(
                        f'Unsupported associated resource type "{associated_resource_type}".'
                    )
                query_size = sizeof(query_output)
                if query_size >= SIZE_WARNING_THRESHOLD:
                    end = time.time()
                    duration = end - start
                    log(
                        f'User {self.associated_user_object.id} comment query returned {query_size} bytes in {duration} seconds'
                    )

                return self.success(data=query_output)

            try:
                comment_id = int(comment_id)
            except (TypeError, ValueError):
                return self.error("Must provide a valid (scalar integer) comment ID. ")

            # the default is to comment on an object
            if associated_resource_type.lower() == "sources":
                comment = session.scalars(
                    Comment.select(session.user_or_token).where(
                        Comment.id == comment_id
                    )
                ).first()
                if comment is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(comment.obj_id)

            elif associated_resource_type.lower() == "spectra":
                comment = session.scalars(
                    CommentOnSpectrum.select(session.user_or_token).where(
                        CommentOnSpectrum.id == comment_id
                    )
                ).first()
                if comment is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(comment.spectrum_id)
            elif associated_resource_type.lower() == "gcn_event":
                comment = session.scalars(
                    CommentOnGCN.select(session.user_or_token).where(
                        CommentOnGCN.id == comment_id
                    )
                ).first()
                if comment is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(comment.gcn_id)
            elif associated_resource_type.lower() == "earthquake":
                comment = session.scalars(
                    CommentOnEarthquake.select(session.user_or_token).where(
                        CommentOnEarthquake.id == comment_id
                    )
                ).first()
                if comment is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(comment.gcn_id)
            elif associated_resource_type.lower() == "shift":
                comment = session.scalars(
                    CommentOnShift.select(session.user_or_token).where(
                        CommentOnShift.id == comment_id
                    )
                ).first()
                if comment is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(comment.shift_id)
            # add more options using elif
            else:
                return self.error(
                    f'Unsupported associated_resource_type "{associated_resource_type}".'
                )

            if comment_resource_id_str != resource_id:
                return self.error(
                    f'Comment resource ID does not match resource ID given in path ({resource_id})'
                )

            comment_data = {
                **comment.to_dict(),
                'resourceType': associated_resource_type.lower(),
            }
            query_size = sizeof(comment_data)
            if query_size >= SIZE_WARNING_THRESHOLD:
                end = time.time()
                duration = end - start
                log(
                    f'User {self.associated_user_object.id} source query returned {query_size} bytes in {duration} seconds'
                )

            return self.success(data=comment_data)

    @permissions(['Comment'])
    def post(self, associated_resource_type, resource_id):
        """
        ---
        description: Post a comment
        tags:
          - comments
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum, gcn_event, earthquake, shift]
            description: |
               What underlying data the comment is on:
               "source" or "spectrum" or "gcn_event" or "earthquake" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event, earthquake, shift]
            description: |
               The ID of the source or spectrum
               that the comment is posted to.
               This would be a string for a source ID
               or an integer for a spectrum, gcn_event, earthquake, or shift.
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
                      able to view comment. Defaults to the public group.
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
        attachment_bytes, attachment_name, data_to_disk = None, None, None

        if 'attachment' in data:
            if (
                isinstance(data['attachment'], dict)
                and 'body' in data['attachment']
                and 'name' in data['attachment']
            ):
                attachment_name = data['attachment']['name']
                data_to_disk = base64.b64decode(
                    data['attachment']['body'].split('base64,')[-1]
                )
            else:
                return self.error("Malformed comment attachment")

        author = self.associated_user_object
        is_bot_request = isinstance(self.current_user, Token)

        with self.Session() as session:
            try:
                group_ids = data.pop('group_ids', None)
                if not isinstance(group_ids, list) or len(group_ids) == 0:
                    public_group = session.scalar(
                        sa.select(Group.id).where(
                            Group.name == cfg['misc.public_group_name']
                        )
                    )
                    if public_group is None:
                        return self.error(
                            f'No group_ids were specified and the public group "{cfg["misc.public_group_name"]}" does not exist. Cannot post comment'
                        )
                    group_ids = [public_group]
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()
                if {g.id for g in groups} != set(group_ids):
                    return self.error(
                        f'Cannot find one or more groups with IDs: {group_ids}.'
                    )

                existing = None
                if associated_resource_type.lower() == "sources":
                    obj_id = resource_id
                    existing = session.scalars(
                        Comment.select(session.user_or_token).where(
                            Comment.text == comment_text,
                            Comment.obj_id == obj_id,
                            Comment.attachment_bytes == attachment_bytes,
                            Comment.attachment_name == attachment_name,
                            Comment.author_id == author.id,
                            Comment.bot == is_bot_request,
                        )
                    ).first()
                    if existing is not None:
                        if {g.id for g in existing.groups} != set(group_ids):
                            existing = None
                    if existing is None:
                        comment = Comment(
                            text=comment_text,
                            obj_id=obj_id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=author,
                            groups=groups,
                            bot=is_bot_request,
                        )
                elif associated_resource_type.lower() == "spectra":
                    spectrum_id = resource_id
                    spectrum = session.scalars(
                        Spectrum.select(session.user_or_token).where(
                            Spectrum.id == spectrum_id
                        )
                    ).first()
                    if spectrum is None:
                        return self.error(
                            f'Could not find any accessible spectra with ID {spectrum_id}.'
                        )
                    existing = session.scalars(
                        CommentOnSpectrum.select(session.user_or_token).where(
                            CommentOnSpectrum.text == comment_text,
                            CommentOnSpectrum.spectrum_id == spectrum_id,
                            CommentOnSpectrum.attachment_bytes == attachment_bytes,
                            CommentOnSpectrum.attachment_name == attachment_name,
                            CommentOnSpectrum.author_id == author.id,
                            CommentOnSpectrum.bot == is_bot_request,
                        )
                    ).first()
                    if existing is not None:
                        if {g.id for g in existing.groups} != set(group_ids):
                            existing = None
                    if existing is None:
                        comment = CommentOnSpectrum(
                            text=comment_text,
                            spectrum_id=spectrum_id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=author,
                            groups=groups,
                            bot=is_bot_request,
                            obj_id=spectrum.obj_id,
                        )

                elif associated_resource_type.lower() == "gcn_event":
                    gcnevent_id = resource_id
                    gcn_event = session.scalars(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.id == gcnevent_id
                        )
                    ).first()
                    if gcn_event is None:
                        return self.error(
                            f'Could not find any accessible gcn events with ID {gcnevent_id}.'
                        )
                    existing = session.scalars(
                        CommentOnGCN.select(session.user_or_token).where(
                            CommentOnGCN.text == comment_text,
                            CommentOnGCN.gcn_id == gcnevent_id,
                            CommentOnGCN.attachment_bytes == attachment_bytes,
                            CommentOnGCN.attachment_name == attachment_name,
                            CommentOnGCN.author_id == author.id,
                            CommentOnGCN.bot == is_bot_request,
                        )
                    ).first()
                    if existing is not None:
                        if {g.id for g in existing.groups} != set(group_ids):
                            existing = None
                    if existing is None:
                        comment = CommentOnGCN(
                            text=comment_text,
                            gcn_id=gcn_event.id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=author,
                            groups=groups,
                            bot=is_bot_request,
                        )
                elif associated_resource_type.lower() == "earthquake":
                    earthquake_id = resource_id
                    earthquake = session.scalars(
                        EarthquakeEvent.select(session.user_or_token).where(
                            EarthquakeEvent.id == earthquake_id
                        )
                    ).first()
                    if earthquake is None:
                        return self.error(
                            f'Could not find any accessible earthquakes with ID {earthquake_id}.'
                        )
                    existing = session.scalars(
                        CommentOnEarthquake.select(session.user_or_token).where(
                            CommentOnEarthquake.text == comment_text,
                            CommentOnEarthquake.earthquake_id == earthquake_id,
                            CommentOnEarthquake.attachment_bytes == attachment_bytes,
                            CommentOnEarthquake.attachment_name == attachment_name,
                            CommentOnEarthquake.author_id == author.id,
                            CommentOnEarthquake.bot == is_bot_request,
                        )
                    ).first()
                    if existing is not None:
                        if {g.id for g in existing.groups} != set(group_ids):
                            existing = None
                    if existing is None:
                        comment = CommentOnEarthquake(
                            text=comment_text,
                            earthquake_id=earthquake.id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=author,
                            groups=groups,
                            bot=is_bot_request,
                        )
                elif associated_resource_type.lower() == "shift":
                    shift_id = resource_id
                    shift = session.scalars(
                        Shift.select(session.user_or_token).where(Shift.id == shift_id)
                    ).first()
                    if shift is None:
                        return self.error(
                            f'Could not access Shift {shift.id}.', status=403
                        )
                    existing = session.scalars(
                        CommentOnShift.select(session.user_or_token).where(
                            CommentOnShift.text == comment_text,
                            CommentOnShift.shift_id == shift_id,
                            CommentOnShift.attachment_bytes == attachment_bytes,
                            CommentOnShift.attachment_name == attachment_name,
                            CommentOnShift.author_id == author.id,
                            CommentOnShift.bot == is_bot_request,
                        )
                    ).first()
                    if existing is not None:
                        if {g.id for g in existing.groups} != set(group_ids):
                            existing = None
                    if existing is None:
                        comment = CommentOnShift(
                            text=comment_text,
                            shift_id=shift.id,
                            attachment_bytes=attachment_bytes,
                            attachment_name=attachment_name,
                            author=author,
                            groups=groups,
                            bot=is_bot_request,
                        )
                else:
                    return self.error(
                        f'Unknown resource type "{associated_resource_type}".'
                    )

                if existing is not None:
                    return self.success(
                        data={
                            'comment_id': existing.id,
                            "message": "Same comment already exists.",
                        }
                    )

                users_mentioned_in_comment = users_mentioned(comment_text, session)
                if associated_resource_type.lower() == "sources":
                    text_to_send = f"*@{self.associated_user_object.username}* mentioned you in a comment on *{obj_id}*"
                    url_endpoint = f"/source/{obj_id}"
                elif associated_resource_type.lower() == "spectra":
                    text_to_send = f"*@{self.associated_user_object.username}* mentioned you in a comment on *{spectrum_id}*"
                    url_endpoint = f"/source/{spectrum_id}"
                elif associated_resource_type.lower() == "gcn_event":
                    text_to_send = f"*@{self.associated_user_object.username}* mentioned you in a comment on *{gcnevent_id}*"
                    url_endpoint = f"/gcn_events/{gcnevent_id}"
                elif associated_resource_type.lower() == "shift":
                    text_to_send = f"*@{self.associated_user_object.username}* mentioned you in a comment on *shift {shift_id}*"
                    url_endpoint = "/shifts"
                elif associated_resource_type.lower() == "earthquake":
                    text_to_send = f"*@{self.associated_user_object.username}* mentioned you in a comment on *{earthquake_id}*"
                    url_endpoint = f"/earthquakes/{earthquake_id}"
                else:
                    return self.error(
                        f'Unknown resource type "{associated_resource_type}".'
                    )

                if users_mentioned_in_comment:
                    for user_mentioned in users_mentioned_in_comment:
                        session.add(
                            UserNotification(
                                user=user_mentioned,
                                text=text_to_send,
                                notification_type="mention",
                                url=url_endpoint,
                            )
                        )

                users_mentioned_in_instrument_comment = instruments_mentioned(
                    comment_text, session
                )
                if associated_resource_type.lower() == "sources":
                    text_to_send = (
                        f"*@{self.associated_user_object.username}* "
                        "mentioned an instrument you have an "
                        f"allocation on in a comment on *{obj_id}*"
                    )
                    url_endpoint = f"/source/{obj_id}"
                elif associated_resource_type.lower() == "spectra":
                    text_to_send = (
                        f"*@{self.associated_user_object.username}* "
                        "mentioned an instrument you have an "
                        f"allocation on in a comment on *{spectrum_id}*"
                    )
                    url_endpoint = f"/source/{spectrum_id}"
                elif associated_resource_type.lower() == "gcn_event":
                    text_to_send = (
                        f"*@{self.associated_user_object.username}* "
                        "mentioned an instrument you have an "
                        f"allocation on in a comment on *{gcnevent_id}*"
                    )
                    url_endpoint = f"/gcn_events/{gcnevent_id}"
                elif associated_resource_type.lower() == "shift":
                    text_to_send = (
                        f"*@{self.associated_user_object.username}* "
                        "mentioned an instrument you have an "
                        "allocation on in a comment on *shift {shift_id}*"
                    )
                    url_endpoint = "/shifts"
                elif associated_resource_type.lower() == "earthquake":
                    text_to_send = (
                        f"*@{self.associated_user_object.username}* "
                        "mentioned an instrument you have an "
                        "allocation on in a comment on *{earthquake_id}*"
                    )
                    url_endpoint = f"/earthquakes/{earthquake_id}"
                else:
                    return self.error(
                        f'Unknown resource type "{associated_resource_type}".'
                    )

                if users_mentioned_in_instrument_comment:
                    for user_mentioned in users_mentioned_in_instrument_comment:
                        session.add(
                            UserNotification(
                                user=user_mentioned,
                                text=text_to_send,
                                notification_type="mention",
                                url=url_endpoint,
                            )
                        )

                session.add(comment)
                session.commit()
                if data_to_disk is not None:
                    comment.save_data(attachment_name, data_to_disk)
                    session.commit()

                if users_mentioned_in_comment:
                    for user_mentioned in users_mentioned_in_comment:
                        self.flow.push(
                            user_mentioned.id, "skyportal/FETCH_NOTIFICATIONS", {}
                        )

                if hasattr(
                    comment, 'obj'
                ):  # comment on object, or object related resources
                    self.push_all(
                        action='skyportal/REFRESH_SOURCE',
                        payload={'obj_key': comment.obj.internal_key},
                    )

                if isinstance(comment, CommentOnGCN):
                    self.push_all(
                        action='skyportal/REFRESH_GCN_EVENT',
                        payload={'gcnEvent_dateobs': comment.gcn.dateobs},
                    )
                elif isinstance(comment, CommentOnEarthquake):
                    self.push_all(
                        action='skyportal/REFRESH_EARTHQUAKE',
                        payload={'earthquake_event_id': comment.earthquake.event_id},
                    )
                elif isinstance(comment, CommentOnSpectrum):
                    self.push_all(
                        action='skyportal/REFRESH_SOURCE_SPECTRA',
                        payload={'obj_internal_key': comment.obj.internal_key},
                    )
                elif isinstance(comment, CommentOnShift):
                    self.push_all(
                        action='skyportal/REFRESH_SHIFT',
                        payload={'shift_id': comment.shift_id},
                    )

                return self.success(data={'comment_id': comment.id})
            except Exception as e:
                session.rollback()
                return self.error(
                    f'Error posting comment for {associated_resource_type} {resource_id}: {str(e)}'
                )

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
              enum: [sources, spectrum, gcn_event, shift]
            description: |
               What underlying data the comment is on:
               "sources" or "spectra" or "gcn_event" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event, shift]
            description: |
               The ID of the source or spectrum
               that the comment is posted to.
               This would be a string for an object ID
               or an integer for a spectrum, gcn_event or shift.
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

        with self.Session() as session:
            try:
                if associated_resource_type.lower() == "sources":
                    schema = Comment.__schema__()
                    c = session.scalars(
                        Comment.select(session.user_or_token, mode="update").where(
                            Comment.id == comment_id
                        )
                    ).first()
                    if c is None:
                        return self.error(
                            'Could not find any accessible comments.', status=403
                        )
                    comment_resource_id_str = str(c.obj_id)

                elif associated_resource_type.lower() == "spectra":
                    schema = CommentOnSpectrum.__schema__()
                    c = session.scalars(
                        CommentOnSpectrum.select(
                            session.user_or_token, mode="update"
                        ).where(CommentOnSpectrum.id == comment_id)
                    ).first()
                    if c is None:
                        return self.error(
                            'Could not find any accessible comments.', status=403
                        )
                    comment_resource_id_str = str(c.spectrum_id)

                elif associated_resource_type.lower() == "gcn_event":
                    schema = CommentOnGCN.__schema__()
                    c = session.scalars(
                        CommentOnGCN.select(session.user_or_token, mode="update").where(
                            CommentOnGCN.id == comment_id
                        )
                    ).first()
                    if c is None:
                        return self.error(
                            'Could not find any accessible comments.', status=403
                        )
                    comment_resource_id_str = str(c.gcn_id)
                elif associated_resource_type.lower() == "earthquake":
                    schema = CommentOnEarthquake.__schema__()
                    c = session.scalars(
                        CommentOnEarthquake.select(
                            session.user_or_token, mode="update"
                        ).where(CommentOnEarthquake.id == comment_id)
                    ).first()
                    if c is None:
                        return self.error(
                            'Could not find any accessible comments.', status=403
                        )
                    comment_resource_id_str = str(c.gcn_id)
                elif associated_resource_type.lower() == "shift":
                    schema = CommentOnShift.__schema__()
                    c = session.scalars(
                        CommentOnShift.select(
                            session.user_or_token, mode="update"
                        ).where(CommentOnShift.id == comment_id)
                    ).first()
                    if c is None:
                        return self.error(
                            'Could not find any accessible comments.', status=403
                        )
                    comment_resource_id_str = str(c.shift_id)
                # add more options using elif
                else:
                    return self.error(
                        f'Unsupported associated_resource_type "{associated_resource_type}".'
                    )

                data = self.get_json()
                group_ids = data.pop("group_ids", None)
                data['id'] = comment_id

                attachment_name, data_to_disk = None, None
                attachment = data.pop('attachment', None)
                if attachment:
                    if (
                        isinstance(attachment, dict)
                        and 'body' in attachment
                        and 'name' in attachment
                    ):
                        attachment_name = attachment['name']
                        data_to_disk = base64.b64decode(
                            attachment['body'].split('base64,')[-1]
                        )
                    else:
                        return self.error("Malformed comment attachment")

                try:
                    schema.load(data, partial=True)
                except ValidationError as e:
                    return self.error(
                        f'Invalid/missing parameters: {e.normalized_messages()}'
                    )

                if 'text' in data:
                    c.text = data['text']
                if attachment_name:
                    c.attachment_name = attachment_name

                if isinstance(group_ids, list) and len(group_ids) > 0:
                    groups = session.scalars(
                        Group.select(session.user_or_token).where(
                            Group.id.in_(group_ids)
                        )
                    ).all()
                    if {g.id for g in groups} != set(group_ids):
                        return self.error(
                            f'Cannot find one or more groups with IDs: {group_ids}.'
                        )
                    c.groups = groups

                if comment_resource_id_str != resource_id:
                    return self.error(
                        f'Comment resource ID does not match resource ID given in path ({resource_id})'
                    )

                session.add(c)
                session.commit()
                if data_to_disk is not None:
                    c.save_data(attachment_name, data_to_disk)
                    session.commit()

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
                elif isinstance(c, CommentOnGCN):  # also update the gcn
                    self.push_all(
                        action='skyportal/REFRESH_GCN_EVENT',
                        payload={'gcnEvent_dateobs': c.gcn.dateobs},
                    )
                elif isinstance(c, CommentOnEarthquake):  # also update the earthquake
                    self.push_all(
                        action='skyportal/REFRESH_EARTHQUAKE',
                        payload={'earthquake_id': c.earthquake.event_id},
                    )
                elif isinstance(c, CommentOnShift):  # also update the shift
                    self.push_all(
                        action='skyportal/REFRESH_SHIFT',
                        payload={'shift_id': c.shift_id},
                    )

                return self.success()
            except Exception as e:
                return self.error(
                    f'Failed to update comment with ID {comment_id}: {str(e)}'
                )

    @permissions(['Comment'])
    def delete(self, associated_resource_type, resource_id, comment_id):
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

        with self.Session() as session:
            if associated_resource_type.lower() == "sources":
                c = session.scalars(
                    Comment.select(session.user_or_token, mode="delete").where(
                        Comment.id == comment_id
                    )
                ).first()
                if c is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(c.obj_id)
            elif associated_resource_type.lower() == "spectra":
                c = session.scalars(
                    CommentOnSpectrum.select(
                        session.user_or_token, mode="delete"
                    ).where(CommentOnSpectrum.id == comment_id)
                ).first()
                if c is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(c.spectrum_id)
            elif associated_resource_type.lower() == "gcn_event":
                c = session.scalars(
                    CommentOnGCN.select(session.user_or_token, mode="delete").where(
                        CommentOnGCN.id == comment_id
                    )
                ).first()
                if c is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(c.gcn_id)
            elif associated_resource_type.lower() == "earthquake":
                c = session.scalars(
                    CommentOnEarthquake.select(
                        session.user_or_token, mode="delete"
                    ).where(CommentOnEarthquake.id == comment_id)
                ).first()
                if c is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(c.earthquake_id)
            elif associated_resource_type.lower() == "shift":
                c = session.scalars(
                    CommentOnShift.select(session.user_or_token, mode="delete").where(
                        CommentOnShift.id == comment_id
                    )
                ).first()
                if c is None:
                    return self.error(
                        'Could not find any accessible comments.', status=403
                    )
                comment_resource_id_str = str(c.shift_id)

            # add more options using elif
            else:
                return self.error(
                    f'Unsupported associated_resource_type "{associated_resource_type}".'
                )

            if isinstance(c, CommentOnGCN):
                gcnevent_dateobs = c.gcn.dateobs
            elif isinstance(c, CommentOnEarthquake):
                event_id = c.earthquake.event_id
            elif isinstance(c, CommentOnShift):
                shift_id = c.shift_id
            else:
                obj_key = c.obj.internal_key

            if comment_resource_id_str != resource_id:
                return self.error(
                    f'Comment resource ID does not match resource ID given in path ({resource_id})'
                )

            session.delete(c)
            session.commit()

            if hasattr(c, 'obj'):  # comment on object, or object related resources
                self.push_all(
                    action='skyportal/REFRESH_SOURCE',
                    payload={'obj_key': obj_key},
                )

            if isinstance(c, CommentOnGCN):  # also update the GcnEvent
                self.push_all(
                    action='skyportal/REFRESH_GCN_EVENT',
                    payload={'gcnEvent_dateobs': gcnevent_dateobs},
                )
            elif isinstance(c, CommentOnEarthquake):  # also update the earthquake
                self.push_all(
                    action='skyportal/REFRESH_EARTHQUAKE',
                    payload={'earthquake_event_id': event_id},
                )
            elif isinstance(c, CommentOnSpectrum):  # also update the spectrum
                self.push_all(
                    action='skyportal/REFRESH_SOURCE_SPECTRA',
                    payload={'obj_internal_key': obj_key},
                )
            elif isinstance(c, CommentOnShift):  # also update the shift
                self.push_all(
                    action='skyportal/REFRESH_SHIFT',
                    payload={'shift_id': shift_id},
                )

            return self.success()


class CommentAttachmentHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, comment_id):
        """
        ---
        description: Download comment attachment
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
               or an integer for a spectrum.
          - in: path
            name: comment_id
            required: true
            schema:
              type: integer
          - in: query
            name: download
            nullable: True
            schema:
              type: boolean
              description: If true, download the attachment; else return file data as text. True by default.
          - in: query
            name: preview
            nullable: True
            schema:
              type: boolean
              description: If true, return an attachment preview. False by default.
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
        try:
            comment_id = int(comment_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) comment ID. ")

        download = self.get_query_argument('download', True)
        preview = self.get_query_argument('preview', False)

        if download is True and preview is True:
            return self.error(
                'Cannot set both download and preview to True. Please set only one to True, or set both to False.'
            )

        table, resource_id_col = None, None
        if associated_resource_type.lower() == "sources":
            table, resource_id_col = Comment, "obj_id"
        elif associated_resource_type.lower() == "spectra":
            table, resource_id_col = CommentOnSpectrum, "spectrum_id"
        elif associated_resource_type.lower() == "gcn_event":
            table, resource_id_col = CommentOnGCN, "gcn_id"
        elif associated_resource_type.lower() == "earthquake":
            table, resource_id_col = CommentOnEarthquake, "earthquake_id"
        elif associated_resource_type.lower() == "shift":
            table, resource_id_col = CommentOnShift, "shift_id"
        else:
            return self.error(
                f'Unsupported associated resource type "{associated_resource_type}".'
            )

        with self.Session() as session:
            comment = session.scalars(
                table.select(session.user_or_token).where(table.id == comment_id)
            ).first()
            if comment is None:
                return self.error('Could not find any accessible comments.', status=403)

            if str(getattr(comment, resource_id_col)) != str(resource_id):
                return self.error(
                    f'Comment resource ID does not match resource ID given in path ({resource_id})'
                )

            data_path = comment.get_attachment_path()
            if not comment.attachment_bytes and not data_path:
                return self.error('Comment has no attachment')

            if data_path is None:
                try:
                    attachment = base64.b64decode(comment.attachment_bytes)
                except Exception as e:
                    return self.error(f'Error decoding comment attachment: {e}')
            else:
                try:
                    if os.path.isfile(data_path):
                        with open(data_path, 'rb') as f:
                            attachment = f.read()
                    else:
                        return self.error(
                            f'Comment attachment cannot be found on disk: {data_path}'
                        )
                except Exception as e:
                    return self.error(f'Error reading comment attachment: {e}')

            attachment_name = ''.join(
                c
                for c in unicodedata.normalize('NFD', comment.attachment_name)
                if unicodedata.category(c) != 'Mn'
            )
            # we remove all non-ascii characters from the attachment name, which tornado does not like
            # as they can't be encoded in latin-1
            attachment_name = ''.join(
                [i if ord(i) < 128 else ' ' for i in attachment_name]
            )

            if download:
                self.set_header(
                    "Content-Disposition",
                    f'attachment; filename="{attachment_name}"',
                )
                self.set_header("Content-type", "application/octet-stream")
                return self.write(attachment)

            if preview:
                if attachment_name.lower().endswith(
                    (".fit", ".fits", ".fit.fz", ".fits.fz")
                ):
                    try:
                        attachment = get_fits_preview(attachment_name, attachment)
                        attachment_name = os.path.splitext(attachment_name)[0] + ".png"
                    except Exception as e:
                        log(f'Cannot render {attachment_name} as image: {str(e)}')
                        return self.error(
                            f'Cannot render {attachment_name} as image: {str(e)}'
                        )

                extension = attachment_name.split('.')[-1].strip().lower()
                if extension not in EXTENSION_TO_CONTENT_TYPE:
                    return self.error(
                        f'Unsupported file type "{extension}" for preview, must be one of: "{EXTENSION_TO_CONTENT_TYPE.keys()}"'
                    )

                self.set_header(
                    "Content-Disposition",
                    f'inline; filename="{attachment_name}"',
                )
                self.set_header("Content-type", EXTENSION_TO_CONTENT_TYPE[extension])
                return self.write(attachment)

            comment_data = {
                "commentId": int(comment_id),
                "attachment": attachment.decode('utf-8')
                if isinstance(attachment, bytes)
                else attachment,
                "attachmentName": attachment_name,
            }

            query_size = sizeof(comment_data)
            if query_size >= SIZE_WARNING_THRESHOLD:
                log(
                    f'User {self.associated_user_object.id} comment attachment query ({table.__tablename__} with ID {comment_id}) returned {query_size} bytes'
                )

            return self.success(data=comment_data)

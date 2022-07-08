import arrow
import base64
from marshmallow.exceptions import ValidationError
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.access import permissions, auth_or_token
from baselayer.app.flow import Flow
from ..base import BaseHandler
from ...models import (
    DBSession,
    Reminder,
    ReminderOnSpectrum,
    ReminderOnGCN,
    ReminderOnShift,
    Spectrum,
    GcnEvent,
    Shift,
    Group,
    User,
    UserNotification,
    Token,
)


def post_reminder(
    user,
    associated_resource_type,
    resource_id,
    reminder_text,
    groups,
    users,
    is_bot_reminder,
    next_reminder,
    reminder_delay=0,
    number_of_reminders=1,
):
    """Post Reminder(s) to database.

    Parameters
    ----------
    user : baselayer.app.models.User
        User creating the reminder
    associated_resource_type: str
        What underlying data the reminder is on: source, spectrum or gcn_event
    resource_id : int
        The ID of the source or spectrum or gcn_event that the reminder is posted to. This would be a string for a source ID or an integer for a spectrum or gcn_event.
    reminder_text : str
        Text to post for reminder
    groups : skyportal.models.group.Group
        List of groups that have access to reminder
    users : baselayer.app.models.User
        List of users to post reminder for
    is_bot_reminder : bool
        Boolean indicating whether reminder was posted via a bot (token-based request).
    next_reminder : datetime.datetime
        Time for the next reminder
    reminder_delay : float
        Delay until next reminder in days.
    number_of_reminders : number
        Number of remaining requests.
    """

    reminders = []
    if associated_resource_type.lower() == "sources":
        obj_id = resource_id
        for user in users:
            reminders.append(
                Reminder(
                    text=reminder_text,
                    obj_id=obj_id,
                    groups=groups,
                    bot=is_bot_reminder,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
    elif associated_resource_type.lower() == "spectra":
        spectrum_id = resource_id
        try:
            spectrum = Spectrum.get_if_accessible_by(
                spectrum_id, user, raise_if_none=True
            )
        except AccessError:
            raise ValueError(f'Could not access spectrum {resource_id}.')
        for user in users:
            reminders.append(
                ReminderOnSpectrum(
                    text=reminder_text,
                    spectrum_id=spectrum_id,
                    groups=groups,
                    bot=is_bot_reminder,
                    obj_id=spectrum.obj_id,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
    elif associated_resource_type.lower() == "gcn_event":
        gcnevent_id = resource_id
        try:
            gcn_event = GcnEvent.get_if_accessible_by(
                gcnevent_id, user, raise_if_none=True
            )
        except AccessError:
            raise ValueError(f'Could not access GcnEvent {resource_id}.')
        for user in users:
            reminders.append(
                ReminderOnGCN(
                    text=reminder_text,
                    gcn_id=gcn_event.id,
                    groups=groups,
                    bot=is_bot_reminder,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
    elif associated_resource_type.lower() == "shift":
        shift_id = resource_id
        try:
            shift = Shift.get_if_accessible_by(shift_id, user, raise_if_none=True)
        except AccessError:
            raise ValueError(f'Could not access Shift {resource_id}.')
        for user in users:
            reminders.append(
                ReminderOnShift(
                    text=reminder_text,
                    shift_id=shift.id,
                    groups=groups,
                    bot=is_bot_reminder,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
    else:
        raise ValueError(f'Unknown resource type "{associated_resource_type}".')

    return reminders


class ReminderHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, reminder_id=None):
        """
        ---
        single:
          description: Retrieve a reminder
          tags:
            - reminders
            - sources
            - spectra
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
              description: |
                 What underlying data the reminder is on:
                 "sources" or "spectra" or "gcn_event".
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
                enum: [sources, spectra, gcn_event]
              description: |
                 The ID of the source, spectrum, or gcn_event
                 that the reminder is posted to.
                 This would be a string for a source ID
                 or an integer for a spectrum or gcn_event
            - in: path
              name: reminder_id
              required: true
              schema:
                type: integer

          responses:
            200:
              content:
                application/json:
                  schema: SingleReminder
            400:
              content:
                application/json:
                  schema: Error
        multiple:
          description: Retrieve all reminders associated with specified resource
          tags:
            - reminders
            - spectra
            - sources
            - gcn_event
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [sources]
              description: |
                 What underlying data the reminder is on, e.g., "sources"
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
                  schema: ArrayOfReminders
            400:
              content:
                application/json:
                  schema: Error
        """
        if reminder_id is None:
            if associated_resource_type.lower() == "sources":
                reminders = (
                    Reminder.query_records_accessible_by(self.current_user)
                    .filter(Reminder.obj_id == resource_id)
                    .all()
                )
            elif associated_resource_type.lower() == "spectra":
                reminders = (
                    ReminderOnSpectrum.query_records_accessible_by(self.current_user)
                    .filter(ReminderOnSpectrum.spectrum_id == resource_id)
                    .all()
                )
            elif associated_resource_type.lower() == "gcn_event":
                reminders = (
                    ReminderOnGCN.query_records_accessible_by(self.current_user)
                    .filter(ReminderOnGCN.gcn_id == resource_id)
                    .all()
                )
            elif associated_resource_type.lower() == "shift":
                reminders = (
                    ReminderOnShift.query_records_accessible_by(self.current_user)
                    .filter(ReminderOnShift.shift_id == resource_id)
                    .all()
                )
            else:
                return self.error(
                    f'Unsupported associated resource type "{associated_resource_type}".'
                )
            self.verify_and_commit()
            return self.success(data=reminders)

        try:
            reminder_id = int(reminder_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) reminder ID. ")

        # the default is to reminder on an object
        if associated_resource_type.lower() == "sources":
            try:
                reminder = Reminder.get_if_accessible_by(
                    reminder_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(reminder.obj_id)

        elif associated_resource_type.lower() == "spectra":
            try:
                reminder = ReminderOnSpectrum.get_if_accessible_by(
                    reminder_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(reminder.spectrum_id)
        elif associated_resource_type.lower() == "gcn_event":
            try:
                reminder = ReminderOnGCN.get_if_accessible_by(
                    reminder_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(reminder.gcn_id)
        elif associated_resource_type.lower() == "shift":
            try:
                reminder = ReminderOnShift.get_if_accessible_by(
                    reminder_id, self.current_user, raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(reminder.shift_id)
        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        if reminder_resource_id_str != resource_id:
            return self.error(
                f'Reminder resource ID does not match resource ID given in path ({resource_id})'
            )

        if not reminder.attachment_bytes:
            return self.success(data=reminder)
        else:
            return self.success(
                data={
                    "reminderId": int(reminder_id),
                    "text": reminder.text,
                    "attachment": base64.b64decode(reminder.attachment_bytes).decode(),
                    "attachment_name": str(reminder.attachment_name),
                }
            )

    @permissions(['Reminder'])
    def post(self, associated_resource_type, resource_id):
        """
        ---
        description: Post a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum, gcn_event]
            description: |
               What underlying data the reminder is on:
               "source" or "spectrum" or "gcn_event".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event]
            description: |
               The ID of the source or spectrum
               that the reminder is posted to.
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
                      able to view reminder. Defaults to all of requesting user's
                      groups.
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
                            reminder_id:
                              type: integer
                              description: New reminder ID
        """
        data = self.get_json()

        reminder_text = data.get("text")
        next_reminder = data.get("next_reminder")
        # error here with strip
        next_reminder = arrow.get(next_reminder).datetime
        reminder_delay = data.get("reminder_delay", 0)
        number_of_reminders = data.get("number_of_reminders", 1)
        with self.Session() as session:
            group_ids = data.pop('group_ids', None)
            if not group_ids:
                group_ids = [g.id for g in self.current_user.accessible_groups]
            try:
                groups = session.scalars(
                    Group.select(self.current_user).where(Group.id.in_(group_ids))
                ).all()
            except AccessError:
                return self.error('Could not find any accessible groups.', status=403)

            user_ids = data.pop('user_ids', None)
            if not user_ids:
                users = [self.associated_user_object]
            else:
                try:
                    users = session.query(User).filter(User.id.in_(user_ids)).all()
                except AccessError:
                    return self.error(
                        'Could not find any accessible users.', status=403
                    )

            is_bot_reminder = isinstance(self.current_user, Token)
            reminders = post_reminder(
                self.associated_user_object,
                associated_resource_type,
                resource_id,
                reminder_text,
                groups,
                users,
                is_bot_reminder,
                next_reminder,
                reminder_delay=reminder_delay,
                number_of_reminders=number_of_reminders,
            )
        DBSession().add_all(reminders)

        if associated_resource_type.lower() == "sources":
            text_to_send = f"*@{self.associated_user_object.username}* created a reminder on *{resource_id}*"
            url_endpoint = f"/source/{resource_id}"
        elif associated_resource_type.lower() == "spectra":
            text_to_send = f"*@{self.associated_user_object.username}* created a reminder on *{resource_id}*"
            url_endpoint = f"/source/{resource_id}"
        elif associated_resource_type.lower() == "gcn_event":
            text_to_send = f"*@{self.associated_user_object.username}* created a reminder on *{resource_id}*"
            url_endpoint = f"/gcn_events/{resource_id}"
        elif associated_resource_type.lower() == "shift":
            text_to_send = f"*@{self.associated_user_object.username}* created a reminder on *shift {resource_id}*"
            url_endpoint = "/shifts"
        else:
            return self.error(f'Unknown resource type "{associated_resource_type}".')

        ws_flow = Flow()
        for user in users:
            DBSession().add(
                UserNotification(
                    user=user,
                    text=text_to_send,
                    notification_type="mention",
                    url=url_endpoint,
                )
            )
            ws_flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS")

        self.verify_and_commit()

        return self.success(
            data={'reminder_ids': [reminder.id for reminder in reminders]}
        )

    @permissions(['Reminder'])
    def put(self, associated_resource_type, resource_id, reminder_id):
        """
        ---
        description: Update a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [sources, spectrum, gcn_event, shift]
            description: |
               What underlying data the reminder is on:
               "sources" or "spectra" or "gcn_event" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event, shift]
            description: |
               The ID of the source or spectrum
               that the reminder is posted to.
               This would be a string for an object ID
               or an integer for a spectrum, gcn_event or shift.
          - in: path
            name: reminder_id
            required: true
            schema:
              type: integer
        requestBody:
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ReminderNoID'
                  - type: object
                    properties:
                      group_ids:
                        type: array
                        items:
                          type: integer
                        description: |
                          List of group IDs corresponding to which groups should be
                          able to view reminder.
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
            reminder_id = int(reminder_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) reminder ID. ")

        if associated_resource_type.lower() == "sources":
            schema = Reminder.__schema__()
            try:
                c = Reminder.get_if_accessible_by(
                    reminder_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.obj_id)

        elif associated_resource_type.lower() == "spectra":
            schema = ReminderOnSpectrum.__schema__()
            try:
                c = ReminderOnSpectrum.get_if_accessible_by(
                    reminder_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.spectrum_id)

        elif associated_resource_type.lower() == "gcn_event":
            schema = ReminderOnGCN.__schema__()
            try:
                c = ReminderOnGCN.get_if_accessible_by(
                    reminder_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.gcn_id)
        elif associated_resource_type.lower() == "shift":
            schema = ReminderOnShift.__schema__()
            try:
                c = ReminderOnShift.get_if_accessible_by(
                    reminder_id, self.current_user, mode="update", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.shift_id)
        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        data['id'] = reminder_id
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

        if reminder_resource_id_str != resource_id:
            return self.error(
                f'Reminder resource ID does not match resource ID given in path ({resource_id})'
            )

        self.verify_and_commit()

        if hasattr(c, 'obj'):  # reminder on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': c.obj.internal_key},
            )
        if isinstance(c, ReminderOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': c.obj.internal_key},
            )
        elif isinstance(c, ReminderOnGCN):  # also update the gcn
            self.push_all(
                action='skyportal/REFRESH_SOURCE_GCN',
                payload={'obj_internal_key': c.obj.internal_key},
            )
        elif isinstance(c, ReminderOnShift):  # also update the shift
            self.push_all(
                action='skyportal/REFRESH_SHIFT',
                payload={'obj_internal_key': c.obj.internal_key},
            )

        return self.success()

    @permissions(['Reminder'])
    def delete(self, associated_resource_type, resource_id, reminder_id):
        """
        ---
        description: Delete a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
            description: |
               What underlying data the reminder is on:
               "sources" or "spectra".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
              enum: [sources, spectra, gcn_event]
            description: |
               The ID of the source or spectrum
               that the reminder is posted to.
               This would be a string for a source ID
               or an integer for a spectrum or gcn_event.
          - in: path
            name: reminder_id
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
            reminder_id = int(reminder_id)
        except (TypeError, ValueError):
            return self.error("Must provide a valid (scalar integer) reminder ID.")

        if associated_resource_type.lower() == "sources":
            try:
                c = Reminder.get_if_accessible_by(
                    reminder_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.obj_id)
        elif associated_resource_type.lower() == "spectra":
            try:
                c = ReminderOnSpectrum.get_if_accessible_by(
                    reminder_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.spectrum_id)
        elif associated_resource_type.lower() == "gcn_event":
            try:
                c = ReminderOnGCN.get_if_accessible_by(
                    reminder_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.gcn_id)
        elif associated_resource_type.lower() == "shift":
            try:
                c = ReminderOnShift.get_if_accessible_by(
                    reminder_id, self.current_user, mode="delete", raise_if_none=True
                )
            except AccessError:
                return self.error(
                    'Could not find any accessible reminders.', status=403
                )
            reminder_resource_id_str = str(c.shift_id)

        # add more options using elif
        else:
            return self.error(
                f'Unsupported associated_resource_type "{associated_resource_type}".'
            )

        if isinstance(c, ReminderOnGCN):
            gcnevent_dateobs = c.gcn.dateobs
        elif not isinstance(c, ReminderOnShift):
            obj_key = c.obj.internal_key

        if reminder_resource_id_str != resource_id:
            return self.error(
                f'Reminder resource ID does not match resource ID given in path ({resource_id})'
            )

        DBSession().delete(c)
        self.verify_and_commit()

        if hasattr(c, 'obj'):  # reminder on object, or object related resources
            self.push_all(
                action='skyportal/REFRESH_SOURCE',
                payload={'obj_key': obj_key},
            )

        if isinstance(c, ReminderOnGCN):  # also update the GcnEvent
            self.push_all(
                action='skyportal/REFRESH_GCNEVENT',
                payload={'gcnEvent_dateobs': gcnevent_dateobs},
            )
        elif isinstance(c, ReminderOnSpectrum):  # also update the spectrum
            self.push_all(
                action='skyportal/REFRESH_SOURCE_SPECTRA',
                payload={'obj_internal_key': obj_key},
            )
        elif isinstance(c, ReminderOnShift):  # also update the shift
            self.push_all(
                action='skyportal/REFRESH_SHIFTS',
            )

        return self.success()

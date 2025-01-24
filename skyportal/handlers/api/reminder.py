import arrow
from marshmallow.exceptions import ValidationError

from baselayer.app.access import auth_or_token, permissions
from baselayer.app.custom_exceptions import AccessError
from baselayer.app.flow import Flow
from skyportal.models.source import Source

from ...models import (
    EarthquakeEvent,
    GcnEvent,
    Group,
    Reminder,
    ReminderOnEarthquake,
    ReminderOnGCN,
    ReminderOnShift,
    ReminderOnSpectrum,
    Shift,
    Spectrum,
    Token,
    User,
    UserNotification,
)
from ..base import BaseHandler


def post_reminder(
    session,
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
        What underlying data the reminder is on: source, spectrum, gcn_event or shift.
    resource_id : int
        The ID of the source or spectrum or gcn_event that the reminder is posted to.
        This would be a string for a source ID or an integer for a spectrum, shift or gcn_event.
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
    resource_name = None
    if associated_resource_type.lower() == "source":
        source = session.scalars(
            Source.select(session.user_or_token).where(Source.obj_id == resource_id)
        ).first()
        if not source:
            raise AccessError(f"Could not find source {resource_id}")
        for user in users:
            reminders.append(
                Reminder(
                    text=reminder_text,
                    obj_id=source.obj_id,
                    groups=groups,
                    bot=is_bot_reminder,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
        resource_name = source.obj_id
    elif associated_resource_type.lower() == "spectra":
        spectrum = session.scalars(
            Spectrum.select(session.user_or_token).where(Spectrum.id == resource_id)
        ).first()
        if not spectrum:
            raise ValueError(f"Could not find spectrum {resource_id}.")
        for user in users:
            reminders.append(
                ReminderOnSpectrum(
                    text=reminder_text,
                    spectrum_id=spectrum.id,
                    groups=groups,
                    bot=is_bot_reminder,
                    obj_id=spectrum.obj_id,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
        resource_name = spectrum.obj_id
    elif associated_resource_type.lower() == "gcn_event":
        gcn_event = session.scalars(
            GcnEvent.select(session.user_or_token).where(GcnEvent.id == resource_id)
        ).first()
        if not gcn_event:
            raise ValueError(f"Could not find GcnEvent {resource_id}.")
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
        resource_name = str(gcn_event.dateobs).replace(" ", "T")
    elif associated_resource_type.lower() == "earthquake":
        earthquake = session.scalars(
            EarthquakeEvent.select(session.user_or_token).where(
                EarthquakeEvent.id == resource_id
            )
        ).first()
        if not earthquake:
            raise ValueError(f"Could not find EarthquakeEvent {resource_id}.")
        for user in users:
            reminders.append(
                ReminderOnEarthquake(
                    text=reminder_text,
                    earthquake_id=earthquake.id,
                    groups=groups,
                    bot=is_bot_reminder,
                    next_reminder=next_reminder,
                    reminder_delay=reminder_delay,
                    number_of_reminders=number_of_reminders,
                    user=user,
                )
            )
        resource_name = earthquake.event_id
    elif associated_resource_type.lower() == "shift":
        shift = session.scalars(
            Shift.select(session.user_or_token).where(Shift.id == resource_id)
        ).first()
        if not shift:
            raise ValueError(f"Could not find Shift {resource_id}.")
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
        resource_name = shift.id
    else:
        raise ValueError(f'Unknown resource type "{associated_resource_type}".')

    return reminders, resource_name


class ReminderHandler(BaseHandler):
    @auth_or_token
    def get(self, associated_resource_type, resource_id, reminder_id=None):
        """
        ---
        single:
          summary: Retrieve a reminder
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
                enum: [source, spectra, gcn_event, shift, earthquake]
              description: |
                What underlying data the reminder is on:
                "sources" or "spectra" or "gcn_event" or "shift" or "earthquake"
            - in: path
              name: resource_id
              required: true
              schema:
                type: string
              description: |
                 The ID of the source, spectrum, gcn_event or shift
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
          summary: Retrieve all reminders
          description: Retrieve all reminders associated with specified resource
          tags:
            - reminders
            - spectra
            - sources
            - gcn events
            - earthquakes
          parameters:
            - in: path
              name: associated_resource_type
              required: true
              schema:
                type: string
                enum: [source, spectra, gcn_event, shift]
              description: |
                What underlying data the reminder is on:
                "sources" or "spectra" or "gcn_event" or "shift" or "earthquake".
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
        try:
            with self.Session() as session:
                if reminder_id is None:
                    if associated_resource_type.lower() == "source":
                        stmt = Reminder.select(session.user_or_token).where(
                            Reminder.obj_id == resource_id
                        )
                    elif associated_resource_type.lower() == "spectra":
                        stmt = ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.spectrum_id == resource_id
                        )
                    elif associated_resource_type.lower() == "gcn_event":
                        stmt = ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.gcn_id == resource_id
                        )
                    elif associated_resource_type.lower() == "earthquake":
                        stmt = ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.earthquake_id == resource_id
                        )
                    elif associated_resource_type.lower() == "shift":
                        stmt = ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.shift_id == resource_id
                        )
                    else:
                        return self.error(
                            f'Unsupported associated resource type "{associated_resource_type}".'
                        )
                    reminders = session.scalars(stmt).all()
                    session.commit()
                    return self.success(
                        data={
                            "resourceId": resource_id,
                            "resourceType": associated_resource_type.lower(),
                            "reminders": reminders,
                        }
                    )
                else:
                    try:
                        reminder_id = int(reminder_id)
                    except (TypeError, ValueError):
                        return self.error(
                            "Must provide a valid (scalar integer) reminder ID. "
                        )

                    # the default is to reminder on an object
                    if associated_resource_type.lower() == "source":
                        stmt = Reminder.select(session.user_or_token).where(
                            Reminder.id == reminder_id
                        )

                    elif associated_resource_type.lower() == "spectra":
                        stmt = ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.id == reminder_id
                        )
                    elif associated_resource_type.lower() == "gcn_event":
                        stmt = ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.id == reminder_id
                        )
                    elif associated_resource_type.lower() == "earthquake":
                        stmt = ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.id == reminder_id
                        )
                    elif associated_resource_type.lower() == "shift":
                        stmt = ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.id == reminder_id
                        )
                    # add more options using elif
                    else:
                        return self.error(
                            f'Unsupported associated_resource_type "{associated_resource_type}".'
                        )

                    reminder = session.scalar(stmt).first()

                    if reminder is None:
                        return self.error(f"Could not find reminder {reminder_id}.")

                    if associated_resource_type.lower() in ["source", "spectra"]:
                        reminder_resource_id_str = str(reminder.obj_id)
                    elif associated_resource_type.lower() == "gcn_event":
                        reminder_resource_id_str = str(reminder.gcn_id)
                    elif associated_resource_type.lower() == "earthquake":
                        reminder_resource_id_str = str(reminder.earthquake_id)
                    elif associated_resource_type.lower() == "shift":
                        reminder_resource_id_str = str(reminder.shift_id)

                    if reminder_resource_id_str != resource_id:
                        return self.error(
                            f"Reminder resource ID does not match resource ID given in path ({resource_id})"
                        )

                    return self.success(data=reminder)
        except Exception as e:
            return self.error(str(e))

    @permissions(["Reminder"])
    def post(self, associated_resource_type, resource_id, *ignored_args):
        """
        ---
        summary: Post a reminder
        description: Post a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [source, spectra, gcn_event, shift]
            description: |
              What underlying data the reminder is on:
              "sources" or "spectra" or "gcn_event" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
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
        next_reminder = arrow.get(next_reminder).datetime.replace(tzinfo=None)
        reminder_delay = data.get("reminder_delay", 1)
        number_of_reminders = data.get("number_of_reminders", 1)
        with self.Session() as session:
            try:
                group_ids = data.pop("group_ids", None)
                if not group_ids:
                    group_ids = [g.id for g in self.current_user.accessible_groups]
                elif not set(group_ids).issubset(
                    {g.id for g in self.current_user.accessible_groups}
                ):
                    return self.error(
                        "cannot find some of the requested groups", status=403
                    )
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()

                user_ids = data.pop("user_ids", None)
                if not user_ids:
                    user_ids = [self.associated_user_object.id]
                else:
                    accessible_users = session.scalars(
                        User.select(session.user_or_token)
                    ).all()
                    accessible_user_ids = [u.id for u in accessible_users]
                    if not set(user_ids).issubset(set(accessible_user_ids)):
                        return self.error(
                            "cannot find some of the requested users", status=403
                        )
                users = session.scalars(
                    User.select(session.user_or_token).where(User.id.in_(user_ids))
                ).all()

                is_bot_reminder = isinstance(self.current_user, Token)
                try:
                    reminders, resource_name = post_reminder(
                        session,
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
                except Exception as e:
                    return self.error(str(e))

                for reminder in reminders:
                    session.add(reminder)

                action, payload = None, None
                if associated_resource_type.lower() == "source":
                    text_to_send = f"*@{self.associated_user_object.username}* created a reminder on source *{resource_name}*"
                    url_endpoint = f"/source/{resource_name}"
                    action = "skyportal/REFRESH_REMINDER_SOURCE"
                    payload = {"id": resource_id}
                    notification_type = "reminder_source"
                elif associated_resource_type.lower() == "spectra":
                    text_to_send = f"*@{self.associated_user_object.username}* created a reminder on spectrum *{resource_name}*"
                    url_endpoint = f"/source/{resource_name}"
                    action = "skyportal/REFRESH_REMINDER_SOURCE_SPECTRA"
                    payload = {"id": resource_id}
                    notification_type = "reminder_spectra"
                elif associated_resource_type.lower() == "gcn_event":
                    text_to_send = f"*@{self.associated_user_object.username}* created a reminder on GCN event *{resource_name}*"
                    url_endpoint = f"/gcn_events/{resource_name}"
                    action = "skyportal/REFRESH_REMINDER_GCNEVENT"
                    payload = {"id": resource_id}
                    notification_type = "reminder_gcn"
                elif associated_resource_type.lower() == "shift":
                    text_to_send = f"*@{self.associated_user_object.username}* created a reminder on shift *{resource_name}*"
                    url_endpoint = f"/shifts/{resource_name}"
                    action = "skyportal/REFRESH_REMINDER_SHIFT"
                    payload = {"id": resource_id}
                    notification_type = "reminder_shift"
                elif associated_resource_type.lower() == "earthquake":
                    text_to_send = f"*@{self.associated_user_object.username}* created a reminder on earthquake *{resource_name}*"
                    url_endpoint = f"/earthquakes/{resource_name}"
                    action = "skyportal/REFRESH_REMINDER_EARTHQUAKE"
                    payload = {"id": resource_id}
                    notification_type = "reminder_earthquake"
                else:
                    return self.error(
                        f'Unknown resource type "{associated_resource_type}".'
                    )

                ws_flow = Flow()
                for user in users:
                    session.add(
                        UserNotification(
                            user=user,
                            text=text_to_send,
                            notification_type=notification_type,
                            url=url_endpoint,
                        )
                    )
                    ws_flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS")

                session.commit()
                self.push_all(action, payload)
                return self.success(
                    data={"reminder_ids": [reminder.id for reminder in reminders]}
                )
            except Exception as e:
                session.rollback()
                return self.error(str(e))

    @permissions(["Reminder"])
    def patch(self, associated_resource_type, resource_id, reminder_id):
        """
        ---
        summary: Update a reminder
        description: Update a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [source, spectra, gcn_event, shift]
            description: |
              What underlying data the reminder is on:
              "sources" or "spectra" or "gcn_event" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
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

        data = self.get_json()
        group_ids = data.pop("group_ids", None)
        with self.Session() as session:
            try:
                group_ids = data.pop("group_ids", None)
                if not group_ids:
                    group_ids = [g.id for g in self.current_user.accessible_groups]
                elif not set(group_ids).issubset(
                    {g.id for g in self.current_user.accessible_groups}
                ):
                    return self.error(
                        "cannot find some of the requested groups", status=403
                    )
                groups = session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                ).all()
                data["groups"] = groups

                user_ids = data.pop("user_ids", None)
                if not user_ids:
                    user_ids = [self.associated_user_object.id]
                else:
                    accessible_users = session.scalars(
                        User.select(session.user_or_token)
                    ).all()
                    accessible_user_ids = [u.id for u in accessible_users]
                    if not set(user_ids).issubset(set(accessible_user_ids)):
                        return self.error(
                            "cannot find some of the requested users", status=403
                        )
                users = session.scalars(
                    User.select(session.user_or_token).where(User.id.in_(user_ids))
                ).all()
                data["users"] = users
                data["id"] = reminder_id

                if associated_resource_type.lower() == "source":
                    source = session.scalars(
                        Source.select(session.user_or_token).where(
                            Source.obj_id == resource_id
                        )
                    )
                    if not source:
                        raise AccessError(f"Could not find source {resource_id}")
                    schema = Reminder.__schema__()
                    reminder = session.scalars(
                        Reminder.select(session.user_or_token).where(
                            Reminder.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "spectra":
                    spectrum = session.scalars(
                        Spectrum.select(session.user_or_token).where(
                            Spectrum.obj_id == resource_id
                        )
                    )
                    if not spectrum:
                        raise AccessError(f"Could not find spectrum {resource_id}")
                    schema = ReminderOnSpectrum.__schema__()
                    reminder = session.scalars(
                        ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "gcn_event":
                    gcn_event = session.scalars(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.id == resource_id
                        )
                    )
                    if not gcn_event:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    schema = ReminderOnGCN.__schema__()
                    reminder = session.scalars(
                        ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.id == reminder_id
                        )
                    ).first()
                elif associated_resource_type.lower() == "earthquake":
                    earthquake = session.scalars(
                        EarthquakeEvent.select(session.user_or_token).where(
                            EarthquakeEvent.id == resource_id
                        )
                    )
                    if not earthquake:
                        raise AccessError(f"Could not find earthquake {resource_id}")
                    schema = ReminderOnEarthquake.__schema__()
                    reminder = session.scalars(
                        ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.id == reminder_id
                        )
                    ).first()
                elif associated_resource_type.lower() == "shift":
                    shift = session.scalars(
                        Shift.select(session.user_or_token).where(
                            Shift.id == resource_id
                        )
                    )
                    if not shift:
                        raise AccessError(f"Could not find shift {resource_id}")
                    schema = ReminderOnShift.__schema__()
                    reminder = session.scalars(
                        ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.id == reminder_id
                        )
                    ).first()
                # add more options using elif
                else:
                    return self.error(
                        f'Unsupported associated_resource_type "{associated_resource_type}".'
                    )

                if not reminder:
                    return self.error(f"Could not find reminder {reminder_id}")

                if associated_resource_type.lower() in ["source", "spectra"]:
                    reminder_resource_id_str = str(reminder.obj_id)
                elif associated_resource_type.lower() == "gcn_event":
                    reminder_resource_id_str = str(reminder.gcn_id)
                elif associated_resource_type.lower() == "shift":
                    reminder_resource_id_str = str(reminder.shift_id)
                elif associated_resource_type.lower() == "earthquake":
                    reminder_resource_id_str = str(reminder.earthquake_id)

                if reminder_resource_id_str != resource_id:
                    return self.error(
                        f"Reminder resource ID does not match resource ID given in path ({resource_id})"
                    )

                try:
                    schema.load(data, partial=True)
                except ValidationError as e:
                    return self.error(
                        f"Invalid/missing parameters: {e.normalized_messages()}"
                    )

                session.commit()

                if isinstance(reminder, Reminder):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SOURCE",
                        payload={"id": reminder.obj_id},
                    )
                elif isinstance(reminder, ReminderOnSpectrum):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SOURCE_SPECTRA",
                        payload={"id": reminder.obj_id},
                    )
                elif isinstance(reminder, ReminderOnGCN):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_GCNEVENT",
                        payload={"id": reminder.gcn_id},
                    )
                elif isinstance(reminder, ReminderOnEarthquake):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_EARTHQUAKE",
                        payload={"id": reminder.earthquake_id},
                    )
                elif isinstance(reminder, ReminderOnShift):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SHIFT",
                        payload={"id": reminder.shift_id},
                    )

                return self.success()
            except Exception as e:
                return self.error(str(e))

    @permissions(["Reminder"])
    def delete(self, associated_resource_type, resource_id, reminder_id):
        """
        ---
        summary: Delete a reminder
        description: Delete a reminder
        tags:
          - reminders
        parameters:
          - in: path
            name: associated_resource_type
            required: true
            schema:
              type: string
              enum: [source, spectra, gcn_event, shift]
            description: |
              What underlying data the reminder is on:
              "sources" or "spectra" or "gcn_event" or "shift".
          - in: path
            name: resource_id
            required: true
            schema:
              type: string
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
        with self.Session() as session:
            try:
                if associated_resource_type.lower() == "source":
                    source = session.scalars(
                        Source.select(session.user_or_token).where(
                            Source.obj_id == resource_id
                        )
                    )
                    if not source:
                        raise AccessError(f"Could not find source {resource_id}")
                    reminder = session.scalars(
                        Reminder.select(session.user_or_token).where(
                            Reminder.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "spectra":
                    spectrum = session.scalars(
                        Spectrum.select(session.user_or_token).where(
                            Spectrum.obj_id == resource_id
                        )
                    )
                    if not spectrum:
                        raise AccessError(f"Could not find spectrum {resource_id}")
                    reminder = session.scalars(
                        ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "gcn_event":
                    gcn_event = session.scalars(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.id == resource_id
                        )
                    )
                    if not gcn_event:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    reminder = session.scalars(
                        ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "earthquake":
                    earthquake = session.scalars(
                        EarthquakeEvent.select(session.user_or_token).where(
                            EarthquakeEvent.id == resource_id
                        )
                    )
                    if not earthquake:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    reminder = session.scalars(
                        ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.id == reminder_id
                        )
                    ).first()

                elif associated_resource_type.lower() == "shift":
                    shift = session.scalars(
                        Shift.select(session.user_or_token).where(
                            Shift.id == resource_id
                        )
                    )
                    if not shift:
                        raise AccessError(f"Could not find shift {resource_id}")
                    reminder = session.scalars(
                        ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.id == reminder_id
                        )
                    ).first()
                # add more options using elif
                else:
                    return self.error(
                        f'Unsupported associated_resource_type "{associated_resource_type}".'
                    )

                if not reminder:
                    return self.error(f"Could not find reminder {reminder_id}")

                if associated_resource_type.lower() in ["source", "spectra"]:
                    reminder_resource_id_str = str(reminder.obj_id)
                elif associated_resource_type.lower() == "gcn_event":
                    reminder_resource_id_str = str(reminder.gcn_id)
                elif associated_resource_type.lower() == "shift":
                    reminder_resource_id_str = str(reminder.shift_id)
                elif associated_resource_type.lower() == "earthquake":
                    reminder_resource_id_str = str(reminder.earthquake_id)

                if reminder_resource_id_str != resource_id:
                    return self.error(
                        f"Reminder resource ID does not match resource ID given in path ({resource_id})"
                    )

                session.delete(reminder)
                session.commit()

                if isinstance(reminder, Reminder):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SOURCE",
                        payload={"id": reminder.obj_id},
                    )
                elif isinstance(reminder, ReminderOnSpectrum):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SOURCE_SPECTRA",
                        payload={"id": reminder.obj_id},
                    )
                elif isinstance(reminder, ReminderOnGCN):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_GCNEVENT",
                        payload={"id": reminder.gcn_id},
                    )
                elif isinstance(reminder, ReminderOnShift):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_SHIFT",
                        payload={"id": reminder.shift_id},
                    )
                elif isinstance(reminder, ReminderOnEarthquake):
                    self.push_all(
                        action="skyportal/REFRESH_REMINDER_EARTHQUAKE",
                        payload={"id": reminder.earthquake_id},
                    )

                return self.success()
            except Exception as e:
                return self.error(str(e))

import arrow
from pydantic import BaseModel, ConfigDict, Field

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


class ReminderPostBody(BaseModel):
    """Request body for creating reminder(s)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="Text to post for the reminder")
    next_reminder: str = Field(
        description="Arrow-parseable date string for the next reminder"
    )
    reminder_delay: float = Field(
        default=1, description="Delay until the next reminder in days"
    )
    number_of_reminders: int = Field(
        default=1, description="Number of remaining reminders"
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view reminder. Defaults to all of requesting user's groups.",
    )
    user_ids: list[int] | None = Field(
        default=None,
        description="List of IDs of users to post the reminder for. Defaults to "
        "the requesting user.",
    )


class ReminderPostResponse(BaseModel):
    """IDs of the newly created reminders."""

    reminder_ids: list[int] = Field(
        description="IDs of the new reminders (one per user)"
    )


class ReminderPatchBody(BaseModel):
    """Request body for updating a reminder."""

    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(default=None, description="Text to post for the reminder")
    next_reminder: str | None = Field(
        default=None, description="Arrow-parseable date string for the next reminder"
    )
    reminder_delay: float | None = Field(
        default=None, description="Delay until the next reminder in days"
    )
    number_of_reminders: int | None = Field(
        default=None, description="Number of remaining reminders"
    )
    group_ids: list[int] | None = Field(
        default=None,
        description="List of group IDs corresponding to which groups should be "
        "able to view reminder. Defaults to all of requesting user's groups.",
    )
    user_ids: list[int] | None = Field(
        default=None,
        description="List of IDs of users the reminder is for. Defaults to "
        "the requesting user.",
    )


def _coerce_resource_id(associated_resource_type, resource_id):
    """For non-source resources the underlying FK column is integer;
    psycopg3 binds Python strings as VARCHAR and Postgres refuses the
    implicit comparison. Returns (coerced_value, error_message) — if the
    coercion fails, the caller should `return self.error(error_message)`.
    """
    if associated_resource_type.lower() == "source":
        return resource_id, None
    try:
        return int(resource_id), None
    except (TypeError, ValueError):
        return (
            None,
            f"Invalid resource_id {resource_id!r} for {associated_resource_type}",
        )


async def post_reminder(
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
        source = await session.scalar(
            Source.select(session.user_or_token).where(Source.obj_id == resource_id)
        )
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
        spectrum = await session.scalar(
            Spectrum.select(session.user_or_token).where(Spectrum.id == resource_id)
        )
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
        gcn_event = await session.scalar(
            GcnEvent.select(session.user_or_token).where(GcnEvent.id == resource_id)
        )
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
        earthquake = await session.scalar(
            EarthquakeEvent.select(session.user_or_token).where(
                EarthquakeEvent.id == resource_id
            )
        )
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
        shift = await session.scalar(
            Shift.select(session.user_or_token).where(Shift.id == resource_id)
        )
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
    async def get(
        self,
        associated_resource_type: str,
        resource_id: str,
        reminder_id: int | None = None,
    ):
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
        coerced_resource_id, err = _coerce_resource_id(
            associated_resource_type, resource_id
        )
        if err is not None:
            return self.error(err)
        try:
            async with self.AsyncSession() as session:
                if reminder_id is None:
                    if associated_resource_type.lower() == "source":
                        stmt = Reminder.select(session.user_or_token).where(
                            Reminder.obj_id == coerced_resource_id
                        )
                    elif associated_resource_type.lower() == "spectra":
                        stmt = ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.spectrum_id == coerced_resource_id
                        )
                    elif associated_resource_type.lower() == "gcn_event":
                        stmt = ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.gcn_id == coerced_resource_id
                        )
                    elif associated_resource_type.lower() == "earthquake":
                        stmt = ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.earthquake_id == coerced_resource_id
                        )
                    elif associated_resource_type.lower() == "shift":
                        stmt = ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.shift_id == coerced_resource_id
                        )
                    else:
                        return self.error(
                            f'Unsupported associated resource type "{associated_resource_type}".'
                        )
                    list_result = await session.scalars(stmt)
                    reminders = list_result.all()
                    await session.commit()
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

                    reminder = await session.scalar(stmt)

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
    async def post(
        self,
        associated_resource_type: str,
        resource_id: str,
        *ignored_args,
        body: ReminderPostBody = None,
    ) -> ReminderPostResponse:
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
        """
        coerced_resource_id, err = _coerce_resource_id(
            associated_resource_type, resource_id
        )
        if err is not None:
            return self.error(err)

        body = self.parse_body(ReminderPostBody)

        reminder_text = body.text
        next_reminder = arrow.get(body.next_reminder).datetime.replace(tzinfo=None)
        reminder_delay = body.reminder_delay
        number_of_reminders = body.number_of_reminders
        async with self.AsyncSession() as session:
            try:
                group_ids = body.group_ids
                if not group_ids:
                    group_ids = [g.id for g in self.current_user.accessible_groups]
                elif not set(group_ids).issubset(
                    {g.id for g in self.current_user.accessible_groups}
                ):
                    return self.error(
                        "cannot find some of the requested groups", status=403
                    )
                groups_result = await session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                )
                groups = groups_result.all()

                user_ids = body.user_ids
                if not user_ids:
                    user_ids = [self.associated_user_object.id]
                else:
                    accessible_result = await session.scalars(
                        User.select(session.user_or_token)
                    )
                    accessible_user_ids = [u.id for u in accessible_result.all()]
                    if not set(user_ids).issubset(set(accessible_user_ids)):
                        return self.error(
                            "cannot find some of the requested users", status=403
                        )
                users_result = await session.scalars(
                    User.select(session.user_or_token).where(User.id.in_(user_ids))
                )
                users = users_result.all()

                is_bot_reminder = isinstance(self.current_user, Token)
                try:
                    reminders, resource_name = await post_reminder(
                        session,
                        associated_resource_type,
                        coerced_resource_id,
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

                await session.commit()
                self.push_all(action, payload)
                return self.success(
                    data={"reminder_ids": [reminder.id for reminder in reminders]}
                )
            except Exception as e:
                await session.rollback()
                return self.error(str(e))

    @permissions(["Reminder"])
    async def patch(
        self,
        associated_resource_type: str,
        resource_id: str,
        reminder_id: int,
        *,
        body: ReminderPatchBody = None,
    ):
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

        coerced_resource_id, err = _coerce_resource_id(
            associated_resource_type, resource_id
        )
        if err is not None:
            return self.error(err)

        body = self.parse_body(ReminderPatchBody)
        async with self.AsyncSession() as session:
            try:
                group_ids = body.group_ids
                if not group_ids:
                    group_ids = [g.id for g in self.current_user.accessible_groups]
                elif not set(group_ids).issubset(
                    {g.id for g in self.current_user.accessible_groups}
                ):
                    return self.error(
                        "cannot find some of the requested groups", status=403
                    )
                groups_result = await session.scalars(
                    Group.select(session.user_or_token).where(Group.id.in_(group_ids))
                )
                groups = groups_result.all()

                user_ids = body.user_ids
                if not user_ids:
                    user_ids = [self.associated_user_object.id]
                else:
                    accessible_result = await session.scalars(
                        User.select(session.user_or_token)
                    )
                    accessible_user_ids = [u.id for u in accessible_result.all()]
                    if not set(user_ids).issubset(set(accessible_user_ids)):
                        return self.error(
                            "cannot find some of the requested users", status=403
                        )

                if associated_resource_type.lower() == "source":
                    source = await session.scalar(
                        Source.select(session.user_or_token).where(
                            Source.obj_id == coerced_resource_id
                        )
                    )
                    if not source:
                        raise AccessError(f"Could not find source {resource_id}")
                    reminder = await session.scalar(
                        Reminder.select(session.user_or_token).where(
                            Reminder.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "spectra":
                    spectrum = await session.scalar(
                        Spectrum.select(session.user_or_token).where(
                            Spectrum.obj_id == coerced_resource_id
                        )
                    )
                    if not spectrum:
                        raise AccessError(f"Could not find spectrum {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "gcn_event":
                    gcn_event = await session.scalar(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.id == coerced_resource_id
                        )
                    )
                    if not gcn_event:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.id == reminder_id
                        )
                    )
                elif associated_resource_type.lower() == "earthquake":
                    earthquake = await session.scalar(
                        EarthquakeEvent.select(session.user_or_token).where(
                            EarthquakeEvent.id == coerced_resource_id
                        )
                    )
                    if not earthquake:
                        raise AccessError(f"Could not find earthquake {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.id == reminder_id
                        )
                    )
                elif associated_resource_type.lower() == "shift":
                    shift = await session.scalar(
                        Shift.select(session.user_or_token).where(
                            Shift.id == coerced_resource_id
                        )
                    )
                    if not shift:
                        raise AccessError(f"Could not find shift {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.id == reminder_id
                        )
                    )
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

                if body.text is not None:
                    reminder.text = body.text
                if body.next_reminder is not None:
                    reminder.next_reminder = arrow.get(
                        body.next_reminder
                    ).datetime.replace(tzinfo=None)
                if body.reminder_delay is not None:
                    reminder.reminder_delay = body.reminder_delay
                if body.number_of_reminders is not None:
                    reminder.number_of_reminders = body.number_of_reminders
                # like the old marshmallow merge, groups are always replaced,
                # defaulting to the requesting user's accessible groups
                reminder.groups = groups

                await session.commit()

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
    async def delete(
        self, associated_resource_type: str, resource_id: str, reminder_id: int
    ):
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
        coerced_resource_id, err = _coerce_resource_id(
            associated_resource_type, resource_id
        )
        if err is not None:
            return self.error(err)
        async with self.AsyncSession() as session:
            try:
                if associated_resource_type.lower() == "source":
                    source = await session.scalar(
                        Source.select(session.user_or_token).where(
                            Source.obj_id == coerced_resource_id
                        )
                    )
                    if not source:
                        raise AccessError(f"Could not find source {resource_id}")
                    reminder = await session.scalar(
                        Reminder.select(session.user_or_token).where(
                            Reminder.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "spectra":
                    spectrum = await session.scalar(
                        Spectrum.select(session.user_or_token).where(
                            Spectrum.obj_id == coerced_resource_id
                        )
                    )
                    if not spectrum:
                        raise AccessError(f"Could not find spectrum {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnSpectrum.select(session.user_or_token).where(
                            ReminderOnSpectrum.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "gcn_event":
                    gcn_event = await session.scalar(
                        GcnEvent.select(session.user_or_token).where(
                            GcnEvent.id == coerced_resource_id
                        )
                    )
                    if not gcn_event:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnGCN.select(session.user_or_token).where(
                            ReminderOnGCN.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "earthquake":
                    earthquake = await session.scalar(
                        EarthquakeEvent.select(session.user_or_token).where(
                            EarthquakeEvent.id == coerced_resource_id
                        )
                    )
                    if not earthquake:
                        raise AccessError(f"Could not find gcn event {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnEarthquake.select(session.user_or_token).where(
                            ReminderOnEarthquake.id == reminder_id
                        )
                    )

                elif associated_resource_type.lower() == "shift":
                    shift = await session.scalar(
                        Shift.select(session.user_or_token).where(
                            Shift.id == coerced_resource_id
                        )
                    )
                    if not shift:
                        raise AccessError(f"Could not find shift {resource_id}")
                    reminder = await session.scalar(
                        ReminderOnShift.select(session.user_or_token).where(
                            ReminderOnShift.id == reminder_id
                        )
                    )
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

                await session.delete(reminder)
                await session.commit()

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

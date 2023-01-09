__all__ = ['UserNotification']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import func

from sqlalchemy import event, inspect
import arrow
import datetime
import lxml
import operator  # noqa: F401
import requests

from baselayer.app.models import Base, User, AccessibleIfUserMatches
from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.log import make_log

from ..app_utils import get_app_base_url
from .allocation import Allocation
from .analysis import ObjAnalysis
from .classification import Classification
from .gcn import GcnNotice
from .localization import Localization
from .spectrum import Spectrum
from .comment import Comment
from .listing import Listing
from .facility_transaction import FacilityTransaction
from .followup_request import FollowupRequest
from .observation_plan import ObservationPlanRequest, EventObservationPlan
from .group import GroupAdmissionRequest, GroupUser, Group
from ..email_utils import send_email
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Say, VoiceResponse
import gcn
from sqlalchemy import or_

from skyportal.models import Shift, ShiftUser
from skyportal.utils.gcn import get_tags, get_properties

from skyportal.utils.notifications import (
    gcn_slack_notification,
    gcn_email_notification,
    source_slack_notification,
    source_email_notification,
)

_, cfg = load_env()

log = make_log('notifications')

account_sid = cfg["twilio.sms_account_sid"]
auth_token = cfg["twilio.sms_auth_token"]
from_number = cfg["twilio.from_number"]
client = None
if account_sid and auth_token and from_number:
    client = TwilioClient(account_sid, auth_token)

email = False
if cfg["email_service"] == "sendgrid" or cfg["email_service"] == "smtp":
    email = True


class UserNotification(Base):

    read = update = delete = AccessibleIfUserMatches('user')

    user_id = sa.Column(
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the associated User",
    )
    user = relationship(
        "User",
        back_populates="notifications",
        doc="The associated User",
    )
    text = sa.Column(
        sa.String(),
        nullable=False,
        doc="The notification text to display",
    )

    notification_type = sa.Column(
        sa.String(), nullable=True, doc="Type of notification"
    )

    viewed = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Boolean indicating whether notification has been viewed.",
    )

    url = sa.Column(
        sa.String(),
        nullable=True,
        doc="URL to which to direct upon click, if relevant",
    )


def notification_resource_type(target):
    if not target.notification_type:
        return None
    if "favorite_sources" not in target.notification_type:
        return target.notification_type
    elif "favorite_sources" in target.notification_type:
        return "favorite_sources"


def user_preferences(target, notification_setting, resource_type):

    if not isinstance(notification_setting, str):
        return
    if not isinstance(resource_type, str):
        return
    if not target.user:
        return

    if notification_setting == "email":
        if not email:
            return
        if not target.user.contact_email:
            return
        # this ensures that an email is sent regardless of the user's preferences
        # this is useful for group_admission_requests, where we want the admins to always be notified by email
        if resource_type in ['group_admission_request']:
            return True

    if not target.user.preferences:
        return

    if notification_setting in ["sms", "phone"]:
        if client is None:
            return
        if not target.user.contact_phone:
            return

    if notification_setting == "slack":
        if not target.user.preferences.get('slack_integration'):
            return
        if not target.user.preferences['slack_integration'].get("active"):
            return
        if (
            not target.user.preferences['slack_integration']
            .get("url", "")
            .startswith(cfg["slack.expected_url_preamble"])
        ):
            return

    prefs = target.user.preferences.get('notifications')
    if not prefs:
        return
    else:
        if resource_type in [
            'sources',
            'favorite_sources',
            'gcn_events',
            'facility_transactions',
            'mention',
            'analysis_services',
            'observation_plans',
        ]:
            if not prefs.get(resource_type, False):
                return
            if not prefs[resource_type].get(notification_setting, False):
                return
            if not prefs[resource_type][notification_setting].get("active", False):
                return

        return prefs


@event.listens_for(UserNotification, 'after_insert')
def send_slack_notification(mapper, connection, target):
    resource_type = notification_resource_type(target)
    notifications_prefs = user_preferences(target, "slack", resource_type)
    if not notifications_prefs:
        return
    integration_url = target.user.preferences['slack_integration'].get('url')

    slack_microservice_url = f'http://127.0.0.1:{cfg["slack.microservice_port"]}'

    app_url = get_app_base_url()

    try:
        if resource_type == 'gcn_events':
            data = json.dumps(
                {
                    "url": integration_url,
                    "blocks": gcn_slack_notification(
                        session=inspect(target).session, target=target, app_url=app_url
                    ),
                }
            )
        elif resource_type == 'sources':
            data = json.dumps(
                {
                    "url": integration_url,
                    "blocks": source_slack_notification(
                        session=inspect(target).session, target=target, app_url=app_url
                    ),
                }
            )
        else:
            data = json.dumps(
                {
                    "url": integration_url,
                    "text": f'{target.text} ({app_url}{target.url})',
                }
            )

        requests.post(
            slack_microservice_url,
            data=data,
            headers={'Content-Type': 'application/json'},
        )
        log(
            f"Sent slack notification to user {target.user.id} at slack_url: {integration_url}, body: {target.text}, resource_type: {resource_type}"
        )
    except Exception as e:
        log(f"Error sending slack notification: {e}")


@event.listens_for(UserNotification, 'after_insert')
def send_email_notification(mapper, connection, target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "email", resource_type)

    if not prefs:
        return

    subject = None
    body = None

    app_url = get_app_base_url()

    try:

        if resource_type == "sources":
            subject, body = source_email_notification(
                session=inspect(target).session, target=target, app_url=app_url
            )

        elif resource_type == "gcn_events":
            subject, body = gcn_email_notification(
                session=inspect(target).session, target=target, app_url=app_url
            )

        elif resource_type == "facility_transactions":
            subject = f"{cfg['app.title']} - New facility transaction"

        elif resource_type == "observation_plans":
            subject = f"{cfg['app.title']} - New observation plans"

        elif resource_type == "analysis_services":
            subject = f"{cfg['app.title']} - New completed analysis service"

        elif resource_type == "favorite_sources":
            if target.notification_type == "favorite_sources_new_classification":
                subject = (
                    f"{cfg['app.title']} - New classification on a favorite source"
                )

            elif target.notification_type == "favorite_sources_new_spectrum":
                subject = f"{cfg['app.title']} - New spectrum on a favorite source"

            elif target.notification_type == "favorite_sources_new_comment":
                subject = f"{cfg['app.title']} - New comment on a favorite source"

        elif resource_type == "mention":
            subject = f"{cfg['app.title']} - User mentioned you in a comment"

        elif resource_type == "group_admission_request":
            subject = f"{cfg['app.title']} - New group admission request"

        if subject and target.user.contact_email:
            try:
                if body is None:
                    body = f'{target.text} ({app_url}{target.url})'
                send_email(
                    recipients=[target.user.contact_email],
                    subject=subject,
                    body=body,
                )
                log(
                    f"Sent email notification to user {target.user.id} at email: {target.user.contact_email}, subject: {subject}, body: {body}, resource_type: {resource_type}"
                )
            except Exception as e:
                log(f"Error sending email notification: {e}")

    except Exception as e:
        log(f"Error sending email notification: {e}")


@event.listens_for(UserNotification, 'after_insert')
def send_sms_notification(mapper, connection, target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "sms", resource_type)
    if not prefs:
        return

    sending = False
    if prefs[resource_type]['sms'].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target.user.id)
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]['sms'].get("time_slot", [])
    if len(timeslot) > 0:
        current_time = arrow.utcnow().datetime
        if timeslot[0] < timeslot[1]:
            if current_time.hour >= timeslot[0] and current_time.hour <= timeslot[1]:
                sending = True
        else:
            if current_time.hour <= timeslot[1] or current_time.hour >= timeslot[0]:
                sending = True

    if sending:
        try:
            client.messages.create(
                body=f"{cfg['app.title']} - {target.text}",
                from_=from_number,
                to=target.user.contact_phone.e164,
            )
            log(
                f"Sent SMS notification to user {target.user.id} at phone number: {target.user.contact_phone.e164}, body: {target.text}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending sms notification: {e}")


@event.listens_for(UserNotification, 'after_insert')
def send_phone_notification(mapper, connection, target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "phone", resource_type)

    if not prefs:
        return

    sending = False
    if prefs[resource_type]['phone'].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target.user.id)
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]['phone'].get("time_slot", [])
    if len(timeslot) > 0:
        current_time = arrow.utcnow().datetime
        if timeslot[0] < timeslot[1]:
            if current_time.hour >= timeslot[0] and current_time.hour <= timeslot[1]:
                sending = True
        else:
            if current_time.hour <= timeslot[1] or current_time.hour >= timeslot[0]:
                sending = True

    if sending:
        try:
            message = f"Greetings. This is the SkyPortal robot. {target.text}"
            client.calls.create(
                twiml=VoiceResponse().append(Say(message=message)),
                from_=from_number,
                to=target.user.contact_phone.e164,
            )
            log(
                f"Sent Phone Call notification to user {target.user.id} at phone number: {target.user.contact_phone.e164}, message: {message}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending phone call notification: {e}")


@event.listens_for(UserNotification, 'after_insert')
def send_whatsapp_notification(mapper, connection, target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "whatsapp", resource_type)
    if not prefs:
        return

    sending = False
    if prefs[resource_type]['whatsapp'].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target.user.id)
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]['whatsapp'].get("time_slot", [])
    if len(timeslot) > 0:
        current_time = arrow.utcnow().datetime
        if timeslot[0] < timeslot[1]:
            if current_time.hour >= timeslot[0] and current_time.hour <= timeslot[1]:
                sending = True
        else:
            if current_time.hour <= timeslot[1] or current_time.hour >= timeslot[0]:
                sending = True

    if sending:
        try:
            client.messages.create(
                body=f"{cfg['app.title']} - {target.text}",
                from_="whatsapp:" + str(from_number),
                to="whatsapp" + str(target.user.contact_phone.e164),
            )
            log(
                f"Sent WhatsApp notification to user {target.user.id} at phone number: {target.user.contact_phone.e164}, body: {target.text}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending WhatsApp notification: {e}")


@event.listens_for(UserNotification, 'after_insert')
def push_frontend_notification(mapper, connection, target):
    if 'user_id' in target.__dict__:
        user_id = target.user_id
    elif 'user' in target.__dict__:
        if 'id' in target.user.__dict__:
            user_id = target.user.id
        else:
            user_id = None
    else:
        user_id = None

    if user_id is None:
        log(
            "Error sending frontend notification: user_id or user.id not found in notification's target"
        )
        return
    resource_type = notification_resource_type(target)
    log(
        f"Sent frontend notification to user {user_id}, body: {target.text}, resource_type: {resource_type}"
    )
    ws_flow = Flow()
    ws_flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS")


@event.listens_for(Classification, 'after_insert')
@event.listens_for(Spectrum, 'after_insert')
@event.listens_for(Comment, 'after_insert')
@event.listens_for(GcnNotice, 'after_insert')
@event.listens_for(FacilityTransaction, 'after_insert')
@event.listens_for(GroupAdmissionRequest, 'after_insert')
@event.listens_for(ObjAnalysis, 'after_update')
@event.listens_for(EventObservationPlan, 'after_insert')
@event.listens_for(FollowupRequest, 'after_update')
def add_user_notifications(mapper, connection, target):

    # Add front-end user notifications
    @event.listens_for(inspect(target).session, "after_flush", once=True)
    def receive_after_flush(session, context):

        is_facility_transaction = target.__class__.__name__ == "FacilityTransaction"
        is_gcnevent = target.__class__.__name__ == "GcnNotice"
        is_classification = target.__class__.__name__ == "Classification"
        is_spectra = target.__class__.__name__ == "Spectrum"
        is_comment = target.__class__.__name__ == "Comment"
        is_group_admission_request = (
            target.__class__.__name__ == "GroupAdmissionRequest"
        )
        is_analysis_service = target.__class__.__name__ == "ObjAnalysis"
        is_observation_plan = target.__class__.__name__ == "EventObservationPlan"
        is_followup_request = target.__class__.__name__ == "FollowupRequest"

        if is_gcnevent:
            users = session.scalars(
                sa.select(User).where(
                    User.preferences["notifications"]["gcn_events"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                )
            ).all()
        elif is_facility_transaction or is_followup_request:
            users = session.scalars(
                sa.select(User).where(
                    User.preferences["notifications"]["facility_transactions"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                )
            ).all()
        elif is_analysis_service:
            users = session.scalars(
                sa.select(User).where(
                    User.preferences["notifications"]["analysis_services"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                )
            ).all()
        elif is_observation_plan:
            users = session.scalars(
                sa.select(User).where(
                    User.preferences["notifications"]["facility_transactions"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                )
            ).all()
        elif is_group_admission_request:
            users = []
            group_admins_gu = session.scalars(
                sa.select(GroupUser).where(
                    GroupUser.group_id == target.group_id,
                    GroupUser.admin.is_(True),
                )
            ).all()
            for gu in group_admins_gu:
                group_admin = session.scalars(
                    sa.select(User).where(User.id == gu.user_id)
                ).first()

                if group_admin is not None:
                    users.append(group_admin)

        else:

            if is_classification:
                users = session.scalars(
                    sa.select(User).where(
                        or_(
                            User.preferences["notifications"]["sources"]["active"]
                            .astext.cast(sa.Boolean)
                            .is_(True),
                            User.preferences["notifications"]["favorite_sources"][
                                "active"
                            ]
                            .astext.cast(sa.Boolean)
                            .is_(True),
                        )
                    )
                ).all()
            elif is_spectra:
                users = session.scalars(
                    sa.select(User).where(
                        User.preferences["notifications"]["favorite_sources"]["active"]
                        .astext.cast(sa.Boolean)
                        .is_(True)
                    )
                ).all()
            elif is_comment:
                users = session.scalars(
                    sa.select(User).where(
                        User.preferences["notifications"]["favorite_sources"]["active"]
                        .astext.cast(sa.Boolean)
                        .is_(True)
                    )
                ).all()
            else:
                users = []

        for user in users:
            # Only notify users who have read access to the new record in question
            if user.preferences is not None:
                pref = user.preferences.get('notifications', None)
            else:
                pref = None

            if (
                session.scalars(
                    target.__class__.select(user, mode='read').where(
                        target.__class__.id == target.id
                    )
                ).first()
                is not None
            ):
                if is_gcnevent:
                    if (pref is not None) and "gcn_notice_types" in pref[
                        "gcn_events"
                    ].keys():
                        if (
                            gcn.NoticeType(target.notice_type).name
                            in pref['gcn_events']['gcn_notice_types']
                        ):
                            send_notification = True
                            if "gcn_tags" in pref["gcn_events"].keys():
                                if len(pref['gcn_events']["gcn_tags"]) > 0:
                                    root = lxml.etree.fromstring(target.content)
                                    tags = [text for text in get_tags(root)]
                                    intersection = list(
                                        set(tags) & set(pref['gcn_events']["gcn_tags"])
                                    )
                                    if len(intersection) == 0:
                                        send_notification = False
                                        break

                            if "gcn_properties" in pref["gcn_events"].keys():
                                if len(pref['gcn_events']["gcn_properties"]) > 0:
                                    root = lxml.etree.fromstring(target.content)
                                    properties_dict = get_properties(root)

                                    for prop_filt in pref['gcn_events'][
                                        "gcn_properties"
                                    ]:
                                        prop_split = prop_filt.split(":")
                                        if not len(prop_split) == 3:
                                            raise ValueError(
                                                "Invalid propertiesFilter value -- property filter must have 3 values"
                                            )
                                        name = prop_split[0].strip()
                                        if name in properties_dict:
                                            value = prop_split[1].strip()
                                            try:
                                                value = float(value)
                                            except ValueError as e:
                                                raise ValueError(
                                                    f"Invalid propotation filter value: {e}"
                                                )
                                            op = prop_split[2].strip()
                                            op_options = [
                                                "lt",
                                                "le",
                                                "eq",
                                                "ne",
                                                "ge",
                                                "gt",
                                            ]
                                            if op not in op_options:
                                                raise ValueError(
                                                    f"Invalid operator: {op}"
                                                )
                                            comp_function = getattr(operator, op)
                                            if not comp_function(
                                                properties_dict[name], value
                                            ):
                                                send_notification = False
                                                break
                            if send_notification:
                                stmt = sa.select(GcnNotice).where(
                                    GcnNotice.dateobs == target.dateobs
                                )
                                count_stmt = sa.select(func.count()).select_from(stmt)
                                count_notices = session.execute(count_stmt).scalar()
                                if count_notices > 1:
                                    session.add(
                                        UserNotification(
                                            user=user,
                                            text=f"New Notice for GCN Event *{target.dateobs}*, with Notice Type *{gcn.NoticeType(target.notice_type).name}*",
                                            notification_type="gcn_events",
                                            url=f"/gcn_events/{str(target.dateobs).replace(' ','T')}",
                                        )
                                    )
                                else:
                                    session.add(
                                        UserNotification(
                                            user=user,
                                            text=f"New GCN Event *{target.dateobs}*, with Notice Type *{gcn.NoticeType(target.notice_type).name}*",
                                            notification_type="gcn_events",
                                            url=f"/gcn_events/{str(target.dateobs).replace(' ','T')}",
                                        )
                                    )

                elif is_facility_transaction:
                    if "observation_plan_request" in target.to_dict():
                        allocation_id = target.observation_plan_request.allocation_id
                        allocation = session.scalars(
                            sa.select(Allocation).where(Allocation.id == allocation_id)
                        ).first()
                        notification_user_ids = [
                            allocation_user.user.id
                            for allocation_user in allocation.allocation_users
                        ]
                        notification_user_ids.append(
                            target.observation_plan_request.requester_id
                        )
                        instrument = allocation.instrument
                        localization_id = (
                            target.observation_plan_request.localization_id
                        )
                        localization = session.scalars(
                            sa.select(Localization).where(
                                Localization.id == localization_id
                            )
                        ).first()
                        if user.id in notification_user_ids:
                            session.add(
                                UserNotification(
                                    user=user,
                                    text=f"New Observation Plan submission for GcnEvent *{localization.dateobs}* for *{instrument.name}* by user *{target.observation_plan_request.requester.username}*",
                                    notification_type="facility_transactions",
                                    url=f"/gcn_events/{str(localization.dateobs).replace(' ','T')}",
                                )
                            )
                    elif "followup_request" in target.to_dict():
                        allocation_id = target.followup_request.allocation_id
                        allocation = session.scalars(
                            sa.select(Allocation).where(Allocation.id == allocation_id)
                        ).first()
                        notification_user_ids = [
                            allocation_user.user.id
                            for allocation_user in allocation.allocation_users
                        ]
                        notification_user_ids.append(
                            target.followup_request.requester_id
                        )
                        shift_user_ids = users_on_shift(session)
                        for shift_user_id in shift_user_ids:
                            user = session.scalar(
                                sa.select(User).where(User.id == shift_user_id)
                            )
                            check_access = session.scalar(
                                Allocation.select(user).where(
                                    Allocation.id == allocation_id
                                )
                            )
                            if check_access is not None:
                                notification_user_ids.append(shift_user_id)
                        notification_user_ids = list(set(notification_user_ids))

                        instrument = allocation.instrument
                        if user.id in notification_user_ids:
                            session.add(
                                UserNotification(
                                    user=user,
                                    text=f"New Follow-up submission for object *{target.followup_request.obj_id}* by *{instrument.name}* by user *{target.followup_request.requester.username}*",
                                    notification_type="facility_transactions",
                                    url=f"/source/{target.followup_request.obj_id}",
                                )
                            )
                elif is_followup_request:
                    if target.status == "submitted":
                        continue
                    allocation_id = target.allocation_id
                    allocation = session.scalars(
                        sa.select(Allocation).where(Allocation.id == allocation_id)
                    ).first()
                    notification_user_ids = [
                        allocation_user.user.id
                        for allocation_user in allocation.allocation_users
                    ] + [watcher.user_id for watcher in target.watchers]
                    notification_user_ids.append(target.requester_id)
                    notification_user_ids.append(target.last_modified_by_id)
                    shift_user_ids = users_on_shift(session)
                    for shift_user_id in shift_user_ids:
                        user = session.scalar(
                            sa.select(User).where(User.id == shift_user_id)
                        )
                        check_access = session.scalar(
                            Allocation.select(user).where(
                                Allocation.id == allocation_id
                            )
                        )
                        if check_access is not None:
                            notification_user_ids.append(shift_user_id)
                    notification_user_ids = list(set(notification_user_ids))

                    instrument = allocation.instrument
                    if user.id in notification_user_ids:
                        session.add(
                            UserNotification(
                                user=user,
                                text=f"Follow-up submission for object *{target.obj_id}* by *{instrument.name}* updated by user *{target.last_modified_by.username}*",
                                notification_type="facility_transactions",
                                url=f"/source/{target.obj_id}",
                            )
                        )
                elif is_analysis_service:
                    if target.status == "completed":
                        session.add(
                            UserNotification(
                                user=user,
                                text=f"New completed analysis service for object *{target.obj_id}* with name *{target.analysis_service.name}*",
                                notification_type="analysis_services",
                                url=f"/source/{target.obj_id}",
                            )
                        )
                elif is_observation_plan:
                    observation_plan_request_id = target.observation_plan_request_id
                    observation_plan_request = session.scalars(
                        sa.select(ObservationPlanRequest).where(
                            ObservationPlanRequest.id == observation_plan_request_id
                        )
                    ).first()
                    allocation = session.scalars(
                        sa.select(Allocation).where(
                            Allocation.id == observation_plan_request.allocation_id
                        )
                    ).first()
                    notification_user_ids = [
                        allocation_user.user.id
                        for allocation_user in allocation.allocation_users
                    ]
                    notification_user_ids.append(observation_plan_request.requester_id)
                    instrument = allocation.instrument
                    localization_id = observation_plan_request.localization_id
                    localization = session.scalars(
                        sa.select(Localization).where(
                            Localization.id == localization_id
                        )
                    ).first()
                    if user.id in notification_user_ids:
                        session.add(
                            UserNotification(
                                user=user,
                                text=f"New Observation Plan submission for GcnEvent *{localization.dateobs}* for *{instrument.name}* by user *{observation_plan_request.requester.username}*",
                                notification_type="observation_plans",
                                url=f"/gcn_events/{str(localization.dateobs).replace(' ','T')}",
                            )
                        )
                elif is_group_admission_request:
                    user_from_request = session.scalars(
                        sa.select(User).where(User.id == target.user_id)
                    ).first()
                    group_from_request = session.scalars(
                        sa.select(Group).where(Group.id == target.group_id)
                    ).first()
                    session.add(
                        UserNotification(
                            user=user,
                            text=f"New Group Admission Request from *@{user_from_request.username}* for Group *{group_from_request.name}*",
                            notification_type="group_admission_request",
                            url=f"/group/{group_from_request.id}",
                        )
                    )
                else:
                    favorite_sources = session.scalars(
                        sa.select(Listing)
                        .where(Listing.list_name == 'favorites')
                        .where(Listing.obj_id == target.obj_id)
                        .where(Listing.user_id == user.id)
                    ).all()
                    if pref is None:
                        continue

                    if is_classification:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources" in pref.keys()
                            and any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            )
                        ):
                            session.add(
                                UserNotification(
                                    user=user,
                                    text=f"New classification on favorite source *{target.obj_id}*",
                                    notification_type="favorite_sources_new_classification",
                                    url=f"/source/{target.obj_id}",
                                )
                            )
                        elif (pref is not None) and "sources" in pref.keys():
                            if "classifications" in pref['sources'].keys():
                                if (
                                    target.classification
                                    in pref['sources']['classifications']
                                ):
                                    session.add(
                                        UserNotification(
                                            user=user,
                                            text=f"New classification *{target.classification}* for source *{target.obj_id}*",
                                            notification_type="sources",
                                            url=f"/source/{target.obj_id}",
                                        )
                                    )
                    elif is_spectra:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources" in pref.keys()
                        ):
                            if any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New spectrum on favorite source *{target.obj_id}*",
                                        notification_type="favorite_sources_new_spectra",
                                        url=f"/source/{target.obj_id}",
                                    )
                                )
                    elif is_comment:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources" in pref.keys()
                        ):
                            if any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New comment on favorite source *{target.obj_id}*",
                                        notification_type="favorite_sources_new_comment",
                                        url=f"/source/{target.obj_id}",
                                    )
                                )


def users_on_shift(session):
    users = session.scalars(
        sa.select(ShiftUser).where(
            ShiftUser.shift_id == Shift.id,
            Shift.start_date <= datetime.datetime.now(),
            Shift.end_date >= datetime.datetime.now(),
        )
    ).all()
    return [user.user_id for user in users]

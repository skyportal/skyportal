import asyncio
import html
import json
import operator
import string
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import arrow
import requests
import sqlalchemy as sa
import tornado.escape
import tornado.ioloop
import tornado.web
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Say, VoiceResponse

from baselayer.app.env import load_env
from baselayer.app.flow import Flow
from baselayer.app.models import init_db
from baselayer.log import make_log
from skyportal.models import (
    Allocation,
    AnalysisService,
    Classification,
    Comment,
    DBSession,
    Deployment,
    EventObservationPlan,
    Feedback,
    FeedbackReply,
    FollowupRequest,
    FollowupRequestUser,
    GcnEvent,
    GcnEventExtraction,
    GcnNotice,
    GcnTag,
    Group,
    GroupAdmissionRequest,
    GroupUser,
    Listing,
    Localization,
    ObjAnalysis,
    ObservationPlanRequest,
    RoleACL,
    Shift,
    ShiftUser,
    Source,
    Spectrum,
    User,
    UserACL,
    UserNotification,
    UserRole,
)
from skyportal.utils.app import get_app_base_url
from skyportal.utils.email import send_email
from skyportal.utils.gcn import get_skymap_properties
from skyportal.utils.gcn_extraction_tags import (
    apply_tags,
    classification_of,
    tag_event,
    wants_classification,
)
from skyportal.utils.notifications import (
    escape_markdown,
    escape_slack,
    feedback_notification_text,
    gcn_email_notification,
    gcn_notification_content,
    gcn_slack_notification,
    mention_email_notification,
    source_email_notification,
    source_notification_content,
    source_slack_notification,
)

env, cfg = load_env()
log = make_log("notification_queue")

FEEDBACK_CATEGORIES = {"bug": "bug report", "change": "change request"}

init_db(**cfg["database"])

request_session = requests.Session()
request_session.trust_env = (
    False  # Otherwise pre-existing netrc config will override auth headers
)

account_sid = cfg["twilio.sms_account_sid"]
auth_token = cfg["twilio.sms_auth_token"]
from_number = cfg["twilio.from_number"]
client = None
if account_sid and auth_token and from_number:
    client = TwilioClient(account_sid, auth_token)

email = False
if cfg.get("email_service") == "sendgrid" or cfg.get("email_service") == "smtp":
    email = True


op_options = [
    "lt",
    "le",
    "eq",
    "ne",
    "ge",
    "gt",
]


def notification_resource_type(target):
    if not target["notification_type"]:
        return None
    if target["notification_type"].startswith("feedback"):
        return "feedback"
    if (
        "favorite_sources" not in target["notification_type"]
        and "gcn_events" not in target["notification_type"]
        and "sources" not in target["notification_type"]
    ):
        return target["notification_type"]
    elif "favorite_sources" in target["notification_type"]:
        return "favorite_sources"
    elif "gcn_events" in target["notification_type"]:
        return "gcn_events"
    elif "sources" in target["notification_type"]:
        return "sources"


def user_preferences(target, notification_setting, resource_type):
    if not isinstance(notification_setting, str):
        return
    if not isinstance(resource_type, str):
        return
    if not target["user"]:
        return

    if notification_setting == "email":
        if not email:
            return
        if not target["user"]["contact_email"]:
            return
        # this ensures that an email is sent regardless of the user's preferences
        # this is useful for group_admission_requests, where we want the admins to always be notified by email
        if resource_type in ["group_admission_request"]:
            return True

    if "preferences" not in target["user"]:
        return

    if notification_setting in ["sms", "phone"]:
        if client is None:
            return
        if not target["user"]["contact_phone"]:
            return

    if notification_setting == "slack":
        if not target["user"]["preferences"].get("slack_integration"):
            return
        if not target["user"]["preferences"]["slack_integration"].get("active"):
            return
        if (
            not target["user"]["preferences"]["slack_integration"]
            .get("url", "")
            .startswith(cfg["slack.expected_url_preamble"])
        ):
            return

    prefs = target["user"]["preferences"].get("notifications")
    if not prefs:
        return
    else:
        if resource_type in [
            "sources",
            "favorite_sources",
            "gcn_events",
            "gcn_extractions",
            "facility_transactions",
            "mention",
            "analysis_services",
            "observation_plans",
            "deployments",
            "feedback",
        ]:
            if not prefs.get(resource_type, False):
                return
            if not prefs[resource_type].get(notification_setting, False):
                return
            if not prefs[resource_type][notification_setting].get("active", False):
                return

        return prefs


def send_slack_notification(target):
    resource_type = notification_resource_type(target)
    notifications_prefs = user_preferences(target, "slack", resource_type)
    if not notifications_prefs:
        return
    integration_url = target["user"]["preferences"]["slack_integration"].get("url")

    slack_microservice_url = (
        f"http://{cfg['hosts.slack']}:{cfg['slack.microservice_port']}"
    )

    app_url = get_app_base_url()

    try:
        if resource_type == "gcn_events":
            data = json.dumps(
                {
                    "url": integration_url,
                    "blocks": gcn_slack_notification(
                        target=target,
                        data=target["content"],
                        new_tag=(target["notification_type"] == "gcn_events_new_tag"),
                    ),
                }
            )
        elif resource_type == "sources":
            data = json.dumps(
                {
                    "url": integration_url,
                    "blocks": source_slack_notification(
                        target=target, data=target["content"]
                    ),
                }
            )
        elif resource_type == "feedback" and target.get("content"):
            text = feedback_notification_text(target["content"], escape_slack)
            data = json.dumps(
                {"url": integration_url, "text": f"{text} ({app_url}{target['url']})"}
            )
        else:
            data = json.dumps(
                {
                    "url": integration_url,
                    "text": f"{target['text']} ({app_url}{target['url']})",
                }
            )

        requests.post(
            slack_microservice_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        log(
            f"Sent slack notification to user {target['user']['id']} at slack_url: {integration_url}, body: {target['text']}, resource_type: {resource_type}"
        )
    except Exception as e:
        log(f"Error sending slack notification: {e}")


def send_email_notification(target):
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
                target=target, data=target["content"]
            )
        elif resource_type == "gcn_events":
            subject, body = gcn_email_notification(
                target=target,
                data=target["content"],
                new_tag=(target["notification_type"] == "gcn_events_new_tag"),
            )

        elif resource_type == "facility_transactions":
            subject = f"{cfg['app.title']} - New facility transaction"

        elif resource_type == "observation_plans":
            subject = f"{cfg['app.title']} - New observation plans"

        elif resource_type == "analysis_services":
            subject = f"{cfg['app.title']} - New completed analysis service"

        elif resource_type == "favorite_sources":
            if target["notification_type"] == "favorite_sources_new_classification":
                subject = (
                    f"{cfg['app.title']} - New classification on a favorite source"
                )
            elif target["notification_type"] == "favorite_sources_new_spectrum":
                subject = f"{cfg['app.title']} - New spectrum on a favorite source"
            elif target["notification_type"] == "favorite_sources_new_comment":
                subject = f"{cfg['app.title']} - New comment on a favorite source"

        elif resource_type == "mention":
            if target.get("content"):
                subject, body = mention_email_notification(
                    target=target, data=target["content"]
                )
            else:
                subject = f"{cfg['app.title']} - User mentioned you in a comment"

        elif resource_type == "group_admission_request":
            subject = f"{cfg['app.title']} - New group admission request"

        elif resource_type == "deployments":
            subject = f"{cfg['app.title']} - New deployment"

        elif resource_type == "feedback":
            subject = (
                f"{cfg['app.title']} - Reply to your feedback"
                if target["notification_type"] == "feedback_reply"
                else f"{cfg['app.title']} - New feedback"
            )
            if target.get("content"):
                text = feedback_notification_text(
                    target["content"], html.escape, bold=""
                )
                body = f"<p>{text}</p><p><a href='{app_url}{target['url']}'>View in {cfg['app.title']}</a></p>"

        if subject and target["user"]["contact_email"]:
            try:
                if body is None:
                    body = f"{target['text']} ({app_url}{target['url']})"
                send_email(
                    recipients=[target["user"]["contact_email"]],
                    subject=subject,
                    body=body,
                )
                log(
                    f"Sent email notification to user {target['user']['id']} at email: {target['user']['contact_email']}, subject: {subject}, body: {body}, resource_type: {resource_type}"
                )
            except Exception as e:
                log(f"Error sending email notification: {e}")

    except Exception as e:
        log(f"Error sending email notification: {e}")


def send_sms_notification(target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "sms", resource_type)
    if not prefs:
        return

    sending = False
    if prefs[resource_type]["sms"].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target["user"]["id"])
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]["sms"].get("time_slot", [])
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
                body=f"{cfg['app.title']} - {target['text']}",
                from_=from_number,
                to=target["user"]["contact_phone"].e164,
            )
            log(
                f"Sent SMS notification to user {target['user']['id']} at phone number: {target['user']['contact_phone'].e164}, body: {target['text']}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending sms notification: {e}")


def send_phone_notification(target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "phone", resource_type)

    if not prefs:
        return

    sending = False
    if prefs[resource_type]["phone"].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target["user"]["id"])
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]["phone"].get("time_slot", [])
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
            message = f"Greetings. This is the SkyPortal robot. {target['text']}"
            client.calls.create(
                twiml=VoiceResponse().append(Say(message=message)),
                from_=from_number,
                to=target["user"]["contact_phone"].e164,
            )
            log(
                f"Sent Phone Call notification to user {target['user']['id']} at phone number: {target['user']['contact_phone'].e164}, message: {message}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending phone call notification: {e}")


def send_whatsapp_notification(target):
    resource_type = notification_resource_type(target)
    prefs = user_preferences(target, "whatsapp", resource_type)
    if not prefs:
        return

    sending = False
    if prefs[resource_type]["whatsapp"].get("on_shift", False):
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target["user"]["id"])
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            sending = True

    timeslot = prefs[resource_type]["whatsapp"].get("time_slot", [])
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
                body=f"{cfg['app.title']} - {target['text']}",
                from_="whatsapp:" + str(from_number),
                to="whatsapp" + str(target["user"]["contact_phone"].e164),
            )
            log(
                f"Sent WhatsApp notification to user {target['user']['id']} at phone number: {target['user']['contact_phone'].e164}, body: {target['text']}, resource_type: {resource_type}"
            )
        except Exception as e:
            log(f"Error sending WhatsApp notification: {e}")


def push_frontend_notification(target):
    if "user_id" in target:
        user_id = target["user_id"]
    elif "user" in target:
        if "id" in target["user"]:
            user_id = target["user"]["id"]
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
        f"Sent frontend notification to user {user_id}, body: {target['text']}, resource_type: {resource_type}"
    )
    ws_flow = Flow()
    ws_flow.push(user_id, "skyportal/FETCH_NOTIFICATIONS")


def users_on_shift(session):
    now = arrow.utcnow().datetime
    return session.scalars(
        sa.select(ShiftUser.user_id)
        .join(Shift, Shift.id == ShiftUser.shift_id)
        .where(Shift.start_date <= now, Shift.end_date >= now)
        .distinct()
    ).all()


def shift_users_with_access(session, allocation_id):
    shift_users = session.scalars(
        sa.select(User).where(User.id.in_(users_on_shift(session)))
    ).all()
    return [
        shift_user.id
        for shift_user in shift_users
        if session.scalar(
            Allocation.select(shift_user).where(Allocation.id == allocation_id)
        )
        is not None
    ]


queue = []


def service(queue):
    while True:
        if len(queue) == 0:
            time.sleep(1)
            continue
        notification = queue.pop(0)
        if notification is None:
            continue

        try:
            push_frontend_notification(notification)
            send_phone_notification(notification)
            send_sms_notification(notification)
            send_whatsapp_notification(notification)
            send_email_notification(notification)
            send_slack_notification(notification)
        except Exception as e:
            log(f"Error processing notification ID {notification['id']}: {str(e)}")


def api(queue):
    processor = ThreadPoolExecutor(max_workers=1)

    class QueueHandler(tornado.web.RequestHandler):
        def get(self):
            self.set_header("Content-Type", "application/json")
            self.write({"status": "success", "data": {"queue_length": len(queue)}})

        def post(self):
            try:
                data = tornado.escape.json_decode(self.request.body)
            except json.JSONDecodeError:
                self.set_status(400)
                return self.write({"status": "error", "message": "Malformed JSON data"})
            if "target_class_name" not in data or "target_id" not in data:
                self.set_status(400)
                return self.write(
                    {
                        "status": "error",
                        "message": "Missing target_class_name or target_id",
                    }
                )

            processor.submit(self.process, data)
            self.write(
                {
                    "status": "success",
                    "message": "Notification request accepted into queue",
                    "data": {"queue_length": len(queue)},
                }
            )

        @staticmethod
        def process(data):
            target_class_name = data["target_class_name"]
            target_id = data["target_id"]
            target_content = None

            is_gcn_notice = target_class_name == "GcnNotice"
            is_gcn_localization = target_class_name == "Localization"
            is_gcn_tag = target_class_name == "GcnTag"
            is_classification = target_class_name == "Classification"
            is_gcn_extraction = target_class_name == "GcnEventExtraction"
            is_spectra = target_class_name == "Spectrum"
            is_comment = target_class_name == "Comment"
            is_group_admission_request = target_class_name == "GroupAdmissionRequest"
            is_analysis_service = target_class_name == "ObjAnalysis"
            is_observation_plan = target_class_name == "EventObservationPlan"
            is_followup_request = target_class_name == "FollowupRequest"
            is_deployment = target_class_name == "Deployment"
            is_feedback = target_class_name == "Feedback"
            is_feedback_reply = target_class_name == "FeedbackReply"

            with DBSession() as session:
                try:
                    if is_gcn_notice or is_gcn_localization or is_gcn_tag:
                        stmt = sa.select(User).where(
                            User.preferences["notifications"]["gcn_events"]["active"]
                            .astext.cast(sa.Boolean)
                            .is_(True),
                        )
                        if is_gcn_tag:
                            stmt = stmt.where(
                                User.preferences["notifications"]["gcn_events"][
                                    "new_tags"
                                ]
                                .astext.cast(sa.Boolean)
                                .is_(True),
                            )
                        users = session.scalars(stmt).all()

                        if is_gcn_tag:
                            gcn_tag = session.scalars(
                                sa.select(GcnTag).where(GcnTag.id == target_id)
                            ).first()
                            gcn_event = session.scalars(
                                sa.select(GcnEvent).where(
                                    GcnEvent.dateobs == gcn_tag.dateobs
                                )
                            ).first()
                            if len(gcn_event.localizations) > 0:
                                target_id = gcn_event.localizations[0].id
                            else:
                                return

                        target_class = Localization if not is_gcn_notice else GcnNotice
                        target = session.scalars(
                            sa.select(target_class).where(target_class.id == target_id)
                        ).first()
                        target_data = target.to_dict()
                        target_content = gcn_notification_content(target, session)

                    elif is_followup_request:
                        users = session.scalars(
                            sa.select(User).where(
                                User.preferences["notifications"][
                                    "facility_transactions"
                                ]["active"]
                                .astext.cast(sa.Boolean)
                                .is_(True)
                            )
                        ).all()
                        target_class = FollowupRequest
                        target_data = session.scalars(
                            sa.select(FollowupRequest).where(
                                FollowupRequest.id == target_id
                            )
                        ).first()
                        try:
                            target_data = target_data.to_dict()
                        except Exception:
                            # this happens if the followup request is deleted
                            # in the future, maybe we'll want to notify on deletion?
                            return
                        if target_data["status"].startswith(
                            ("submitted", "In progress")
                        ):
                            return
                        allocation = session.scalars(
                            sa.select(Allocation).where(
                                Allocation.id == target_data["allocation_id"]
                            )
                        ).first()
                        instrument = allocation.instrument
                        notification_user_ids = {
                            allocation_user.user_id
                            for allocation_user in allocation.allocation_users
                        } | set(
                            session.scalars(
                                sa.select(FollowupRequestUser.user_id).where(
                                    FollowupRequestUser.followuprequest_id == target_id
                                )
                            )
                        )
                        notification_user_ids.add(target_data["requester_id"])
                        notification_user_ids.update(
                            shift_users_with_access(session, allocation.id)
                        )
                    elif is_analysis_service:
                        users = session.scalars(
                            sa.select(User).where(
                                User.preferences["notifications"]["analysis_services"][
                                    "active"
                                ]
                                .astext.cast(sa.Boolean)
                                .is_(True)
                            )
                        ).all()
                        target_class = ObjAnalysis
                        target_data = (
                            session.scalars(
                                sa.select(ObjAnalysis).where(
                                    ObjAnalysis.id == target_id
                                )
                            )
                            .first()
                            .to_dict()
                        )
                    elif is_observation_plan:
                        users = session.scalars(
                            sa.select(User).where(
                                User.preferences["notifications"][
                                    "facility_transactions"
                                ]["active"]
                                .astext.cast(sa.Boolean)
                                .is_(True)
                            )
                        ).all()
                        target_class = EventObservationPlan
                        target_data = (
                            session.scalars(
                                sa.select(EventObservationPlan).where(
                                    EventObservationPlan.id == target_id
                                )
                            )
                            .first()
                            .to_dict()
                        )
                    elif is_deployment:
                        users = session.scalars(
                            sa.select(User).where(
                                User.preferences["notifications"]["deployments"][
                                    "active"
                                ]
                                .astext.cast(sa.Boolean)
                                .is_(True)
                            )
                        ).all()
                        target_class = Deployment
                        target_data = (
                            session.scalars(
                                sa.select(Deployment).where(Deployment.id == target_id)
                            )
                            .first()
                            .to_dict()
                        )
                    elif is_feedback:
                        admin_ids = sa.union(
                            sa.select(UserACL.user_id).where(
                                UserACL.acl_id == "System admin"
                            ),
                            sa.select(UserRole.user_id)
                            .join(RoleACL, RoleACL.role_id == UserRole.role_id)
                            .where(RoleACL.acl_id == "System admin"),
                        )
                        users = session.scalars(
                            sa.select(User).where(User.id.in_(admin_ids))
                        ).all()
                        target_class = Feedback
                        feedback = session.scalar(
                            sa.select(Feedback).where(Feedback.id == target_id)
                        )
                        target_data = {
                            **feedback.to_dict(),
                            "author": feedback.author.username,
                        }
                    elif is_feedback_reply:
                        target_class = FeedbackReply
                        reply = session.scalar(
                            sa.select(FeedbackReply).where(
                                FeedbackReply.id == target_id
                            )
                        )
                        users = [reply.feedback.author]
                        target_data = {
                            **reply.to_dict(),
                            "author": reply.author.username,
                            "category": reply.feedback.category,
                        }
                    elif is_group_admission_request:
                        target_class = GroupAdmissionRequest
                        target_data = (
                            session.scalars(
                                sa.select(GroupAdmissionRequest).where(
                                    GroupAdmissionRequest.id == target_id
                                )
                            )
                            .first()
                            .to_dict()
                        )

                        users = []
                        group_admins_gu = session.scalars(
                            sa.select(GroupUser).where(
                                GroupUser.group_id == target_data["group_id"],
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
                                    sa.or_(
                                        User.preferences["notifications"]["sources"][
                                            "active"
                                        ]
                                        .astext.cast(sa.Boolean)
                                        .is_(True),
                                        User.preferences["notifications"][
                                            "favorite_sources"
                                        ]["active"]
                                        .astext.cast(sa.Boolean)
                                        .is_(True),
                                    )
                                )
                            ).all()
                            target_class = Classification
                            target = session.scalars(
                                sa.select(Classification).where(
                                    Classification.id == target_id
                                )
                            ).first()
                            target_data = {
                                **target.to_dict(),
                                "group_ids": [group.id for group in target.groups],
                            }
                            target_content = source_notification_content(
                                target, target_type="classification"
                            )
                        elif is_spectra:
                            users = session.scalars(
                                sa.select(User).where(
                                    sa.or_(
                                        User.preferences["notifications"]["sources"][
                                            "active"
                                        ]
                                        .astext.cast(sa.Boolean)
                                        .is_(True),
                                        User.preferences["notifications"][
                                            "favorite_sources"
                                        ]["active"]
                                        .astext.cast(sa.Boolean)
                                        .is_(True),
                                    )
                                )
                            ).all()
                            target_class = Spectrum
                            target = session.scalars(
                                sa.select(Spectrum).where(Spectrum.id == target_id)
                            ).first()
                            target_data = {
                                **target.to_dict(),
                                "group_ids": [group.id for group in target.groups],
                            }
                            if target.followup_request_id is not None:
                                target_data["allocation_id"] = (
                                    target.followup_request.allocation_id
                                )
                            target_content = source_notification_content(
                                target, target_type="spectrum"
                            )
                        elif is_comment:
                            users = session.scalars(
                                sa.select(User).where(
                                    User.preferences["notifications"][
                                        "favorite_sources"
                                    ]["active"]
                                    .astext.cast(sa.Boolean)
                                    .is_(True)
                                )
                            ).all()
                            target_class = Comment
                            target_data = (
                                session.scalars(
                                    sa.select(Comment).where(Comment.id == target_id)
                                )
                                .first()
                                .to_dict()
                            )
                        elif is_gcn_extraction:
                            users = session.scalars(
                                sa.select(User).where(
                                    User.preferences["notifications"][
                                        "gcn_extractions"
                                    ]["active"]
                                    .astext.cast(sa.Boolean)
                                    .is_(True)
                                )
                            ).all()
                            target_class = GcnEventExtraction
                            target_data = (
                                session.scalars(
                                    sa.select(GcnEventExtraction).where(
                                        GcnEventExtraction.id == target_id
                                    )
                                )
                                .first()
                                .to_dict()
                            )
                        else:
                            users = []

                    if is_gcn_extraction:
                        extraction = session.scalar(
                            sa.select(GcnEventExtraction).where(
                                GcnEventExtraction.id == target_id
                            )
                        )
                        if extraction is not None:
                            tagged = apply_tags(
                                session, extraction, extraction.sent_by_id
                            )
                            # The event carries the tag too, since a circular can
                            # classify a trigger that has no object to tag.
                            event_tag = tag_event(
                                session, extraction, extraction.sent_by_id
                            )
                            if tagged or event_tag:
                                session.commit()
                            if tagged:
                                log(
                                    f"tagged {', '.join(tagged)} from extraction {target_id}"
                                )
                            if event_tag:
                                log(
                                    f"tagged event {extraction.dateobs} "
                                    f"{event_tag} from extraction {target_id}"
                                )

                    users = [user for user in users if user.is_active()]
                    failure_count = 0
                    nb_users = len(users)
                    for user in users:
                        try:
                            # Only notify users who have read access to the new record in question
                            if user.preferences is not None:
                                pref = user.preferences.get("notifications", None)
                            else:
                                pref = None

                            if (
                                session.scalars(
                                    target_class.select(user, mode="read").where(
                                        target_class.id == target_id
                                    )
                                ).first()
                                is not None
                            ):
                                if (
                                    is_gcn_notice or is_gcn_localization or is_gcn_tag
                                ) and (pref is not None):
                                    event = session.scalars(
                                        sa.select(GcnEvent).where(
                                            GcnEvent.dateobs == target_data["dateobs"]
                                        )
                                    ).first()

                                    notices = event.gcn_notices
                                    if target_class is not GcnNotice:
                                        filtered_notices = [
                                            notice
                                            for notice in notices
                                            if notice.id == target_data["notice_id"]
                                        ]

                                        # only notify on localizations that come from a notice
                                        if len(filtered_notices) == 0:
                                            continue
                                        notice = filtered_notices[0]
                                    else:
                                        # here, the notice is the notice of the target_id
                                        filtered_notices = [
                                            notice
                                            for notice in notices
                                            if notice.id == target_id
                                        ]
                                        if len(filtered_notices) == 0:
                                            continue
                                        notice = filtered_notices[0]

                                    gcn_prefs = pref["gcn_events"].get("properties", {})
                                    if len(gcn_prefs.keys()) == 0:
                                        continue
                                    for gcn_pref in gcn_prefs.values():
                                        notice_type = (
                                            notice.notice_type
                                            if notice.notice_format
                                            in ["voevent", "json"]
                                            else None
                                        )
                                        if (
                                            len(gcn_pref.get("gcn_notice_types", []))
                                            > 0
                                        ):
                                            if (
                                                notice_type is not None
                                                and notice_type
                                                not in gcn_pref["gcn_notice_types"]
                                            ):
                                                continue

                                        if len(gcn_pref.get("gcn_tags", [])) > 0:
                                            intersection = list(
                                                set(event.tags)
                                                & set(gcn_pref["gcn_tags"])
                                            )
                                            if len(intersection) == 0:
                                                continue

                                        if len(gcn_pref.get("gcn_properties", [])) > 0:
                                            properties_bool = []
                                            for properties in event.properties:
                                                properties_dict = properties.data
                                                properties_pass = True
                                                for prop_filt in gcn_pref[
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
                                                                f"Invalid propertiesFilter value: {e}"
                                                            )
                                                        op = prop_split[2].strip()
                                                        if op not in op_options:
                                                            raise ValueError(
                                                                f"Invalid operator: {op}"
                                                            )
                                                        comp_function = getattr(
                                                            operator, op
                                                        )
                                                        if not comp_function(
                                                            properties_dict[name], value
                                                        ):
                                                            properties_pass = False
                                                            break
                                                properties_bool.append(properties_pass)
                                            if not any(properties_bool):
                                                continue

                                        if not is_gcn_notice:
                                            localization = session.scalars(
                                                sa.select(Localization).where(
                                                    Localization.id == target_id
                                                )
                                            ).first()
                                            (
                                                localization_properties_dict,
                                                localization_tags_list,
                                            ) = get_skymap_properties(localization)

                                            if (
                                                len(
                                                    gcn_pref.get(
                                                        "localization_tags", []
                                                    )
                                                )
                                                > 0
                                            ):
                                                intersection = list(
                                                    set(localization_tags_list)
                                                    & set(gcn_pref["localization_tags"])
                                                )
                                                if len(intersection) == 0:
                                                    continue

                                            for prop_filt in gcn_pref.get(
                                                "localization_properties", []
                                            ):
                                                prop_split = prop_filt.split(":")
                                                if not len(prop_split) == 3:
                                                    raise ValueError(
                                                        "Invalid propertiesFilter value -- property filter must have 3 values"
                                                    )
                                                name = prop_split[0].strip()
                                                if name in localization_properties_dict:
                                                    value = prop_split[1].strip()
                                                    try:
                                                        value = float(value)
                                                    except ValueError as e:
                                                        raise ValueError(
                                                            f"Invalid propertiesFilter value: {e}"
                                                        )
                                                    op = prop_split[2].strip()
                                                    if op not in op_options:
                                                        raise ValueError(
                                                            f"Invalid operator: {op}"
                                                        )
                                                    comp_function = getattr(
                                                        operator, op
                                                    )
                                                    if not comp_function(
                                                        localization_properties_dict[
                                                            name
                                                        ],
                                                        value,
                                                    ):
                                                        continue

                                        if is_gcn_tag:
                                            text = (
                                                f"Updated GCN Event *{target_data['dateobs']}*, "
                                                f"with Tag *{gcn_tag.text}*"
                                            )
                                        elif len(notices) > 1:
                                            text = (
                                                f"New Notice for GCN Event *{target_data['dateobs']}*, "
                                                f"with Notice Type *{notice_type}*"
                                            )
                                        else:
                                            text = (
                                                f"New GCN Event *{target_data['dateobs']}*, "
                                                f"with Notice Type *{notice_type}*"
                                            )

                                        notification = UserNotification(
                                            user=user,
                                            text=text,
                                            notification_type="gcn_events_new_tag"
                                            if is_gcn_tag
                                            else "gcn_events",
                                            url=f"/gcn_events/{str(target_data['dateobs']).replace(' ', 'T')}",
                                        )
                                        session.add(notification)
                                        session.commit()
                                        target = {
                                            **notification.to_dict(),
                                            "user": {
                                                **notification.user.to_dict(),
                                                "preferences": notification.user.preferences,
                                            },
                                            "content": target_content,
                                        }
                                        queue.append(target)

                                elif is_followup_request:
                                    if user.id in notification_user_ids:
                                        notification = UserNotification(
                                            user=user,
                                            text=f"Follow-up request for object *{target_data['obj_id']}* by *{instrument.name}*: {textwrap.shorten(target_data['status'], 120, placeholder='...')}",
                                            notification_type="facility_transactions",
                                            url=f"/source/{target_data['obj_id']}",
                                        )
                                        session.add(notification)
                                        session.commit()
                                        target = {
                                            **notification.to_dict(),
                                            "user": {
                                                **notification.user.to_dict(),
                                                "preferences": notification.user.preferences,
                                            },
                                        }
                                        queue.append(target)
                                elif is_gcn_extraction:
                                    label = classification_of(target_data.get("data"))
                                    if wants_classification(pref, label):
                                        dateobs = target_data["dateobs"]
                                        circular_id = target_data.get("circular_id")
                                        source = (
                                            f"Circular {circular_id}"
                                            if circular_id
                                            else "A circular"
                                        )
                                        notification = UserNotification(
                                            user=user,
                                            text=(
                                                f"{source} reports *{label}* "
                                                f"for event *{dateobs}*"
                                            ),
                                            notification_type="gcn_extractions",
                                            url=f"/gcn_events/{dateobs}",
                                        )
                                        session.add(notification)
                                        session.commit()
                                        target = {
                                            **notification.to_dict(),
                                            "user": {
                                                **notification.user.to_dict(),
                                                "preferences": notification.user.preferences,
                                            },
                                        }
                                        queue.append(target)
                                elif is_analysis_service:
                                    if target_data["status"] == "completed":
                                        analysis_service_id = target_data[
                                            "analysis_service_id"
                                        ]
                                        analysis_service = session.scalars(
                                            sa.select(AnalysisService).where(
                                                AnalysisService.id
                                                == analysis_service_id
                                            )
                                        ).first()
                                        notification = UserNotification(
                                            user=user,
                                            text=f"New completed analysis service for object *{target_data['obj_id']}* with name *{analysis_service.name}*",
                                            notification_type="analysis_services",
                                            url=f"/source/{target_data['obj_id']}",
                                        )
                                        session.add(notification)
                                        session.commit()
                                        target = {
                                            **notification.to_dict(),
                                            "user": {
                                                **notification.user.to_dict(),
                                                "preferences": notification.user.preferences,
                                            },
                                        }
                                        queue.append(target)
                                elif is_observation_plan:
                                    observation_plan_request_id = target_data[
                                        "observation_plan_request_id"
                                    ]
                                    observation_plan_request = session.scalars(
                                        sa.select(ObservationPlanRequest).where(
                                            ObservationPlanRequest.id
                                            == observation_plan_request_id
                                        )
                                    ).first()
                                    allocation = session.scalars(
                                        sa.select(Allocation).where(
                                            Allocation.id
                                            == observation_plan_request.allocation_id
                                        )
                                    ).first()
                                    notification_user_ids = [
                                        allocation_user.user.id
                                        for allocation_user in allocation.allocation_users
                                    ]
                                    notification_user_ids.append(
                                        observation_plan_request.requester_id
                                    )
                                    instrument = allocation.instrument
                                    localization_id = (
                                        observation_plan_request.localization_id
                                    )
                                    localization = session.scalars(
                                        sa.select(Localization).where(
                                            Localization.id == localization_id
                                        )
                                    ).first()
                                    if user.id in notification_user_ids:
                                        notification = UserNotification(
                                            user=user,
                                            text=f"New Observation Plan submission for GcnEvent *{localization.dateobs}* for *{instrument.name}* by user *{observation_plan_request.requester.username}*",
                                            notification_type="observation_plans",
                                            url=f"/gcn_events/{str(localization.dateobs).replace(' ', 'T')}",
                                        )
                                        session.add(notification)
                                        session.commit()
                                        target = {
                                            **notification.to_dict(),
                                            "user": {
                                                **notification.user.to_dict(),
                                                "preferences": notification.user.preferences,
                                            },
                                        }
                                        queue.append(target)
                                elif is_deployment:
                                    commit = target_data["commit"] or {}
                                    text = (
                                        f"New deployment of *{cfg['app.title']}*: "
                                        f"SkyPortal *{target_data['version']}*"
                                    )
                                    if commit.get("sha"):
                                        text += f" ({commit['sha']}: {commit.get('description', '')})"
                                    notification = UserNotification(
                                        user=user,
                                        text=text,
                                        notification_type="deployments",
                                        url="/deployments",
                                    )
                                    session.add(notification)
                                    session.commit()
                                    target = {
                                        **notification.to_dict(),
                                        "user": {
                                            **notification.user.to_dict(),
                                            "preferences": notification.user.preferences,
                                        },
                                    }
                                    queue.append(target)
                                elif is_feedback or is_feedback_reply:
                                    if user.id == target_data["author_id"]:
                                        continue
                                    label = FEEDBACK_CATEGORIES.get(
                                        target_data["category"], "message"
                                    )
                                    content = {
                                        "author": target_data["author"],
                                        "label": label,
                                        "snippet": textwrap.shorten(
                                            target_data["text"], 120, placeholder="..."
                                        ),
                                        "reply": is_feedback_reply,
                                    }
                                    notification = UserNotification(
                                        user=user,
                                        text=feedback_notification_text(
                                            content, escape_markdown
                                        ),
                                        notification_type="feedback_reply"
                                        if is_feedback_reply
                                        else "feedback",
                                        url="/deployments?tab=feedback",
                                    )
                                    session.add(notification)
                                    session.commit()
                                    target = {
                                        **notification.to_dict(),
                                        "user": {
                                            **notification.user.to_dict(),
                                            "preferences": notification.user.preferences,
                                        },
                                        "content": content,
                                    }
                                    queue.append(target)
                                elif is_group_admission_request:
                                    user_from_request = session.scalars(
                                        sa.select(User).where(
                                            User.id == target_data["user_id"]
                                        )
                                    ).first()
                                    group_from_request = session.scalars(
                                        sa.select(Group).where(
                                            Group.id == target_data["group_id"]
                                        )
                                    ).first()
                                    notification = UserNotification(
                                        user=user,
                                        text=f"New Group Admission Request from *@{user_from_request.username}* for Group *{group_from_request.name}*",
                                        notification_type="group_admission_request",
                                        url=f"/group/{group_from_request.id}",
                                    )
                                    session.add(notification)
                                    session.commit()
                                    target = {
                                        **notification.to_dict(),
                                        "user": {
                                            **notification.user.to_dict(),
                                            "preferences": notification.user.preferences,
                                        },
                                    }
                                    queue.append(target)
                                else:
                                    favorite_sources = session.scalars(
                                        sa.select(Listing)
                                        .where(
                                            Listing.list_name.in_(
                                                ["favorites", "watchlist"]
                                            )
                                        )
                                        .where(Listing.obj_id == target_data["obj_id"])
                                        .where(Listing.user_id == user.id)
                                    ).all()
                                    if pref is None:
                                        continue

                                    if is_classification:
                                        if (
                                            len(favorite_sources) > 0
                                            and "favorite_sources" in pref
                                            and any(
                                                target_data["obj_id"] == source.obj_id
                                                for source in favorite_sources
                                            )
                                            and not (
                                                target_data.get("ml", False)
                                                and not pref.get(
                                                    "favorite_sources", {}
                                                ).get("new_ml_classifications", False)
                                            )
                                        ):
                                            notification = UserNotification(
                                                user=user,
                                                text=f"New classification on favorite source *{target_data['obj_id']}*",
                                                notification_type="favorite_sources_new_classification",
                                                url=f"/source/{target_data['obj_id']}",
                                            )
                                            session.add(notification)
                                            session.commit()
                                            target = {
                                                **notification.to_dict(),
                                                "user": {
                                                    **notification.user.to_dict(),
                                                    "preferences": notification.user.preferences,
                                                },
                                            }
                                            queue.append(target)
                                            continue
                                        if (pref is not None) and "sources" in pref:
                                            if "classifications" in pref["sources"]:
                                                if (
                                                    target_data["classification"]
                                                    in pref["sources"][
                                                        "classifications"
                                                    ]
                                                ):
                                                    if user.is_admin is False:
                                                        accessible_groups = [
                                                            group.id
                                                            for group in user.accessible_groups
                                                        ]
                                                        if (
                                                            len(
                                                                list(
                                                                    set(
                                                                        accessible_groups
                                                                    )
                                                                    & set(
                                                                        target_data[
                                                                            "group_ids"
                                                                        ]
                                                                    )
                                                                )
                                                            )
                                                            == 0
                                                        ):
                                                            continue
                                                    if (
                                                        len(
                                                            pref["sources"].get(
                                                                "groups", []
                                                            )
                                                        )
                                                        > 0
                                                    ):
                                                        sources = session.scalars(
                                                            sa.select(Source).where(
                                                                Source.obj_id
                                                                == target_data[
                                                                    "obj_id"
                                                                ],
                                                                Source.group_id.in_(
                                                                    pref["sources"].get(
                                                                        "groups", []
                                                                    )
                                                                ),
                                                                Source.active.is_(True),
                                                            )
                                                        ).all()
                                                        if len(sources) == 0:
                                                            continue
                                                    notification = UserNotification(
                                                        user=user,
                                                        text=f"New classification *{target_data['classification']}* for source *{target_data['obj_id']}*",
                                                        notification_type="sources_new_classification",
                                                        url=f"/source/{target_data['obj_id']}",
                                                    )
                                                    session.add(notification)
                                                    session.commit()
                                                    target = {
                                                        **notification.to_dict(),
                                                        "user": {
                                                            **notification.user.to_dict(),
                                                            "preferences": notification.user.preferences,
                                                        },
                                                        "content": target_content,
                                                    }
                                                    queue.append(target)
                                    elif is_spectra:
                                        if (
                                            len(favorite_sources) > 0
                                            and "favorite_sources" in pref
                                            and any(
                                                target_data["obj_id"] == source.obj_id
                                                for source in favorite_sources
                                            )
                                        ):
                                            notification = UserNotification(
                                                user=user,
                                                text=f"New spectrum on favorite source *{target_data['obj_id']}*",
                                                notification_type="favorite_sources_new_spectrum",
                                                url=f"/source/{target_data['obj_id']}",
                                            )
                                            session.add(notification)
                                            session.commit()
                                            target = {
                                                **notification.to_dict(),
                                                "user": {
                                                    **notification.user.to_dict(),
                                                    "preferences": notification.user.preferences,
                                                },
                                            }
                                            queue.append(target)
                                            continue
                                        if (
                                            (pref is not None)
                                            and "sources" in pref
                                            and pref["sources"].get(
                                                "new_spectra", False
                                            )
                                        ):
                                            if user.is_admin is False:
                                                # check if the user's accessible_groups intersect with the groups of the spectra
                                                accessible_groups = [
                                                    group.id
                                                    for group in user.accessible_groups
                                                ]
                                                if (
                                                    len(
                                                        list(
                                                            set(accessible_groups)
                                                            & set(
                                                                target_data["group_ids"]
                                                            )
                                                        )
                                                    )
                                                    == 0
                                                ):
                                                    continue
                                            if (
                                                len(pref["sources"].get("groups", []))
                                                > 0
                                            ):
                                                sources = session.scalars(
                                                    sa.select(Source).where(
                                                        Source.obj_id
                                                        == target_data["obj_id"],
                                                        Source.group_id.in_(
                                                            pref["sources"].get(
                                                                "groups", []
                                                            )
                                                        ),
                                                        Source.active.is_(True),
                                                    )
                                                ).all()
                                                if len(sources) == 0:
                                                    continue
                                            if (
                                                (
                                                    len(
                                                        pref["sources"].get(
                                                            "allocations", []
                                                        )
                                                    )
                                                    > 0
                                                )
                                                and (
                                                    target_data.get(
                                                        "allocation_id", None
                                                    )
                                                    is not None
                                                )
                                                and target_data["allocation_id"]
                                                not in pref["sources"].get(
                                                    "allocations", []
                                                )
                                            ):
                                                continue

                                            notification = UserNotification(
                                                user=user,
                                                text=f"New spectrum for source *{target_data['obj_id']}*",
                                                notification_type="sources_new_spectrum",
                                                url=f"/source/{target_data['obj_id']}",
                                            )
                                            session.add(notification)
                                            session.commit()
                                            target = {
                                                **notification.to_dict(),
                                                "user": {
                                                    **notification.user.to_dict(),
                                                    "preferences": notification.user.preferences,
                                                },
                                                "content": target_content,
                                            }
                                            queue.append(target)

                                    elif is_comment:
                                        if (
                                            len(favorite_sources) > 0
                                            and "favorite_sources" in pref
                                            and not (
                                                target_data.get("bot", False)
                                                and not pref.get(
                                                    "favorite_sources", {}
                                                ).get("new_bot_comments", False)
                                            )
                                        ):
                                            if any(
                                                target_data["obj_id"] == source.obj_id
                                                for source in favorite_sources
                                            ):
                                                notification = UserNotification(
                                                    user=user,
                                                    text=f"New comment on favorite source *{target_data['obj_id']}*",
                                                    notification_type="favorite_sources_new_comment",
                                                    url=f"/source/{target_data['obj_id']}",
                                                )
                                                session.add(notification)
                                                session.commit()
                                                target = {
                                                    **notification.to_dict(),
                                                    "user": {
                                                        **notification.user.to_dict(),
                                                        "preferences": notification.user.preferences,
                                                    },
                                                }
                                                queue.append(target)
                        except Exception as e:
                            failure_count += 1
                            log(
                                f"Error processing notification for user {user.id}: {str(e)}"
                            )
                            DBSession().rollback()
                            continue

                    if is_comment:
                        _punctuation = string.punctuation.replace("-", "").replace(
                            "@", ""
                        )
                        _usernames = [
                            word.strip(_punctuation).replace("@", "")
                            for word in target_data.get("text", "")
                            .replace(",", " ")
                            .split()
                            if word.strip(_punctuation).startswith("@")
                        ]
                        if _usernames:
                            _author = session.scalars(
                                sa.select(User).where(
                                    User.id == target_data.get("author_id")
                                )
                            ).first()
                            _author_username = (
                                _author.username if _author else "unknown"
                            )
                            _obj_id = target_data.get("obj_id", "")
                            _mention_text = (
                                f"*@{_author_username}* mentioned you"
                                f" in a comment on *{_obj_id}*"
                            )
                            _url = f"/source/{_obj_id}"
                            _comment_obj = session.scalars(
                                sa.select(Comment).where(Comment.id == target_id)
                            ).first()
                            _content = (
                                {
                                    "author_username": _author.username,
                                    "comment_text": _comment_obj.text,
                                    "source_name": _comment_obj.obj_id,
                                }
                                if _comment_obj and _author
                                else None
                            )
                            _mentioned_users = session.scalars(
                                sa.select(User).where(
                                    User.username.in_(_usernames),
                                    User.preferences["notifications"]["mention"][
                                        "active"
                                    ]
                                    .astext.cast(sa.Boolean)
                                    .is_(True),
                                )
                            ).all()
                            for _mentioned_user in _mentioned_users:
                                if not _mentioned_user.is_active():
                                    continue
                                queue.append(
                                    {
                                        "text": _mention_text,
                                        "notification_type": "mention",
                                        "url": _url,
                                        "content": _content,
                                        "user": {
                                            **_mentioned_user.to_dict(),
                                            "preferences": _mentioned_user.preferences,
                                        },
                                    }
                                )

                    if failure_count == nb_users and nb_users > 0:
                        log("Failed to notify all users")
                except Exception as e:
                    log(f"Error processing notification: {str(e)}")
                    DBSession().rollback()

    app = tornado.web.Application([(r"/", QueueHandler)])
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    app.listen(cfg["ports.notification_queue"])
    loop.run_forever()


if __name__ == "__main__":
    try:
        t = Thread(target=service, args=(queue,))
        t2 = Thread(target=api, args=(queue,))
        t.start()
        t2.start()

        while True:
            log(f"Current notification queue length: {len(queue)}")
            time.sleep(60)
            if not t.is_alive():
                log("Notification queue service thread died, restarting")
                t = Thread(target=service, args=(queue,))
                t.start()
            if not t2.is_alive():
                log("Notification queue API thread died, restarting")
                t2 = Thread(target=api, args=(queue,))
                t2.start()
    except Exception as e:
        log(f"Error starting notification queue: {str(e)}")
        raise e

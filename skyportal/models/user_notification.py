__all__ = ['UserNotification']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import event
import arrow
import requests

from baselayer.app.models import DBSession, Base, User, AccessibleIfUserMatches
from baselayer.app.env import load_env
from baselayer.app.flow import Flow

from ..app_utils import get_app_base_url
from .allocation import Allocation
from .classification import Classification
from .gcn import GcnNotice
from .localization import Localization
from .spectrum import Spectrum
from .comment import Comment
from .listing import Listing
from .facility_transaction import FacilityTransaction
from ..email_utils import send_email
from twilio.rest import Client as TwilioClient
import gcn
from sqlalchemy import or_

from skyportal.models import Shift, ShiftUser

_, cfg = load_env()

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


@event.listens_for(UserNotification, 'after_insert')
def send_slack_notification(mapper, connection, target):

    if not target.user:
        return

    if not target.user.preferences:
        return

    notifications_prefs = target.user.preferences.get('notifications')
    if not notifications_prefs:
        return

    slack_prefs = target.user.preferences.get('slack_integration')
    print('slack prefs', slack_prefs)

    if not slack_prefs:
        return

    if slack_prefs.get("active", False):
        integration_url = slack_prefs.get("url", "")
    else:
        return

    if not integration_url.startswith(cfg.get("slack.expected_url_preamble", "https")):
        print("Slack integration URL does not start with expected preamble")
        return

    slack_microservice_url = (
        f'http://127.0.0.1:{cfg.get("slack.microservice_port", 64100)}'
    )
    ressource_type = None
    if "favorite_sources" not in target.notification_type:
        ressource_type = target.notification_type
    elif "favorite_sources" in target.notification_type:
        ressource_type = "favorite_sources"

    if not notifications_prefs.get(ressource_type, False):
        return
    if not notifications_prefs[ressource_type].get("slack", False):
        return
    if not notifications_prefs[ressource_type]['slack'].get("active", False):
        return

    app_url = get_app_base_url()
    data = json.dumps(
        {"url": integration_url, "text": f'{target.text} ({app_url}{target.url})'}
    )
    requests.post(
        slack_microservice_url, data=data, headers={'Content-Type': 'application/json'}
    )


@event.listens_for(UserNotification, 'after_insert')
def send_email_notification(mapper, connection, target):
    print("trying to send email")

    if not email:
        print("email not enabled")
        return

    if not target.user:
        print("no user")
        return

    if not target.user.contact_email:
        print("no contact email")
        return

    if not target.user.preferences:
        print("no preferences")
        return

    prefs = target.user.preferences.get('notifications')

    if not prefs:
        print("no prefs notification")
        return

    ressource_type = None
    if "favorite_sources" not in target.notification_type:
        ressource_type = target.notification_type
    elif "favorite_sources" in target.notification_type:
        ressource_type = "favorite_sources"

    if not prefs.get(ressource_type, False):
        return
    if not prefs[ressource_type].get("email", False):
        return
    if not prefs[ressource_type]['email'].get("active", False):
        return

    subject = None
    body = None

    if ressource_type == "sources":
        subject = f"{cfg['app.title']} - New followed classification on a source"
        body = f'{target.text} ({get_app_base_url()}{target.url})'

    elif ressource_type == "gcn_events":
        subject = f"{cfg['app.title']} - New GCN Event with followed notice type"
        body = f'{target.text} ({get_app_base_url()}{target.url})'

    elif ressource_type == "facility_transactions":
        subject = f"{cfg['app.title']} - New facility transaction"
        body = f'{target.text} ({get_app_base_url()}{target.url})'

    elif ressource_type == "favorite_sources":
        if target.notification_type == "favorite_sources_new_classification":
            subject = f"{cfg['app.title']} - New classification on a favorite source"
            body = f'{target.text} ({get_app_base_url()}{target.url})'
        elif target.notification_type == "favorite_sources_new_spectrum":
            subject = f"{cfg['app.title']} - New spectrum on a favorite source"
            body = f'{target.text} ({get_app_base_url()}{target.url})'
        elif target.notification_type == "favorite_sources_new_comment":
            subject = f"{cfg['app.title']} - New comment on a favorite source"
            body = f'{target.text} ({get_app_base_url()}{target.url})'

    elif ressource_type == "mention":
        subject = f"{cfg['app.title']} - User mentioned you in a comment"
        body = f'{target.text} ({get_app_base_url()}{target.url})'

    if subject and body and target.user.contact_email:
        print("sending email to ", target.user.contact_email)
        send_email(
            recipients=[target.user.contact_email],
            subject=subject,
            body=body,
        )


@event.listens_for(UserNotification, 'after_insert')
def send_sms_notification(mapper, connection, target):
    if client is None:
        return

    if not target.user:
        return

    if not target.user.contact_phone:
        return

    if not target.user.preferences:
        return

    prefs = target.user.preferences.get('notifications')

    if not prefs:
        return

    ressource_type = None
    if "favorite_sources" not in target.notification_type:
        ressource_type = target.notification_type
    elif "favorite_sources" in target.notification_type:
        ressource_type = "favorite_sources"

    if not prefs.get(ressource_type, False):
        return
    if not prefs[ressource_type].get("sms", False):
        return
    if not prefs[ressource_type]['sms'].get("active", False):
        return

    sending = False
    if prefs[ressource_type]['sms'].get("on_shift", False):
        print("user wants to receive sms on shift")
        current_shift = (
            Shift.query.join(ShiftUser)
            .filter(ShiftUser.user_id == target.user.id)
            .filter(Shift.start_date <= arrow.utcnow().datetime)
            .filter(Shift.end_date >= arrow.utcnow().datetime)
            .first()
        )
        if current_shift is not None:
            print("currently on shift")
            sending = True
    else:
        timeslot = prefs[ressource_type]['sms'].get("time_slot", [])
        print("timeslot", timeslot)
        if len(timeslot) > 0:
            current_time = arrow.utcnow().datetime
            print("time slot start", timeslot[0])
            print("time slot end", timeslot[1])
            print("current time", current_time.hour)

            if timeslot[0] < timeslot[1]:
                if (
                    current_time.hour >= timeslot[0]
                    and current_time.hour <= timeslot[1]
                ):
                    print("sending sms 1")
                    sending = True
            else:
                if current_time.hour <= timeslot[0] or current_time.hour >= timeslot[1]:
                    print("sending sms 2")
                    sending = True
    if sending:
        client.messages.create(
            body=f"{cfg['app.title']} - {target.text}",
            from_=from_number,
            to=target.user.contact_phone.e164,
        )
        print("sending sms !!!")


@event.listens_for(Classification, 'after_insert')
@event.listens_for(Spectrum, 'after_insert')
@event.listens_for(Comment, 'after_insert')
@event.listens_for(GcnNotice, 'after_insert')
@event.listens_for(FacilityTransaction, 'after_insert')
def add_user_notifications(mapper, connection, target):
    # Add front-end user notifications
    @event.listens_for(DBSession(), "after_flush", once=True)
    def receive_after_flush(session, context):
        print("add_user_notifications")
        is_facility_transaction = target.__class__.__name__ == "FacilityTransaction"
        is_gcnevent = target.__class__.__name__ == "GcnNotice"
        is_classification = target.__class__.__name__ == "Classification"
        is_spectra = target.__class__.__name__ == "Spectrum"
        is_comment = target.__class__.__name__ == "Comment"

        if is_gcnevent:
            print("it is a gcn")
            users = User.query.filter(
                User.preferences["notifications"]["gcn_events"]["active"]
                .astext.cast(sa.Boolean)
                .is_(True)
            ).all()
        elif is_facility_transaction:
            print("it is a facility transaction")
            users = User.query.filter(
                User.preferences["notifications"]["facility_transactions"]["active"]
                .astext.cast(sa.Boolean)
                .is_(True)
            ).all()
        else:
            if is_classification:
                print("it is a classification")
                users = User.query.filter(
                    or_(
                        User.preferences["notifications"]["sources"]["active"]
                        .astext.cast(sa.Boolean)
                        .is_(True),
                        User.preferences["notifications"]["favorite_sources"]["active"]
                        .astext.cast(sa.Boolean)
                        .is_(True),
                    )
                ).all()
            elif is_spectra:
                print("it is a spectrum")
                users = User.query.filter(
                    User.preferences["notifications"]["favorite_sources"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                ).all()
            elif is_comment:
                print("it is a comment")
                users = User.query.filter(
                    User.preferences["notifications"]["favorite_sources"]["active"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                ).all()
            else:
                users = []

        ws_flow = Flow()
        for user in users:
            # Only notify users who have read access to the new record in question
            if (
                target.__class__.get_if_accessible_by(target.id, user) is not None
                and "notifications" in user.preferences
            ):
                if is_gcnevent:
                    if (
                        "gcn_notice_types"
                        in user.preferences['notifications']["gcn_events"].keys()
                    ):
                        if (
                            gcn.NoticeType(target.notice_type).name
                            in user.preferences['notifications']['gcn_events'][
                                'gcn_notice_types'
                            ]
                        ):
                            print("sending gcn notification to", user.id)
                            session.add(
                                UserNotification(
                                    user=user,
                                    text=f"New GcnEvent *{target.dateobs}* with Notice Type *{gcn.NoticeType(target.notice_type).name}*",
                                    notification_type="gcn_events",
                                    url=f"/gcn_events/{str(target.dateobs).replace(' ','T')}",
                                )
                            )
                elif is_facility_transaction:
                    if "observation_plan_request" in target.to_dict():
                        allocation_id = target.observation_plan_request.allocation_id
                        allocation = session.query(Allocation).get(allocation_id)
                        instrument = allocation.instrument
                        localization_id = (
                            target.observation_plan_request.localization_id
                        )
                        localization = session.query(Localization).get(localization_id)
                        session.add(
                            UserNotification(
                                user=user,
                                text=f"New Observation Plan submission for GcnEvent *{localization.dateobs}* by *{instrument.name}*",
                                notification_type="facility_transactions",
                                url=f"/gcn_events/{str(localization.dateobs).replace(' ','T')}",
                            )
                        )
                    elif "followup_request" in target.to_dict():
                        allocation_id = target.followup_request.allocation_id
                        allocation = session.query(Allocation).get(allocation_id)
                        instrument = allocation.instrument
                        session.add(
                            UserNotification(
                                user=user,
                                text=f"New Follow-up submission for object *{target.followup_request.obj_id}* by *{instrument.name}*",
                                notification_type="facility_transactions",
                                url=f"/source/{target.followup_request.obj_id}",
                            )
                        )
                else:
                    favorite_sources = (
                        Listing.query.filter(Listing.list_name == "favorites")
                        .filter(Listing.obj_id == target.obj_id)
                        .distinct(Listing.user_id)
                        .all()
                    )

                    if is_classification:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources"
                            in user.preferences['notifications'].keys()
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
                        elif "sources" in user.preferences['notifications'].keys():
                            if (
                                "classifications"
                                in user.preferences['notifications']['sources'].keys()
                            ):
                                if (
                                    target.classification
                                    in user.preferences['notifications']['sources'][
                                        'classifications'
                                    ]
                                ):
                                    session.add(
                                        UserNotification(
                                            user=user,
                                            text=f"New classification *{target.classification}* for source *{target.obj_id}*",
                                            notification_type="sources",
                                            url=f"/sources/{target.obj_id}",
                                        )
                                    )
                    elif is_spectra:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources"
                            in user.preferences["notifications"].keys()
                        ):
                            if any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New Spectrum on favorite source *{target.obj_id}*",
                                        notification_type="favorite_sources_new_spectra",
                                        url=f"/source/{target.obj_id}",
                                    )
                                )
                    elif is_comment:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources"
                            in user.preferences["notifications"].keys()
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
                ws_flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS")

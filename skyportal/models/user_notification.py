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
client = TwilioClient(account_sid, auth_token)


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

    prefs = target.user.preferences.get('slack_integration')

    if not prefs:
        return

    if prefs.get("active", False):
        integration_url = prefs.get("url", "")
    else:
        return

    if not integration_url.startswith(cfg.get("slack.expected_url_preamble", "https")):
        return

    slack_microservice_url = (
        f'http://127.0.0.1:{cfg.get("slack.microservice_port", 64100)}'
    )

    if target.notification_type == "mention":
        if not target.user.preferences['slack_integration'].get("mentions", False):
            return
    elif target.notification_type == "gcnNotice":
        if not target.user.preferences['slack_integration'].get("gcnnotices", False):
            return
    elif target.notification_type == "facilityTransaction":
        if not target.user.preferences['slack_integration'].get(
            "facilitytransactions", False
        ):
            return
    elif not target.user.preferences['slack_integration'].get(
        "favorite_sources", False
    ):
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

    if not target.user:
        return

    if not target.user.preferences:
        return

    prefs = target.user.preferences.get('followed_ressources')

    if not prefs:
        return

    subject = None
    body = None

    if target.notification_type == "sources":
        if not target.user.preferences['followed_ressources'].get("sources", False):
            if not target.user.preferences['followed_ressources'].get(
                "sources_by_email", False
            ):
                return
        subject = "New followed classification on a source"
        body = f'{target.text} ({get_app_base_url()}{target.url})'
    elif target.notification_type == "gcn_events":
        if not target.user.preferences['followed_ressources'].get("gcn_events", False):
            if not target.user.preferences['followed_ressources'].get(
                "gcn_events_by_email", False
            ):
                return
        subject = "New GCN Event with followed notice type"
        body = f'{target.text} ({get_app_base_url()}{target.url})'
    elif target.notification_type == "favorite_sources_new_classification":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_email", False
            ):
                return
        subject = "New classification on a favorite source"
        body = f'{target.text} ({get_app_base_url()}{target.url})'
    elif target.notification_type == "favorite_sources_new_comment":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_email", False
            ):
                return
        subject = "New comment on a favorite source"
        body = f'{target.text} ({get_app_base_url()}{target.url})'
    elif target.notification_type == "favorite_sources_new_spectrum":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_email", False
            ):
                return
        subject = "New spectrum on a favorite source"
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

    if not target.user:
        return

    if not target.user.preferences:
        return

    prefs = target.user.preferences.get('followed_ressources')

    if not prefs:
        return

    if target.notification_type == "sources":
        if not target.user.preferences['followed_ressources'].get("sources", False):
            if not target.user.preferences['followed_ressources'].get(
                "sources_by_sms", False
            ):
                if not target.user.preferences['followed_ressources'].get(
                    "sources_by_sms_on_shift", False
                ):
                    return
    elif target.notification_type == "gcn_events":
        if not target.user.preferences['followed_ressources'].get("gcn_events", False):
            if not target.user.preferences['followed_ressources'].get(
                "gcn_events_by_sms", False
            ):
                return
    elif target.notification_type == "favorite_sources_new_classification":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ) and not target.user.preferences['followed_ressources'].get(
            "favorite_sources_new_classification", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_sms", False
            ):
                return
    elif target.notification_type == "favorite_sources_new_comment":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ) and not target.user.preferences['followed_ressources'].get(
            "favorite_sources_new_comment", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_sms", False
            ):
                return
    elif target.notification_type == "favorite_sources_new_spectrum":
        if not target.user.preferences['followed_ressources'].get(
            "favorite_sources", False
        ) and not target.user.preferences['followed_ressources'].get(
            "favorite_sources_new_spectrum", False
        ):
            if not target.user.preferences['followed_ressources'].get(
                "favorite_sources_by_sms", False
            ):
                return

    current_shift = (
        Shift.query.join(ShiftUser)
        .filter(ShiftUser.user_id == target.user.id)
        .filter(Shift.start_date <= arrow.utcnow().datetime)
        .filter(Shift.end_date >= arrow.utcnow().datetime)
        .first()
    )
    if current_shift is not None:
        print('user is on shift')
        client.messages.create(
            body=target.text, from_=from_number, to=target.user.contact_phone.e164
        )


@event.listens_for(Classification, 'after_insert')
@event.listens_for(Spectrum, 'after_insert')
@event.listens_for(Comment, 'after_insert')
@event.listens_for(GcnNotice, 'after_insert')
@event.listens_for(FacilityTransaction, 'after_insert')
def add_user_notifications(mapper, connection, target):
    # Add front-end user notifications
    @event.listens_for(DBSession(), "after_flush", once=True)
    def receive_after_flush(session, context):
        is_facility_transaction = "initiator_id" in target.to_dict()
        is_gcnevent = target.__tablename__ == "GcnNotice"
        is_classification = target.__class__.__name__ == "Classification"
        is_spectra = target.__class__.__name__ == "Spectrum"
        is_comment = target.__class__.__name__ == "Comment"

        if is_gcnevent:
            users = User.query.filter(
                User.preferences["followed_ressources"]["gcn_events"]
                .astext.cast(sa.Boolean)
                .is_(True)
            ).all()
        elif is_facility_transaction:
            users = User.query.filter(
                User.preferences["slack_integration"]["facilitytransactions"]
                .astext.cast(sa.Boolean)
                .is_(True)
            ).all()
        else:
            if is_classification:
                users = User.query.filter(
                    or_(
                        User.preferences["followed_ressources"]["sources"]
                        .astext.cast(sa.Boolean)
                        .is_(True),
                        User.preferences["followed_ressources"]["favorite_sources"]
                        .astext.cast(sa.Boolean)
                        .is_(True),
                    )
                ).all()
            elif is_spectra:
                users = User.query.filter(
                    User.preferences["followed_ressources"]["sources"]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                ).all()
            elif is_comment:
                users = User.query.filter(
                    User.preferences["followed_ressources"]["sources"]
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
                and "followed_ressources" in user.preferences
            ):
                if is_gcnevent:
                    if (
                        "gcn_notice_types"
                        in user.preferences['followed_ressources'].keys()
                    ):
                        if (
                            gcn.NoticeType(target.notice_type).name
                            in user.preferences['followed_ressources'][
                                'gcn_notice_types'
                            ]
                        ):
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
                                notification_type="facilityTransaction",
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
                                notification_type="facilityTransaction",
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
                            in user.preferences['followed_ressources'].keys()
                        ):
                            if any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New Classification on favorite source *{target.obj_id}*",
                                        notification_type="favorite_sources_new_classification",
                                        url=f"/source/{target.obj_id}",
                                    )
                                )
                        elif (
                            "sources" in user.preferences['followed_ressources'].keys()
                            and "sources_classifications"
                            in user.preferences['followed_ressources'].keys()
                        ):
                            if (
                                target.classification
                                in user.preferences['followed_ressources'][
                                    'sources_classifications'
                                ]
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New Classification *{target.classification}* for source *{target.obj_id}*",
                                        notification_type="sources",
                                        url=f"/sources/{target.obj_id}",
                                    )
                                )
                    elif is_spectra:
                        if (
                            len(favorite_sources) > 0
                            and "favorite_sources"
                            in user.preferences["followed_ressources"].keys()
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
                            in user.preferences["followed_ressources"].keys()
                        ):
                            if any(
                                target.obj_id == source.obj_id
                                for source in favorite_sources
                            ):
                                session.add(
                                    UserNotification(
                                        user=user,
                                        text=f"New Comment on favorite source *{target.obj_id}*",
                                        notification_type="favorite_sources_new_comment",
                                        url=f"/source/{target.obj_id}",
                                    )
                                )
                ws_flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS")

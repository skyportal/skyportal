__all__ = ['UserNotification']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy import event

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

_, cfg = load_env()


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

    is_mention = target.text.find("mentioned you") != -1
    is_gcnnotice = target.text.find("on GcnEvent") != -1
    is_facility_transaction = target.text.find("submission") != -1

    if is_mention:
        if not target.user.preferences['slack_integration'].get("mentions", False):
            return
    elif is_gcnnotice:
        if not target.user.preferences['slack_integration'].get("gcnnotices", False):
            return
    elif is_facility_transaction:
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


@event.listens_for(Classification, 'after_insert')
@event.listens_for(Spectrum, 'after_insert')
@event.listens_for(Comment, 'after_insert')
@event.listens_for(GcnNotice, 'after_insert')
@event.listens_for(FacilityTransaction, 'after_insert')
def add_user_notifications(mapper, connection, target):
    # Add front-end user notifications
    @event.listens_for(DBSession(), "after_flush", once=True)
    def receive_after_flush(session, context):

        is_gcnnotice = "dateobs" in target.to_dict()
        is_facility_transaction = "initiator_id" in target.to_dict()

        if is_gcnnotice:
            users = User.query.filter(
                User.preferences["slack_integration"]["gcnnotices"]
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
            listing_subquery = (
                Listing.query.filter(Listing.list_name == "favorites")
                .filter(Listing.obj_id == target.obj_id)
                .distinct(Listing.user_id)
                .subquery()
            )
            users = (
                User.query.join(listing_subquery, User.id == listing_subquery.c.user_id)
                .filter(
                    User.preferences["favorite_sources_activity_notifications"][
                        target.__tablename__
                    ]
                    .astext.cast(sa.Boolean)
                    .is_(True)
                )
                .all()
            )
        ws_flow = Flow()
        for user in users:
            # Only notify users who have read access to the new record in question
            if target.__class__.get_if_accessible_by(target.id, user) is not None:
                if is_gcnnotice:
                    session.add(
                        UserNotification(
                            user=user,
                            text=f"New {target.__class__.__name__.lower()} on GcnEvent *{target.dateobs}*",
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
                                text=f"New observation plan submission for GcnEvent *{localization.dateobs}* by *{instrument.name}*",
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
                                text=f"New follow-up submission for object *{target.followup_request.obj_id}* by *{instrument.name}*",
                                url=f"/source/{target.followup_request.obj_id}",
                            )
                        )

                else:
                    session.add(
                        UserNotification(
                            user=user,
                            text=f"New {target.__class__.__name__.lower()} on your favorite source *{target.obj_id}*",
                            url=f"/source/{target.obj_id}",
                        )
                    )
                ws_flow.push(user.id, "skyportal/FETCH_NOTIFICATIONS")

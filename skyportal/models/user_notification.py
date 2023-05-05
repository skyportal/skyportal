__all__ = ['UserNotification']

import asyncio
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from sqlalchemy import event, inspect
import requests
from tornado.ioloop import IOLoop

from baselayer.app.models import Base, AccessibleIfUserMatches
from baselayer.app.env import load_env
from baselayer.log import make_log

from .analysis import ObjAnalysis
from .classification import Classification
from .localization import Localization
from .spectrum import Spectrum
from .comment import Comment
from .facility_transaction import FacilityTransaction
from .followup_request import FollowupRequest
from .observation_plan import EventObservationPlan
from .group import GroupAdmissionRequest


_, cfg = load_env()

log = make_log('notifications')


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


@event.listens_for(Classification, 'after_insert')
@event.listens_for(Spectrum, 'after_insert')
@event.listens_for(Comment, 'after_insert')
@event.listens_for(FacilityTransaction, 'after_insert')
@event.listens_for(GroupAdmissionRequest, 'after_insert')
@event.listens_for(ObjAnalysis, 'after_update')
@event.listens_for(EventObservationPlan, 'after_insert')
@event.listens_for(FollowupRequest, 'after_update')
@event.listens_for(Localization, 'after_insert')
def add_user_notifications(mapper, connection, target):

    # Add front-end user notifications
    @event.listens_for(inspect(target).session, "after_commit", once=True)
    def receive_after_commit(session):

        if target is None:
            return

        target_class_name = target.__class__.__name__
        try:
            target_id = target.id
        except Exception:
            return

        request_body = {
            'target_class_name': target_class_name,
            'target_id': target_id,
        }

        notifications_microservice_url = (
            f'http://127.0.0.1:{cfg["ports.notification_queue"]}'
        )

        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        IOLoop.current().run_in_executor(
            None,
            lambda: post_notification(
                notifications_microservice_url, request_body, timeout=30
            ),
        )


def post_notification(notifications_microservice_url, request_body, timeout=2):

    resp = requests.post(
        notifications_microservice_url, json=request_body, timeout=timeout
    )
    if resp.status_code != 200:
        log(
            f'Notification request failed for {request_body["target_class_name"]} with ID {request_body["target_id"]}: {resp.content}'
        )

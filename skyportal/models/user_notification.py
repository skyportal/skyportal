__all__ = ["UserNotification"]

import asyncio

import sqlalchemy as sa
from sqlalchemy import event, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from tornado.ioloop import IOLoop

from baselayer.app.models import AccessibleIfUserMatches, Base

from ..utils.notifications import post_notification
from .analysis import ObjAnalysis
from .classification import Classification
from .comment import Comment
from .facility_transaction import FacilityTransaction
from .followup_request import FollowupRequest
from .group import GroupAdmissionRequest
from .observation_plan import EventObservationPlan
from .spectrum import Spectrum


class UserNotification(Base):
    read = update = delete = AccessibleIfUserMatches("user")

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

    # Out-of-process delivery (SMS/email/Slack/etc.) is dispatched by the
    # notification_queue service via a DB-backed work queue. Notifications that
    # do not need external delivery (e.g., reminders that just push the
    # frontend) leave delivery_status NULL so the dispatcher ignores them.
    delivery_status = sa.Column(
        sa.Enum("pending", "sent", "failed", name="notification_delivery_status"),
        nullable=True,
        index=True,
        doc=(
            "Out-of-process delivery state. NULL means no external delivery "
            "is requested (frontend-only). 'pending' rows are claimed by the "
            "notification_queue dispatcher via FOR UPDATE SKIP LOCKED."
        ),
    )

    delivery_payload = sa.Column(
        JSONB,
        nullable=True,
        doc=(
            "Snapshot of the dispatch context (user preferences + rendered "
            "content) captured when the notification was enqueued. Consumed "
            "by the notification_queue dispatcher; opaque elsewhere."
        ),
    )


@event.listens_for(Classification, "after_insert")
@event.listens_for(Spectrum, "after_insert")
@event.listens_for(Comment, "after_insert")
@event.listens_for(FacilityTransaction, "after_insert")
@event.listens_for(GroupAdmissionRequest, "after_insert")
@event.listens_for(ObjAnalysis, "after_update")
@event.listens_for(EventObservationPlan, "after_insert")
@event.listens_for(FollowupRequest, "after_update")
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
            "target_class_name": target_class_name,
            "target_id": target_id,
        }

        try:
            loop = asyncio.get_event_loop()
        except Exception:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        IOLoop.current().run_in_executor(
            None,
            lambda: post_notification(request_body, timeout=30),
        )

__all__ = ['WebhookMixin']

import uuid

import sqlalchemy as sa

from baselayer.app.env import load_env

from ..enum_types import (
    allowed_webbook_status_types,
    WEBHOOK_STATUS_TYPES,
)

_, cfg = load_env()


class WebhookMixin:
    invalid_after = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now() + sa.text('INTERVAL \'1 DAY\''),
        doc='Time after which the webhook is invalid. Default: 1 day from now.',
    )

    token = sa.Column(
        sa.String,
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4()),
        doc='Unique identifier for this webhook.',
    )

    handled_by_url = sa.Column(
        sa.String,
        nullable=False,
        doc='url for internal API to handle the incoming callback.',
    )

    status = sa.Column(
        allowed_webbook_status_types,
        nullable=False,
        doc=(
            f'''Status of the Webhook. One of: {', '.join(f"'{t}'" for t in WEBHOOK_STATUS_TYPES)}.'''
        ),
    )

    duration = sa.Column(
        sa.Float,
        nullable=True,
        doc="How long did this take to run and return this webhook?",
    )

    last_activity = sa.Column(
        sa.DateTime,
        nullable=True,
        default=sa.func.now(),
        doc="When was the last time this webhook was accessed?",
    )

    status_message = sa.Column(
        sa.String, nullable=True, doc="A message describing the status of the webhook."
    )

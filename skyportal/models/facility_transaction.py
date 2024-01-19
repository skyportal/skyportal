__all__ = ['FacilityTransaction', 'FacilityTransactionRequest']

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class FacilityTransaction(Base):
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC time this FacilityTransaction was created.",
    )

    request = sa.Column(psql.JSONB, doc='Serialized HTTP request.')
    response = sa.Column(psql.JSONB, doc='Serialized HTTP response.')

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc="The ID of the FollowupRequest this message pertains to.",
    )

    followup_request = relationship(
        'FollowupRequest',
        back_populates='transactions',
        doc="The FollowupRequest this message pertains to.",
    )

    observation_plan_request_id = sa.Column(
        sa.ForeignKey('observationplanrequests.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc="The ID of the ObservationPlanRequest this message pertains to.",
    )

    observation_plan_request = relationship(
        'ObservationPlanRequest',
        back_populates='transactions',
        doc='The ObservationPlanRequest this message pertains to.',
        passive_deletes=True,
    )

    initiator_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc='The ID of the User who initiated the transaction.',
    )
    initiator = relationship(
        'User',
        back_populates='transactions',
        doc='The User who initiated the transaction.',
        foreign_keys="FacilityTransaction.initiator_id",
    )


class FacilityTransactionRequest(Base):
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC time this FacilityTransactionRequest was created.",
    )

    last_query = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC time this FacilityTransactionRequest was last queried.",
    )

    method = sa.Column(
        sa.String,
        nullable=False,
        doc="HTTP method. Options include GET, POST, PUT, DELETE, etc.",
    )

    endpoint = sa.Column(
        sa.String,
        nullable=False,
        doc="Endpoint for the transaction request",
    )

    data = sa.Column(psql.JSONB, doc='Data to post.')
    params = sa.Column(psql.JSONB, doc='URL parameters, in get.')
    headers = sa.Column(psql.JSONB, doc='Request headers.')

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc="The ID of the FollowupRequest this message pertains to.",
    )

    followup_request = relationship(
        'FollowupRequest',
        back_populates='transaction_requests',
        doc="The FollowupRequest this message pertains to.",
    )

    observation_plan_request_id = sa.Column(
        sa.ForeignKey('observationplanrequests.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc="The ID of the ObservationPlanRequest this message pertains to.",
    )

    observation_plan_request = relationship(
        'ObservationPlanRequest',
        back_populates='transaction_requests',
        doc='The ObservationPlanRequest this message pertains to.',
        passive_deletes=True,
    )

    initiator_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
        doc='The ID of the User who initiated the transaction.',
    )
    initiator = relationship(
        'User',
        back_populates='transaction_requests',
        doc='The User who initiated the transaction.',
        foreign_keys="FacilityTransactionRequest.initiator_id",
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the request.",
    )

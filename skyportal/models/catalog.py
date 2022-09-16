__all__ = [
    'CatalogQuery',
]

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects import postgresql as psql

from baselayer.app.models import (
    Base,
    join_model,
    User,
    AccessibleIfRelatedRowsAreAccessible,
    AccessibleIfUserMatches,
    CustomUserAccessControl,
)

from .group import Group
from .followup_request import updatable_by_token_with_listener_acl


class CatalogQuery(Base):
    """A request to an external catalog."""

    __tablename__ = 'catalog_queries'

    # TODO: Make read-accessible via target groups
    create = read = AccessibleIfRelatedRowsAreAccessible(allocation="read")
    update = delete = (
        (
            AccessibleIfUserMatches('allocation.group.users')
            | AccessibleIfUserMatches('requester')
        )
        & read
    ) | CustomUserAccessControl(updatable_by_token_with_listener_acl)

    requester_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="ID of the User who requested the catalog query.",
    )

    requester = relationship(
        User,
        back_populates='catalog_queries',
        doc="The User who requested the catalog query.",
        foreign_keys=[requester_id],
    )

    payload = sa.Column(
        psql.JSONB,
        nullable=False,
        doc="Content of the catalog query.",
    )

    status = sa.Column(
        sa.String(),
        nullable=False,
        default="pending submission",
        index=True,
        doc="The status of the query.",
    )

    allocation_id = sa.Column(
        sa.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False, index=True
    )
    allocation = relationship('Allocation', back_populates='catalog_queries')

    target_groups = relationship(
        'Group',
        secondary='catalog_queries_groups',
        passive_deletes=True,
        doc='Groups to share the resulting data from this catalog query with.',
        overlaps='groups',
    )


CatalogQueryTargetGroup = join_model(
    'catalog_queries_groups',
    CatalogQuery,
    Group,
    new_name='CatalogQueryTargetGroup',
    overlaps='target_groups',
)
CatalogQueryTargetGroup.create = (
    CatalogQueryTargetGroup.update
) = CatalogQueryTargetGroup.delete = (
    AccessibleIfUserMatches('defaultobservationplanrequest.requester')
    & CatalogQueryTargetGroup.read
)

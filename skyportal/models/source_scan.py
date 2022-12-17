__all__ = ['SourceScan']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from datetime import datetime

from baselayer.app.models import Base, AccessibleIfRelatedRowsAreAccessible

from .group import accessible_by_group_members


class SourceScan(Base):
    """Record of an instance in which a Source was scanned (as noted
    by a checkmark from the User on the Source page).
    """

    create = (
        read
    ) = (
        update
    ) = delete = accessible_by_group_members & AccessibleIfRelatedRowsAreAccessible(
        group='read'
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True,
        doc="Object ID for which the scanning was registered.",
    )
    scanner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User that made this SourceScan",
    )
    scanner = relationship('User', doc="The User that scanned this source.")
    group_id = sa.Column(
        sa.ForeignKey('groups.id', ondelete='CASCADE'),
        index=True,
        doc='The ID of the Group the scan is associated with.',
        nullable=False,
    )
    group = relationship(
        'Group',
        back_populates='source_scans',
        doc='The Group the scan is associated with.',
    )
    created_at = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="UTC timestamp of the scanning.",
    )

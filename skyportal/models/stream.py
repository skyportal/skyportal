__all__ = [
    "Stream",
    "StreamUser",
    "StreamPhotometry",
    "StreamPhotometricSeries",
    "StreamInvitation",
    "StreamSharingService",
]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    User,
    UserAccessControl,
    join_model,
    restricted,
)

from .group import Group, accessible_by_stream_members
from .invitation import Invitation
from .photometric_series import PhotometricSeries
from .photometry import Photometry
from .sharing_service import SharingService


def stream_read_access_logic(cls, user_or_token):
    """A stream is readable by system admins, by its members, and (so they can
    be discovered and self-joined) by everyone if it is an auto-join stream."""
    if user_or_token.is_admin:
        return sa.select(cls)
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    return sa.select(cls).where(
        sa.or_(
            cls.auto_join.is_(True),
            cls.id.in_(
                sa.select(StreamUser.stream_id).where(StreamUser.user_id == user_id)
            ),
        )
    )


class Stream(Base):
    """A data stream producing alerts that can be programmatically filtered
    using a Filter."""

    read = CustomUserAccessControl(stream_read_access_logic)
    create = update = delete = restricted

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Stream name.")
    altdata = sa.Column(
        JSONB,
        nullable=True,
        doc="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )
    auto_join = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        default=False,
        doc="Boolean indicating whether any user may add themselves to this "
        "stream. Auto-join streams are visible to all users.",
    )

    groups = relationship(
        "Group",
        secondary="group_streams",
        back_populates="streams",
        passive_deletes=True,
        doc="The Groups with access to this Stream.",
    )
    users = relationship(
        "User",
        secondary="stream_users",
        back_populates="streams",
        passive_deletes=True,
        doc="The users with access to this stream.",
    )
    filters = relationship(
        "Filter",
        back_populates="stream",
        passive_deletes=True,
        doc="The filters with access to this stream.",
    )
    photometry = relationship(
        "Photometry",
        secondary="stream_photometry",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="The photometry associated with this stream.",
    )

    photometric_series = relationship(
        "PhotometricSeries",
        secondary="stream_photometric_series",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Photometric series associated with this stream.",
    )

    sharing_services = relationship(
        "SharingService",
        secondary="stream_sharingservices",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Sharing services associated with this stream",
    )


def stream_delete_logic(cls, user_or_token):
    """Can only delete a stream from a user if none of the user's groups
    require that stream for membership.
    """
    from .group_joins import GroupStream

    return (
        sa.select(cls)
        .where(sa.literal(user_or_token.is_admin))
        .join(User, cls.user)
        .outerjoin(Group, User.groups)
        .outerjoin(
            GroupStream,
            sa.and_(
                GroupStream.group_id == Group.id,
                GroupStream.stream_id == cls.stream_id,
            ),
        )
        .group_by(cls.id)
        # no OR here because Users will always be a member of at least one
        # group -- their single user group.
        .having(sa.func.bool_and(GroupStream.stream_id.is_(None)))
    )


StreamUser = join_model("stream_users", Stream, User)
StreamUser.__doc__ = "Join table mapping Streams to Users."
StreamUser.create = restricted
# only system admins can modify user stream permissions
# only system admins can modify user stream permissions
StreamUser.delete = CustomUserAccessControl(stream_delete_logic)

StreamPhotometry = join_model(
    "stream_photometry", Stream, Photometry, index_created_at=False, composite_pk=True
)
StreamPhotometry.__doc__ = "Join table mapping Streams to Photometry."
StreamPhotometry.create = accessible_by_stream_members

StreamPhotometricSeries = join_model(
    "stream_photometric_series", Stream, PhotometricSeries
)
StreamPhotometricSeries.__doc__ = "Join table mapping Streams to PhotometricSeries."
StreamPhotometricSeries.create = accessible_by_stream_members

StreamInvitation = join_model("stream_invitations", Stream, Invitation)

StreamSharingService = join_model(
    "stream_sharingservices",
    Stream,
    SharingService,
    column_2="sharing_service_id",
    overlaps="sharing_services",
)
StreamSharingService.__doc__ = "Join table mapping Streams to SharingServices."
StreamSharingService.create = accessible_by_stream_members

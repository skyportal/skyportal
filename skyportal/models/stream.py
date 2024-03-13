__all__ = [
    'Stream',
    'StreamUser',
    'StreamPhotometry',
    'StreamPhotometricSeries',
    'StreamInvitation',
]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    AccessibleIfUserMatches,
    Base,
    CustomUserAccessControl,
    DBSession,
    User,
    join_model,
    restricted,
)

from .group import Group, accessible_by_stream_members
from .invitation import Invitation
from .photometric_series import PhotometricSeries
from .photometry import Photometry
from .tns import TNSRobot


class Stream(Base):
    """A data stream producing alerts that can be programmatically filtered
    using a Filter."""

    read = AccessibleIfUserMatches('users')
    create = update = delete = restricted

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Stream name.")
    altdata = sa.Column(
        JSONB,
        nullable=True,
        doc="Misc. metadata stored in JSON format, e.g. "
        "`{'collection': 'ZTF_alerts', selector: [1, 2]}`",
    )

    groups = relationship(
        'Group',
        secondary='group_streams',
        back_populates='streams',
        passive_deletes=True,
        doc="The Groups with access to this Stream.",
    )
    users = relationship(
        'User',
        secondary='stream_users',
        back_populates='streams',
        passive_deletes=True,
        doc="The users with access to this stream.",
    )
    filters = relationship(
        'Filter',
        back_populates='stream',
        passive_deletes=True,
        doc="The filters with access to this stream.",
    )
    photometry = relationship(
        "Photometry",
        secondary="stream_photometry",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='The photometry associated with this stream.',
    )

    photometric_series = relationship(
        "PhotometricSeries",
        secondary="stream_photometric_series",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Photometric series associated with this stream.',
    )

    tnsrobots = relationship(
        "TNSRobot",
        secondary="stream_tnsrobots",
        back_populates="streams",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="TNS robots associated with this stream, used for auto-reporting.",
    )


def stream_delete_logic(cls, user_or_token):
    """Can only delete a stream from a user if none of the user's groups
    require that stream for membership.
    """
    from .group_joins import GroupStream

    return (
        DBSession()
        .query(cls)
        .filter(sa.literal(user_or_token.is_admin))
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


StreamUser = join_model('stream_users', Stream, User)
StreamUser.__doc__ = "Join table mapping Streams to Users."
StreamUser.create = restricted
# only system admins can modify user stream permissions
# only system admins can modify user stream permissions
StreamUser.delete = CustomUserAccessControl(stream_delete_logic)

StreamPhotometry = join_model("stream_photometry", Stream, Photometry)
StreamPhotometry.__doc__ = "Join table mapping Streams to Photometry."
StreamPhotometry.create = accessible_by_stream_members

StreamPhotometricSeries = join_model(
    "stream_photometric_series", Stream, PhotometricSeries
)
StreamPhotometricSeries.__doc__ = "Join table mapping Streams to PhotometricSeries."
StreamPhotometricSeries.create = accessible_by_stream_members

StreamInvitation = join_model('stream_invitations', Stream, Invitation)

StreamTNSRobot = join_model("stream_tnsrobots", Stream, TNSRobot)
StreamTNSRobot.__doc__ = "Join table mapping Streams to TNSRobots."
StreamTNSRobot.create = accessible_by_stream_members

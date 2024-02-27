__all__ = [
    'TNSRobot',
    'TNSRobotCoauthor',
    'TNSRobotGroup',
    'TNSRobotGroupAutoreporter',
    'TNSRobotSubmission',
]

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship, column_property
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType

from baselayer.app.env import load_env
from baselayer.app.models import (
    Base,
    UserAccessControl,
    CustomUserAccessControl,
)
from .group import Group, GroupUser

_, cfg = load_env()


class TNSRobot(Base):
    """A TNS robot entry."""

    bot_name = sa.Column(sa.String, doc="Name of the TNS bot.", nullable=False)
    bot_id = sa.Column(sa.Integer, doc="ID of the TNS bot.", nullable=False)
    source_group_id = sa.Column(
        sa.Integer, doc="Source group ID of the TNS bot.", nullable=False
    )

    _altdata = sa.Column(
        EncryptedType(JSONType, cfg['app.secret_key'], AesEngine, 'pkcs5')
    )

    instruments = relationship(
        "Instrument",
        secondary="instrument_tnsrobots",
        back_populates="tnsrobots",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Instruments to restrict the photometry to when reporting.",
    )

    streams = relationship(
        "Stream",
        secondary="stream_tnsrobots",
        back_populates="tnsrobots",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams to restrict the photometry to when reporting.",
    )

    acknowledgments = sa.Column(
        sa.String, nullable=False, doc="Acknowledgments to use for this robot."
    )

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        else:
            return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        self._altdata = value

    groups = relationship(
        'TNSRobotGroup',
        back_populates='tnsrobot',
        passive_deletes=True,
        doc='Groups associated with this TNSRobot.',
    )

    coauthors = relationship(
        'TNSRobotCoauthor',
        back_populates='tnsrobot',
        passive_deletes=True,
        doc='Coauthors associated with this TNSRobot.',
    )


# we want a unique constraint on the bot_name, bot_id, source_group_id columns
TNSRobot.__table_args__ = (
    sa.UniqueConstraint('bot_name', 'bot_id', 'source_group_id'),
)


class TNSRobotCoauthor(Base):
    """Coauthors for TNS auto-reports."""

    __tablename__ = 'tnsrobot_coauthors'

    tnsrobot_id = sa.Column(
        sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False
    )
    user_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    tnsrobot = relationship(
        'TNSRobot',
        back_populates='coauthors',
        doc='The TNSRobot associated with this mapper.',
    )


# unique constraint on the tnsrobot_id and user_id columns
TNSRobotCoauthor.__table_args__ = (sa.UniqueConstraint('tnsrobot_id', 'user_id'),)


class TNSRobotGroup(Base):
    """Mapper between TNSRobots and Groups."""

    __tablename__ = 'tnsrobots_groups'

    tnsrobot_id = sa.Column(
        sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False
    )
    group_id = sa.Column(sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)

    owner = sa.Column(sa.Boolean, nullable=False, default=False)
    auto_report = sa.Column(sa.Boolean, nullable=False, default=False)

    tnsrobot = relationship(
        'TNSRobot',
        back_populates='groups',
        doc='The TNSRobot associated with this mapper.',
    )

    group = relationship(
        'Group',
        back_populates='tnsrobots',
        doc='The Group associated with this mapper.',
    )

    autoreporters = relationship(
        'TNSRobotGroupAutoreporter',
        back_populates='tnsrobot_group',
        passive_deletes=True,
        doc='Users associated with this TNSRobotGroup.',
    )


# we want a unique index on the tnsrobot_id and group_id columns
TNSRobotGroup.__table_args__ = (sa.UniqueConstraint('tnsrobot_id', 'group_id'),)


class TNSRobotGroupAutoreporter(Base):
    """Mapper between TNSRobots and Users that are allowed to auto-report."""

    __tablename__ = 'tnsrobot_users'

    tnsrobot_group_id = sa.Column(
        sa.ForeignKey('tnsrobots_groups.id', ondelete='CASCADE'), nullable=False
    )
    group_user_id = sa.Column(
        sa.ForeignKey('group_users.id', ondelete='CASCADE'), nullable=False
    )

    tnsrobot_group = relationship(
        'TNSRobotGroup',
        back_populates='autoreporters',
        doc='The TNSRobot associated with this mapper.',
    )


# we want a unique index on the tnsrobot_id and group_user_id columns
TNSRobotGroupAutoreporter.__table_args__ = (
    sa.UniqueConstraint('tnsrobot_group_id', 'group_user_id'),
)

# we add a method that gives us the user_id from that group_user
TNSRobotGroupAutoreporter.user_id = column_property(
    sa.select(GroupUser.user_id).where(
        GroupUser.id == TNSRobotGroupAutoreporter.group_user_id
    )
)


class TNSRobotSubmission(Base):
    """Objects to be auto-submitted to TNS."""

    # when the autoreporting is activated for a  robot + a group, we'll have a
    # DB trigger run somewhere in the code where users save objects as sources
    # to their group. If saved to a group that has any TNSRobot associated with
    # and the robot has autoreporting activated for that group, then we'll add
    # an entry to this table. This will be used to keep track of which objects
    # need to be autoreported to TNS for a given robot.
    # we also have a status column to keep track of the status of the submission

    __tablename__ = 'tns_submissions'

    tnsrobot_id = sa.Column(
        sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False
    )
    obj_id = sa.Column(sa.ForeignKey('objs.id', ondelete='CASCADE'), nullable=False)
    user_id = sa.Column(sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    custom_reporting_string = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Custom reporting string to use for this submission only.",
    )

    status = sa.Column(sa.String, nullable=False, default='pending')

    archival = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether this is an archival submission or not.",
    )
    archival_comment = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Comment to use for archival submission.",
    )

    submission_id = sa.Column(
        sa.Integer,
        nullable=True,
        default=None,
        doc="ID of the submission returned by TNS.",
    )

    auto_submission = sa.Column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether this submission was auto-requested or not.",
    )

    instrument_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=True,
        default=None,
        doc="Instrument IDs to use for this submission.",
    )

    stream_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=True,
        default=None,
        doc="Stream IDs to use for this submission.",
    )

    tnsrobot = relationship(
        'TNSRobot',
        back_populates='submissions',
        doc='The TNSRobot associated with this mapper.',
    )

    obj = relationship(
        'Obj',
        back_populates='tns_submissions',
        doc='The Obj associated with this mapper.',
    )

    user = relationship(
        'User',
        back_populates='tns_submissions',
        doc='The User associated with this mapper.',
    )


TNSRobot.submissions = relationship(
    'TNSRobotSubmission',
    back_populates='tnsrobot',
    passive_deletes=True,
    doc='Auto-submissions associated with this TNSRobot.',
)


def tnsrobot_create_read_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read TNSRobots that are associated with groups
        # to which they have access
        query = query.join(TNSRobotGroup)
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def tnsrobot_update_delete_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read TNSRobots that are associated with groups
        # to which they have access, and the group is an owner of the robot
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            TNSRobotGroup.owner.is_(True),
        )
    return query


TNSRobot.read = TNSRobot.create = CustomUserAccessControl(
    tnsrobot_create_read_access_logic
)
TNSRobot.update = TNSRobot.delete = CustomUserAccessControl(
    tnsrobot_update_delete_access_logic
)


def tnsrobot_group_read_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read TNSRobotGroups that are associated with groups
        # to which they have access
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def tnsrobot_group_create_update_delete_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # 1. the user has access to the group
        # 2. the user has access to any group that is associated with the robot
        # as an owner
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            TNSRobotGroup.tnsrobot_id.in_(
                sa.select(TNSRobotGroup.tnsrobot_id).where(
                    TNSRobotGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                    TNSRobotGroup.owner.is_(True),
                )
            ),
        )
    return query


TNSRobotGroup.read = CustomUserAccessControl(tnsrobot_group_read_access_logic)
TNSRobotGroup.create = (
    TNSRobotGroup.update
) = TNSRobotGroup.delete = CustomUserAccessControl(
    tnsrobot_group_create_update_delete_access_logic
)


def tnsrobot_user_read_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to read TNSRobotUsers that are associated with groups
        # to which they have access
        query = query.join(TNSRobotGroup)
        query = query.join(Group).join(GroupUser)
        query = query.where(GroupUser.user_id == user_id)
    return query


def tnsrobot_user_create_update_delete_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        # a user should only be able to create/update/delete TNSRobotUsers from TNSRobots that the user has access to
        query = query.join(TNSRobot)
        query = query.join(TNSRobotGroup).join(Group).join(GroupUser)
        query = query.where(GroupUser.user_id == user_id)
    return query


# users should be able to read/create/edit/delete tns submissions only for tns robots they have access to
def tnsrobot_submission_access_logic(cls, user_or_token):
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            TNSRobotSubmission.tnsrobot_id.in_(
                sa.select(TNSRobot.id)
                .join(TNSRobotGroup)
                .join(Group)
                .join(GroupUser)
                .where(GroupUser.user_id == user_id)
            )
        )
    return query


TNSRobotSubmission.read = (
    TNSRobotSubmission.create
) = TNSRobotSubmission.update = TNSRobotSubmission.delete = CustomUserAccessControl(
    tnsrobot_submission_access_logic
)

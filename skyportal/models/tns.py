__all__ = [
    'TNSRobot',
    'TNSRobotCoauthor',
    'TNSRobotGroup',
    'TNSRobotGroupAutoreporter',
    'TNSRobotSubmission',
]

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship, column_property, deferred
from sqlalchemy.dialects import postgresql as psql
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
        sa.String,
        nullable=False,
        server_default="",
        doc="Acknowledgments to use for this robot.",
    )

    report_existing = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="false",
        doc="Whether to still report objects that are already in the TNS, but not reported with this object internal name (i.e., reported by another survey).",
    )

    testing = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default="true",
        doc="If true, robot will not report to TNS and only store the request's payload.",
    )

    photometry_options = sa.Column(
        psql.JSONB,
        nullable=True,
        doc="Photometry options to use for this robot, to make some data optional or mandatory for manual and auto-reporting.",
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


# we want a unique constraint on the bot_name, bot_id, source_group_id, testing columns
# this way you can't have the same bot twice, except for testing
TNSRobot.__table_args__ = (
    sa.UniqueConstraint('bot_name', 'bot_id', 'source_group_id', 'testing'),
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

    __tablename__ = 'tnsrobot_groups'

    tnsrobot_id = sa.Column(
        sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False
    )
    group_id = sa.Column(sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False)

    owner = sa.Column(sa.Boolean, nullable=False, default=False)
    auto_report = sa.Column(sa.Boolean, nullable=False, default=False)
    auto_report_allow_bots = sa.Column(
        sa.Boolean, nullable=False, server_default='false'
    )

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

    __tablename__ = 'tnsrobot_group_users'

    tnsrobot_group_id = sa.Column(
        sa.ForeignKey('tnsrobot_groups.id', ondelete='CASCADE'), nullable=False
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

    __tablename__ = 'tnsrobot_submissions'

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
    custom_remarks_string = sa.Column(
        sa.String,
        nullable=True,
        default=None,
        doc="Custom remarks string to use for this submission only.",
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
        doc="Instrument IDs to use for this submission. If specified, overrides the robot's default instrument IDs.",
    )

    stream_ids = sa.Column(
        sa.ARRAY(sa.Integer),
        nullable=True,
        default=None,
        doc="Stream IDs to use for this submission. If specified, overrides the robot's default stream IDs.",
    )

    photometry_options = sa.Column(
        psql.JSONB,
        nullable=True,
        doc="Photometry options to use for this robot, to make some data optional or mandatory. If specified, overrides the robot's default photometry options.",
    )

    payload = deferred(sa.Column(psql.JSONB, doc='Payload to be sent to TNS.'))
    response = deferred(sa.Column(psql.JSONB, doc='Serialized HTTP response.'))

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


def tnsrobot_read_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobot instances based on user read access."""
    # if the user is a system admin, they can see all TNSRobots
    # otherwise, they can only see TNSRobots that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(TNSRobotGroup)
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            )
        )
    return query


def tnsrobot_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobot instances based on user update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the TNSRobot
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.join(TNSRobotGroup)
        query = query.where(
            TNSRobotGroup.group_id.in_(
                sa.select(GroupUser.group_id).where(GroupUser.user_id == user_id)
            ),
            TNSRobotGroup.owner.is_(True),
        )
    return query


TNSRobot.read = CustomUserAccessControl(tnsrobot_read_access_logic)
TNSRobot.update = TNSRobot.delete = CustomUserAccessControl(
    tnsrobot_update_delete_access_logic
)


def tnsrobot_coauthor_read_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobotCoauthor instances based on user read access."""
    # if the user is a system admin, they can see all TNSRobotCoauthors
    # otherwise, they can only see TNSRobotCoauthors from TNSRobots that are associated with groups they are in
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            TNSRobotCoauthor.tnsrobot_id.in_(
                sa.select(TNSRobotGroup.tnsrobot_id).where(
                    TNSRobotGroup.group_id.in_(
                        sa.select(GroupUser.group_id).where(
                            GroupUser.user_id == user_id
                        )
                    ),
                )
            ),
        )
    return query


def tnsrobot_coauthor_create_update_delete_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobotCoauthor instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the TNSRobot
    user_id = UserAccessControl.user_id_from_user_or_token(user_or_token)
    query = sa.select(cls)
    if not user_or_token.is_system_admin:
        query = query.where(
            TNSRobotCoauthor.tnsrobot_id.in_(
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


TNSRobotCoauthor.read = CustomUserAccessControl(tnsrobot_coauthor_read_access_logic)

TNSRobotCoauthor.create = (
    TNSRobotCoauthor.update
) = TNSRobotCoauthor.delete = CustomUserAccessControl(
    tnsrobot_coauthor_create_update_delete_access_logic
)


def tnsrobot_group_read_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobotGroup instances based on user read access."""
    # if the user is a system admin, they can see all TNSRobotGroups
    # otherwise, they can only see TNSRobotGroups that are associated with groups they are in
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
    """Return a query that filters TNSRobotGroup instances based on user create/update/delete access."""
    # same as read access, but at least one of the groups must be an owner of the TNSRobot
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

# for the TNSRobotGroupAutoreporter, we will use the same access logic as for TNSRobotGroup
TNSRobotGroupAutoreporter.read = CustomUserAccessControl(tnsrobot_read_access_logic)
TNSRobotGroupAutoreporter.create = (
    TNSRobotGroupAutoreporter.update
) = TNSRobotGroupAutoreporter.delete = CustomUserAccessControl(
    tnsrobot_update_delete_access_logic
)


def tnsrobot_submission_access_logic(cls, user_or_token):
    """Return a query that filters TNSRobotSubmission instances based on user read/create/update/delete access."""
    # if the user is a system admin, they can create/read/update/delete all TNSRobotSubmissions
    # otherwise, they can do so only using TNSRobots that are associated with groups they are in
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

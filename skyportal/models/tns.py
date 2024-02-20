__all__ = ['TNSRobot', 'TNSRobotCoAuthor', 'TNSRobotGroup', 'TNSRobotSubmission']

import json

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils.types import JSONType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine, EncryptedType

from baselayer.app.env import load_env
from baselayer.app.models import Base

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

    auto_report_instruments = relationship(
        "Instrument",
        secondary="instrument_tnsrobots",
        back_populates="tnsrobots",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Instruments to restrict the photometry to when auto-reporting.",
    )

    auto_report_streams = relationship(
        "Stream",
        secondary="stream_tnsrobots",
        back_populates="tnsrobots",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams to restrict the photometry to when auto-reporting.",
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


class TNSRobotCoAuthor(Base):
    """Mapper between TNSRobots and Users."""

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

    user = relationship(
        'User',
        back_populates='tnsrobots',
        doc='The User associated with this mapper.',
    )


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


class TNSRobotSubmission(Base):
    """Objects to be auto-submitted to TNS."""

    # when the autoreporting is activated for a robot + a group, we'll have a
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


TNSRobot.groups = relationship(
    'TNSRobotGroup',
    back_populates='tnsrobot',
    passive_deletes=True,
    doc='Groups associated with this TNSRobot.',
)

TNSRobot.coauthors = relationship(
    'TNSRobotCoAuthor',
    back_populates='tnsrobot',
    passive_deletes=True,
    doc='Co-authors associated with this TNSRobot.',
)

TNSRobot.submissions = relationship(
    'TNSRobotSubmission',
    back_populates='tnsrobot',
    passive_deletes=True,
    doc='Auto-submissions associated with this TNSRobot.',
)

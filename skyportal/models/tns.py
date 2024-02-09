__all__ = ['TNSRobot', 'TNSRobotCoAuthor', 'TNSRobotGroup']

import json

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
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

    auto_report_group_ids = sa.Column(
        ARRAY(sa.Integer),
        comment='List of group IDs to report from',
        nullable=True,
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

    @property
    def altdata(self):
        if self._altdata is None:
            return {}
        else:
            return json.loads(self._altdata)

    @altdata.setter
    def altdata(self, value):
        self._altdata = value

    tnsrobots_groups = relationship(
        'TNSRobotGroup',
        back_populates='tnsrobot',
        passive_deletes=True,
        doc='Groups associated with this TNSRobot.',
    )

class TNSRobotCoAuthor(Base):
    """Mapper between TNSRobots and Users."""

    __tablename__ = 'tnsrobot_coauthors'

    tnsrobot_id = sa.Column(sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False)
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

    tnsrobot_id = sa.Column(sa.ForeignKey('tnsrobots.id', ondelete='CASCADE'), nullable=False)
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
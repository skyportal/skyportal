__all__ = ['MMADetector']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    DBSession,
    join_model,
    public,
)

from ..enum_types import (
    mma_detector_types,
)

from .gcn import GcnEvent

from baselayer.app.env import load_env

_, cfg = load_env()


def manage_mmadetector_access_logic(cls, user_or_token):
    if user_or_token.is_system_admin:
        return DBSession().query(cls)
    elif 'Manage allocations' in [acl.id for acl in user_or_token.acls]:
        return DBSession().query(cls)
    else:
        # return an empty query
        return DBSession().query(cls).filter(cls.id == -1)


class MMADetector(Base):
    """Detector information"""

    read = public
    create = update = delete = CustomUserAccessControl(manage_mmadetector_access_logic)

    name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Unabbreviated facility name (e.g., LIGO Hanford Observatory.",
    )
    nickname = sa.Column(
        sa.String, nullable=False, doc="Abbreviated facility name (e.g., LHO)."
    )

    type = sa.Column(
        mma_detector_types,
        nullable=False,
        doc="MMA detector type, one of gravitational wave, neutrino, or gamma-ray burst.",
    )

    lat = sa.Column(sa.Float, nullable=True, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=True, doc='Longitude in deg.')
    elevation = sa.Column(sa.Float, nullable=True, doc='Elevation in meters.')

    fixed_location = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='true',
        doc="Does this telescope have a fixed location (lon, lat, elev)?",
    )

    events = relationship(
        "GcnEvent",
        secondary="gcnevents_mmadetectors",
        back_populates="detectors",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="GcnEvents associated with this detector.",
    )


GcnEventMMADetector = join_model("gcnevents_mmadetectors", GcnEvent, MMADetector)
GcnEventMMADetector.__doc__ = "Join table mapping GcnEvents to MMADetectors."

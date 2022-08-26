__all__ = ['Interferometer']

import sqlalchemy as sa

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    DBSession,
    public,
)

from baselayer.app.env import load_env

_, cfg = load_env()


def manage_interferometer_access_logic(cls, user_or_token):
    if user_or_token.is_system_admin:
        return DBSession().query(cls)
    elif 'Manage allocations' in [acl.id for acl in user_or_token.acls]:
        return DBSession().query(cls)
    else:
        # return an empty query
        return DBSession().query(cls).filter(cls.id == -1)


class Interferometer(Base):
    """Detector information"""

    read = public
    create = update = delete = CustomUserAccessControl(
        manage_interferometer_access_logic
    )

    name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Unabbreviated facility name (e.g., LIGO Hanford Observatory.",
    )
    nickname = sa.Column(
        sa.String, nullable=False, doc="Abbreviated facility name (e.g., LHO)."
    )
    lat = sa.Column(sa.Float, nullable=False, doc='Latitude in deg.')
    lon = sa.Column(sa.Float, nullable=False, doc='Longitude in deg.')

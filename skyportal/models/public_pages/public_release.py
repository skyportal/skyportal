__all__ = ['PublicRelease']

import sqlalchemy as sa
from baselayer.app.models import Base


class PublicRelease(Base):
    """Public release of a group of sources."""

    id = sa.Column(sa.Integer, primary_key=True)

    name = sa.Column(
        sa.String,
        nullable=False,
        doc="Name of the public release",
    )

    description = sa.Column(
        sa.String,
        nullable=False,
        doc="Description of the public release",
    )

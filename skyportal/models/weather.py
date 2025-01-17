__all__ = ["Weather"]

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from baselayer.app.models import Base, public


class Weather(Base):
    update = public

    weather_info = sa.Column(JSONB, doc="Latest weather information.")
    retrieved_at = sa.Column(
        sa.DateTime, doc="UTC time at which the weather was last retrieved."
    )
    telescope_id = sa.Column(
        sa.ForeignKey("telescopes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
        doc="ID of the associated Telescope.",
    )
    telescope = relationship(
        "Telescope",
        foreign_keys=[telescope_id],
        uselist=False,
        doc="The associated Telescope.",
    )

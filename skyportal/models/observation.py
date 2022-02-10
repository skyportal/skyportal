__all__ = ['ExecutedObservation']

import sqlalchemy as sa
from sqlalchemy.orm import relationship

from baselayer.app.models import Base


class ExecutedObservation(Base):
    """Observation information, including the field ID, exposure time, and
    filter."""

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        'Instrument',
        back_populates='observations',
        doc="The Instrument that executed the observation.",
    )

    instrument_field_id = sa.Column(
        sa.ForeignKey("instrumentfields.id", ondelete="CASCADE"),
        primary_key=True,
        doc='Field ID',
    )

    observation_id = sa.Column(
        sa.Integer, primary_key=True, doc='Observation ID supplied by instrument'
    )

    obstime = sa.Column(sa.DateTime, doc='Exposure timestamp')

    field = relationship("InstrumentField")

    filt = sa.Column(sa.String, doc='Filter')

    exposure_time = sa.Column(
        sa.Integer, nullable=False, doc='Exposure time in seconds'
    )

    airmass = sa.Column(sa.Float, doc='Airmass')

    seeing = sa.Column(sa.Float, doc='Seeing')

    limmag = sa.Column(sa.Float, doc='Limiting magnitude')

    processed_fraction = sa.Column(
        sa.Float, nullable=False, comment='fraction of image processed successfully'
    )

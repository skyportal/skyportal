__all__ = ['ExecutedObservation', 'QueuedObservation']


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


class QueuedObservation(Base):
    """Observation queue information, including the field ID, exposure time, and
    filter."""

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        'Instrument',
        back_populates='queued_observations',
        doc="The Instrument that executed the observation.",
    )

    instrument_field_id = sa.Column(
        sa.ForeignKey("instrumentfields.id", ondelete="CASCADE"),
        primary_key=True,
        doc='Field ID',
    )

    queue_name = sa.Column(sa.String, doc='Queue name')

    obstime = sa.Column(sa.DateTime, doc='Queued timestamp')

    validity_window_start = sa.Column(
        sa.DateTime,
        doc='Start of validity window',
    )

    validity_window_end = sa.Column(
        sa.DateTime,
        doc='End of validity window',
    )

    field = relationship("InstrumentField")

    filt = sa.Column(sa.String, doc='Filter')

    exposure_time = sa.Column(
        sa.Integer, nullable=False, doc='Exposure time in seconds'
    )

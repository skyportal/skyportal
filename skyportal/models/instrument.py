__all__ = ['Instrument', 'InstrumentField', 'InstrumentFieldTile']

import re

import healpix_alchemy
import sqlalchemy as sa
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred

from baselayer.app.models import Base, restricted

from skyportal import facility_apis

from ..enum_types import (
    instrument_types,
    allowed_bandpasses,
    listener_classnames,
    api_classnames,
)


class ArrayOfEnum(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)

    def result_processor(self, dialect, coltype):
        super_rp = super().result_processor(dialect, coltype)

        def handle_raw_string(value):
            if value is None or value == '{}':  # 2nd case, empty array
                return []
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",")

        def process(value):
            return super_rp(handle_raw_string(value))

        return process


class Instrument(Base):
    """An instrument attached to a telescope."""

    create = restricted

    name = sa.Column(sa.String, unique=True, nullable=False, doc="Instrument name.")
    type = sa.Column(
        instrument_types,
        nullable=False,
        doc="Instrument type, one of Imager, Spectrograph, or Imaging Spectrograph.",
    )

    band = sa.Column(
        sa.String,
        doc="The spectral band covered by the instrument " "(e.g., Optical, IR).",
    )
    telescope_id = sa.Column(
        sa.ForeignKey('telescopes.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="The ID of the Telescope that hosts the Instrument.",
    )
    telescope = relationship(
        'Telescope',
        back_populates='instruments',
        doc="The Telescope that hosts the Instrument.",
    )

    photometry = relationship(
        'Photometry',
        back_populates='instrument',
        passive_deletes=True,
        doc="The Photometry produced by this instrument.",
    )
    spectra = relationship(
        'Spectrum',
        back_populates='instrument',
        passive_deletes=True,
        doc="The Spectra produced by this instrument.",
    )

    # can be [] if an instrument is spec only
    filters = sa.Column(
        ArrayOfEnum(allowed_bandpasses),
        nullable=False,
        default=[],
        doc='List of filters on the instrument (if any).',
    )

    allocations = relationship(
        'Allocation',
        back_populates="instrument",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
    )
    observing_runs = relationship(
        'ObservingRun',
        back_populates='instrument',
        passive_deletes=True,
        doc="List of ObservingRuns on the Instrument.",
    )

    api_classname = sa.Column(
        api_classnames, nullable=True, doc="Name of the instrument's API class."
    )

    api_classname_obsplan = sa.Column(
        api_classnames,
        nullable=True,
        doc="Name of the instrument's ObservationPlan API class.",
    )

    listener_classname = sa.Column(
        listener_classnames,
        nullable=True,
        doc="Name of the instrument's listener class.",
    )

    observations = relationship(
        'ExecutedObservation',
        back_populates='instrument',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The ExecutedObservations by this instrument.",
    )

    queued_observations = relationship(
        'QueuedObservation',
        back_populates='instrument',
        cascade='save-update, merge, refresh-expire, expunge',
        passive_deletes=True,
        doc="The QueuedObservations for this instrument.",
    )

    treasuremap_id = sa.Column(
        sa.Integer,
        nullable=True,
        doc="treasuremap.space API ID for this instrument",
    )

    tns_id = sa.Column(
        sa.Integer,
        nullable=True,
        doc="TNS API ID for this instrument",
    )

    region = deferred(
        sa.Column(
            sa.String, nullable=True, doc="Instrument astropy.regions representation."
        )
    )

    @property
    def does_spectroscopy(self):
        """Return a boolean indicating whether the instrument is capable of
        performing spectroscopy."""
        return 'spec' in self.type

    @property
    def does_imaging(self):
        """Return a boolean indicating whether the instrument is capable of
        performing imaging."""
        return 'imag' in self.type

    @property
    def api_class(self):
        return getattr(facility_apis, self.api_classname)

    @property
    def api_class_obsplan(self):
        return getattr(facility_apis, self.api_classname_obsplan)

    @property
    def listener_class(self):
        return getattr(facility_apis, self.listener_classname)

    fields = relationship("InstrumentField")
    tiles = relationship("InstrumentFieldTile")
    plans = relationship("EventObservationPlan")


class InstrumentField(Base):
    """A multi-order healpix representation of a telescope's field shape,
    as represented by many InstrumentFieldTiles."""

    tile_class = lambda: InstrumentFieldTile  # pylint: disable=E731 # noqa

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        "Instrument",
        foreign_keys=instrument_id,
        doc="The Instrument that this field belongs to",
    )

    field_id = sa.Column(
        sa.Integer,
        sa.Sequence('seq_field_id', start=1, increment=1),
        autoincrement=True,
        index=True,
        doc='The Field ID for the tile (can be repeated between instruments).',
    )

    ra = sa.Column(
        sa.Float,
        doc='The mid-point right ascension for the tile [degrees].',
        nullable=True,
    )

    dec = sa.Column(
        sa.Float,
        doc='The mid-point declination for the tile [degrees].',
        nullable=True,
    )

    contour = deferred(sa.Column(JSONB, nullable=False, doc='GeoJSON contours'))

    contour_summary = deferred(
        sa.Column(
            JSONB,
            nullable=False,
            doc='GeoJSON contour bounding box for lower memory display',
        )
    )

    tiles = relationship("InstrumentFieldTile")


class InstrumentFieldTile(Base):
    """An individual healpix tile for an InstrumentField."""

    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument ID',
    )

    instrument = relationship(
        "Instrument",
        foreign_keys=instrument_id,
        doc="The Instrument that this tile belongs to",
    )

    instrument_field_id = sa.Column(
        sa.ForeignKey('instrumentfields.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument Field ID',
    )

    field = relationship(
        "InstrumentField",
        foreign_keys=instrument_field_id,
        doc="The Field that this tile belongs to",
    )

    healpix = sa.Column(healpix_alchemy.Tile, primary_key=True, index=True)

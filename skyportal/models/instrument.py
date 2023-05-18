__all__ = ['Instrument', 'InstrumentField', 'InstrumentFieldTile']

import re

from astropy import coordinates as ap_coord
import astroplan
import healpix_alchemy
import numpy as np
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy import cast, event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm import deferred

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    DBSession,
    public,
)

from skyportal import facility_apis

from ..enum_types import (
    instrument_types,
    allowed_bandpasses,
    listener_classnames,
    api_classnames,
)

from baselayer.app.env import load_env
from baselayer.log import make_log

_, cfg = load_env()

log = make_log('model/instrument')


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


def manage_instrument_access_logic(cls, user_or_token):
    if user_or_token.is_system_admin:
        return DBSession().query(cls)
    elif 'Manage allocations' in [acl.id for acl in user_or_token.acls]:
        return DBSession().query(cls)
    else:
        # return an empty query
        return DBSession().query(cls).filter(cls.id == -1)


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
        overlaps='fields',
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

    @property
    def target(self):
        """Representation of the RA and Dec of this Field as an
        astroplan.FixedTarget."""
        coord = ap_coord.SkyCoord(self.ra, self.dec, unit='deg')
        return astroplan.FixedTarget(name=self.id, coord=coord)

    def airmass(self, time, below_horizon=np.inf):
        """Return the airmass of the field at a given time. Uses the Pickering
        (2002) interpolation of the Rayleigh (molecular atmosphere) airmass.

        The Pickering interpolation tends toward 38.7494 as the altitude
        approaches zero.

        Parameters
        ----------
        time : `astropy.time.Time` or list of astropy.time.Time`
            The time or times at which to calculate the airmass
        below_horizon : scalar, Numeric
            Airmass value to assign when an object is below the horizon.
            An object is "below the horizon" when its altitude is less than
            zero degrees.

        Returns
        -------
        airmass : ndarray
           The airmass of the Obj at the requested times
        """

        output_shape = time.shape
        time = np.atleast_1d(time)
        altitude = self.altitude(self.instrument.telescope, time).to('degree').value
        above = altitude > 0

        # use Pickering (2002) interpolation to calculate the airmass
        # The Pickering interpolation tends toward 38.7494 as the altitude
        # approaches zero.
        sinarg = np.zeros_like(altitude)
        airmass = np.ones_like(altitude) * np.inf
        sinarg[above] = altitude[above] + 244 / (165 + 47 * altitude[above] ** 1.1)
        airmass[above] = 1.0 / np.sin(np.deg2rad(sinarg[above]))

        # set objects below the horizon to an airmass of infinity
        airmass[~above] = below_horizon
        airmass = airmass.reshape(output_shape)

        return airmass

    def altitude(self, telescope, time):
        """Return the altitude of the object at a given time.

        Parameters
        ----------
        time : `astropy.time.Time`
            The time or times at which to calculate the altitude

        Returns
        -------
        alt : `astropy.coordinates.AltAz`
           The altitude of the Obj at the requested times
        """

        return self.instrument.telescope.observer.altaz(time, self.target).alt


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
        overlaps='tiles',
    )

    instrument_field_id = sa.Column(
        sa.ForeignKey('instrumentfields.id', ondelete="CASCADE"),
        nullable=False,
        doc='Instrument Field ID',
        index=True,
    )

    field = relationship(
        "InstrumentField",
        foreign_keys=instrument_field_id,
        doc="The Field that this tile belongs to",
        overlaps='tiles',
    )

    healpix = sa.Column(healpix_alchemy.Tile, primary_key=True, index=True)


class Instrument(Base):
    """An instrument attached to a telescope."""

    read = public
    create = update = delete = CustomUserAccessControl(manage_instrument_access_logic)

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
    photometric_series = relationship(
        'PhotometricSeries',
        back_populates='instrument',
        passive_deletes=True,
        doc="PhotometricSeries produced by this instrument.",
    )
    spectra = relationship(
        'Spectrum',
        back_populates='instrument',
        passive_deletes=True,
        doc="The Spectra produced by this instrument.",
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

    sensitivity_data = sa.Column(
        JSONB,
        nullable=True,
        doc="JSON describing the filters on the instrument and the filter's corresponding limiting magnitude and exposure time.",
    )

    configuration_data = sa.Column(
        JSONB,
        nullable=True,
        doc="JSON describing instrument configuration properties such as instrument overhead, filter change time, readout, etc.",
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

    @property
    def number_of_fields(self):
        if not self.has_fields:
            return 0
        stmt = sa.select(InstrumentField).where(
            InstrumentField.instrument_id == self.id
        )
        count_stmt = sa.select(func.count()).select_from(stmt.distinct())
        return DBSession().execute(count_stmt).scalar()

    @property
    def region_summary(self):
        region_summary = ""
        if not self.has_region:
            return region_summary

        if "box" in self.region:
            regionSplit = (
                self.region.split("box")[-1].replace("box(", "").replace(")", "")
            )
            boxSplit = regionSplit.split(",")
            width = float(boxSplit[2])
            height = float(boxSplit[3])
            region_summary = f"Rectangle [width, height]: {width, height}"
        elif "circle" in self.region:
            regionSplit = (
                self.region.split("circle")[-1].replace("circle(", "").replace(")", "")
            )
            circleSplit = regionSplit.split(",")
            radius = float(circleSplit[2])
            region_summary = f"Circle [radius]: {radius}"
        elif "polygon" in self.region:
            region_summary = f"Polygon [num. fields]: {self.region.count('polygon')}"

        return region_summary

    has_fields = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc="Whether the instrument has fields or not.",
    )

    has_region = sa.Column(
        sa.Boolean,
        nullable=False,
        server_default='false',
        doc="Whether the instrument has a region or not.",
    )

    fields = relationship("InstrumentField")
    tiles = relationship("InstrumentFieldTile")
    plans = relationship("EventObservationPlan")


@event.listens_for(Instrument.fields, 'dispose_collection')
def _instrument_fields_dispose_collection(target, collection, collection_adapter):
    target.has_fields = False


@event.listens_for(Instrument.fields, 'init_collection')
def _instrument_fields_init_collection(target, collection, collection_adapter):
    if len(collection) > 0:
        target.has_fields = True
    else:
        target.has_fields = False


@event.listens_for(Instrument.region, 'set')
def _instrument_region_append(target, value, oldvalue, initiator):
    if value is not None and value != "":
        target.has_region = True
    else:
        target.has_region = False


@event.listens_for(Instrument.region, 'remove')
def _instrument_region_remove(target, value, initiator):
    target.has_region = False

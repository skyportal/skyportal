__all__ = ['Photometry', 'PHOT_ZP', 'PHOT_SYS']

import uuid

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import conesearch_alchemy
import numpy as np
import arrow

from baselayer.app.models import Base, accessible_by_owner

from ..enum_types import allowed_bandpasses
from .group import accessible_by_groups_members, accessible_by_streams_members


# In the AB system, a brightness of 23.9 mag corresponds to 1 microJy.
# All DB fluxes are stored in microJy (AB).
PHOT_ZP = 23.9
PHOT_SYS = 'ab'


class Photometry(conesearch_alchemy.Point, Base):
    """Calibrated measurement of the flux of an object through a broadband filter."""

    __tablename__ = 'photometry'

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    mjd = sa.Column(
        sa.Float, nullable=False, doc='MJD of the observations.', index=True
    )
    fluxes = sa.Column(
        sa.Float,
        doc='Fluxes of each observation in µJy. '
        'Corresponds to an AB Zeropoint of 23.9 in all '
        'filters.',
        server_default='NaN',
        nullable=False,
    )

    fluxerr = sa.Column(
        sa.Float, nullable=False, doc='Gaussian errors on the fluxes in µJy.'
    )
    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        doc='Filter with which the observation was taken.',
    )

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    original_user_data = sa.Column(
        JSONB,
        doc='Original data passed by the user '
        'through the PhotometryHandler.POST '
        'API or the PhotometryHandler.PUT '
        'API. The schema of this JSON '
        'validates under either '
        'schema.PhotometryFlux or schema.PhotometryMag '
        '(depending on how the data was passed).',
    )
    altdata = sa.Column(JSONB, doc="Arbitrary metadata in JSON format..")
    upload_id = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="ID of the batch in which this photometric series was uploaded (for bulk deletes).",
    )

    origin = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        index=True,
        doc="Origin from which this Photometry was extracted (if any).",
        server_default='',
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Photometry's Obj.",
    )
    obj = relationship('Obj', back_populates='photometry', doc="The Photometry's Obj.")
    groups = relationship(
        "Group",
        secondary="group_photometry",
        back_populates="photometry",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this Photometry.",
    )
    streams = relationship(
        "Stream",
        secondary="stream_photometry",
        back_populates="photometry",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams associated with this Photometry.",
    )
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that took this Photometry.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='photometry',
        doc="Instrument that took this Photometry.",
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id'), nullable=True, index=True
    )
    followup_request = relationship('FollowupRequest', back_populates='photometry')

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id'), nullable=True, index=True
    )
    assignment = relationship('ClassicalAssignment', back_populates='photometry')

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the photometry.",
    )
    owner = relationship(
        'User',
        back_populates='photometry',
        foreign_keys=[owner_id],
        passive_deletes=True,
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the photometry.",
    )

    @hybrid_property
    def mag(self):
        """The magnitude of the photometry point in the AB system."""
        if not np.isnan(self.flux) and self.flux > 0:
            return -2.5 * np.log10(self.flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_mag(self):
        """The error on the magnitude of the photometry point."""
        if not np.isnan(self.flux) and self.flux > 0 and self.fluxerr > 0:
            return (2.5 / np.log(10)) * (self.fluxerr / self.flux)
        else:
            return None

    @mag.expression
    def mag(cls):
        """The magnitude of the photometry point in the AB system."""
        return sa.case(
            [
                (
                    sa.and_(cls.flux != 'NaN', cls.flux > 0),  # noqa
                    -2.5 * sa.func.log(cls.flux) + PHOT_ZP,
                )
            ],
            else_=None,
        )

    @e_mag.expression
    def e_mag(cls):
        """The error on the magnitude of the photometry point."""
        return sa.case(
            [
                (
                    sa.and_(
                        cls.flux != 'NaN', cls.flux > 0, cls.fluxerr > 0
                    ),  # noqa: E711
                    2.5 / sa.func.ln(10) * cls.fluxerr / cls.flux,
                )
            ],
            else_=None,
        )

    @hybrid_property
    def jd(self):
        """Julian Date of the exposure that produced this Photometry."""
        return self.mjd + 2_400_000.5

    @hybrid_property
    def iso(self):
        """UTC ISO timestamp (ArrowType) of the exposure that produced this Photometry."""
        return arrow.get((self.mjd - 40_587) * 86400.0)

    @iso.expression
    def iso(cls):
        """UTC ISO timestamp (ArrowType) of the exposure that produced this Photometry."""
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd - 40_587) * 86400.0)

    @hybrid_property
    def snr(self):
        """Signal-to-noise ratio of this Photometry point."""
        return (
            self.flux / self.fluxerr
            if not np.isnan(self.flux)
            and not np.isnan(self.fluxerr)
            and self.fluxerr != 0
            else None
        )

    @snr.expression
    def snr(self):
        """Signal-to-noise ratio of this Photometry point."""
        return sa.case(
            [
                (
                    sa.and_(
                        self.flux != 'NaN', self.fluxerr != 'NaN', self.fluxerr != 0
                    ),  # noqa
                    self.flux / self.fluxerr,
                )
            ],
            else_=None,
        )


# Deduplication index. This is a unique index that prevents any photometry
# point that has the same obj_id, instrument_id, origin, mjd, flux error,
# and flux as a photometry point that already exists within the table from
# being inserted into the table. The index also allows fast lookups on this
# set of columns, making the search for duplicates a O(log(n)) operation.

Photometry.__table_args__ = (
    sa.Index(
        'deduplication_index',
        Photometry.obj_id,
        Photometry.instrument_id,
        Photometry.origin,
        Photometry.mjd,
        Photometry.fluxerr,
        Photometry.flux,
        unique=True,
    ),
)


class PhotometricSeries(conesearch_alchemy.Point, Base):
    """
    A series of photometric measurements taken
    of the same object with the same telescope and filter,
    continuously from mjd_start to mjd_end.
    """

    __tablename__ = 'photometric_series'

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    mjd_start = sa.Column(
        sa.Float,
        nullable=False,
        doc='MJD of the start of the observations.',
        index=True,
    )
    mjd_end = sa.Column(
        sa.Float, nullable=False, doc='MJD of the end of the observations.', index=True
    )

    run_object_id = sa.Column(
        sa.String,
        nullable=True,
        doc='Unique identifier of an object inside the set of images out of which the series is generated.',
    )

    run_identifier = sa.Column(
        sa.String,
        nullable=False,
        doc='Unique identifier of the set of images out of which the series is generated.',
    )

    filename = sa.Column(
        sa.String,
        nullable=False,
        doc='Filename of photometric series, where the actual data is saved',
    )

    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        doc='Filter with which the observation was taken.',
    )

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    original_user_data = sa.Column(
        JSONB,
        doc='Original data passed by the user '
        'through the PhotometryHandler.POST '
        'API or the PhotometryHandler.PUT '
        'API. The schema of this JSON '
        'validates under either '
        'schema.PhotometryFlux or schema.PhotometryMag '
        '(depending on how the data was passed).',
    )
    altdata = sa.Column(JSONB, doc="Arbitrary metadata in JSON format..")
    upload_id = sa.Column(
        sa.String,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        doc="ID of the batch in which this Photometry was uploaded (for bulk deletes).",
    )
    origin = sa.Column(
        sa.String,
        nullable=False,
        unique=False,
        index=True,
        doc="Origin from which this photometric series was extracted (if any).",
        server_default='',
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the photometric series' Obj.",
    )
    obj = relationship(
        'Obj', back_populates='photometric_series', doc="The photometric series' Obj."
    )
    groups = relationship(
        "Group",
        secondary="group_photometry",
        back_populates="photometric_series",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Groups that can access this photometric series.",
    )
    streams = relationship(
        "Stream",
        secondary="stream_photometry",
        back_populates="photometric_series",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc="Streams associated with this photometric series.",
    )
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that took this photometric series.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='photometric_series',
        doc="Instrument that took this photometric series.",
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id'), nullable=True, index=True
    )
    followup_request = relationship(
        'FollowupRequest', back_populates='photometric_series'
    )

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id'), nullable=True, index=True
    )
    assignment = relationship(
        'ClassicalAssignment', back_populates='photometric_series'
    )

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the photometric series.",
    )
    owner = relationship(
        'User',
        back_populates='photometry',
        foreign_keys=[owner_id],
        passive_deletes=True,
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the photometric series.",
    )

    @hybrid_property
    def fluxes(self):
        """
        Fluxes of each observation in µJy.
        Corresponds to an AB Zeropoint of 23.9 in all filters.
        """
        df = pd.read_hdf(self.filename, columns=['fluxes'])
        return np.array(df['fluxes'])

    def fluxerr(self):
        """
        Gaussian error on the flux in µJy.
        """
        df = pd.read_hdf(self.filename, columns=['fluxerr'])
        return np.array(df['fluxerr'])

    @hybrid_property
    def mag(self):
        """The magnitude of each point in the AB system."""
        good_points = np.logical_and(np.invert(np.isnan(self.fluxes)), self.flux > 0)
        mag = -2.5 * np.log10(self.fluxes, where=good_points) + PHOT_ZP
        mag[np.invert(good_points)] = np.nan
        # should we turn this into a list and convert the NaNs into Nones?
        return mag

    @hybrid_property
    def magerr(self):
        """The error on the magnitude of each photometry point."""
        good_points = np.logical_and(
            np.invert(np.isnan(self.fluxes)), self.flux > 0, self.fluxerr
        )
        magerr = (2.5 / np.log(10)) * (self.fluxerr / self.fluxes)
        magerr[np.invert(good_points)] = np.nan
        # should we turn this into a list and convert the NaNs into Nones?
        return magerr

    @hybrid_property
    def jd_start(self):
        """Julian Date of the start of the series."""
        return self.mjd_start + 2_400_000.5

    @hybrid_property
    def jd_mid(self):
        """Julian Date of the middle of the series."""
        return self.mjd_mid + 2_400_000.5

    @hybrid_property
    def jd_end(self):
        """Julian Date of the end of the series."""
        return self.mjd_end + 2_400_000.5

    @hybrid_property
    def iso_start(self):
        """UTC ISO timestamp (ArrowType) of the start of the series. """
        return arrow.get((self.mjd_start - 40_587) * 86400.0)

    @iso_start.expression
    def iso_start(cls):
        """UTC ISO timestamp (ArrowType) of the start of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_start - 40_587) * 86400.0)

    @hybrid_property
    def iso_mid(self):
        """UTC ISO timestamp (ArrowType) of the middle of the series. """
        return arrow.get((self.mjd_mid - 40_587) * 86400.0)

    @iso_mid.expression
    def iso_mid(cls):
        """UTC ISO timestamp (ArrowType) of the middle of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_mid - 40_587) * 86400.0)

    @hybrid_property
    def iso_end(self):
        """UTC ISO timestamp (ArrowType) of the end of the series. """
        return arrow.get((self.mjd_end - 40_587) * 86400.0)

    @iso_end.expression
    def iso_end(cls):
        """UTC ISO timestamp (ArrowType) of the end of the series. """
        # converts MJD to unix timestamp
        return sa.func.to_timestamp((cls.mjd_end - 40_587) * 86400.0)

    @hybrid_property
    def snr(self):
        """Signal-to-noise ratio of each measurement"""
        if self.fluxerr is not None and len(self.fluxerr) == len(self.flux):
            err = np.maximum(
                self.fluxerr, self.robust_rms
            )  # assume the worst of the two errors
            return self.flux / err

        return self.flux / self.robust_rms

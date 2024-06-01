__all__ = ['Photometry', 'PHOT_ZP', 'PHOT_SYS']
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

import conesearch_alchemy
import numpy as np
import arrow

from baselayer.app.models import Base, accessible_by_owner
from baselayer.app.env import load_env

from ..enum_types import allowed_bandpasses
from .group import accessible_by_groups_members, accessible_by_streams_members

_, cfg = load_env()

# In the AB system, a brightness of 23.9 mag corresponds to 1 microJy.
# All DB fluxes are stored in microJy (AB).
PHOT_ZP = 23.9
PHOT_SYS = 'ab'

# The minimum signal-to-noise ratio to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


class Photometry(conesearch_alchemy.Point, Base):
    """Calibrated measurement of the flux of an object through a broadband filter."""

    __tablename__ = 'photometry'

    read = (
        accessible_by_groups_members
        | accessible_by_streams_members
        | accessible_by_owner
    )
    update = delete = accessible_by_owner

    mjd = sa.Column(sa.Float, nullable=False, doc='MJD of the observation.', index=True)
    flux = sa.Column(
        sa.Float,
        doc='Flux of the observation in µJy. '
        'Corresponds to an AB Zeropoint of 23.9 in all '
        'filters.',
        server_default='NaN',
        nullable=False,
    )

    fluxerr = sa.Column(
        sa.Float, nullable=False, doc='Gaussian error on the flux in µJy.'
    )
    filter = sa.Column(
        allowed_bandpasses,
        nullable=False,
        doc='Filter with which the observation was taken.',
    )

    ra_unc = sa.Column(sa.Float, doc="Uncertainty of ra position [arcsec]")
    dec_unc = sa.Column(sa.Float, doc="Uncertainty of dec position [arcsec]")

    ref_flux = sa.Column(
        sa.Float,
        nullable=True,
        index=True,
        doc="Reference flux. E.g., "
        "of the source before transient started, "
        "or the mean flux of a variable source.",
    )

    ref_fluxerr = sa.Column(
        sa.Float, nullable=True, doc="Uncertainty on the reference flux."
    )

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

    annotations = relationship(
        'AnnotationOnPhotometry',
        back_populates='photometry',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="AnnotationOnPhotometry.created_at",
        doc="Annotations posted about this photometry.",
    )

    validations = relationship(
        "PhotometryValidation",
        back_populates="photometry",
        passive_deletes=True,
        doc="Photometry validation check.",
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
            (
                sa.and_(cls.flux != 'NaN', cls.flux > 0),  # noqa
                -2.5 * sa.func.log(cls.flux) + PHOT_ZP,
            ),
            else_=None,
        )

    @e_mag.expression
    def e_mag(cls):
        """The error on the magnitude of the photometry point."""
        return sa.case(
            (
                sa.and_(cls.flux != 'NaN', cls.flux > 0, cls.fluxerr > 0),  # noqa: E711
                2.5 / sa.func.ln(10) * cls.fluxerr / cls.flux,
            ),
            else_=None,
        )

    @hybrid_property
    def magref(self):
        """
        Reference magnitude, e.g.,
        the mean magnitude of a variable source,
        or the magnitude of a source before a transient started.
        """
        if self.ref_flux is not None and self.ref_flux > 0:
            return -2.5 * np.log10(self.ref_flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_magref(self):
        """The error on the reference magnitude."""
        if (
            self.ref_flux is not None
            and self.ref_flux > 0
            and self.ref_fluxerr is not None
            and self.ref_fluxerr > 0
        ):
            return (2.5 / np.log(10)) * (self.ref_fluxerr / self.ref_flux)
        else:
            return None

    @magref.expression
    def magref(cls):
        """The magnitude of the photometry point in the AB system."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                ),
                -2.5 * sa.func.log(cls.ref_flux) + PHOT_ZP,
            ),
            else_=None,
        )

    @e_magref.expression
    def e_magref(cls):
        """The error on the magnitude of the photometry point."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                    cls.ref_fluxerr > 0,
                ),  # noqa: E711
                (2.5 / sa.func.ln(10)) * (cls.ref_fluxerr / cls.ref_flux),
            ),
            else_=None,
        )

    @hybrid_property
    def magtot(self):
        """
        Total magnitude, e.g.,
        the combined magnitude of a variable source,
        as opposed to the regular magnitude which may come
        from subtraction images, etc.
        """
        if self.ref_flux is not None and self.ref_flux > 0 and self.flux > 0:
            return -2.5 * np.log10(self.ref_flux + self.flux) + PHOT_ZP
        else:
            return None

    @hybrid_property
    def e_magtot(self):
        """The error on the total magnitude."""
        if (
            self.ref_flux is not None
            and self.ref_flux > 0
            and self.ref_fluxerr is not None
            and self.ref_fluxerr > 0
            and self.flux > 0
            and self.fluxerr > 0
        ):
            return (
                2.5
                / np.log(10)
                * np.sqrt(self.ref_fluxerr**2 + self.fluxerr**2)
                / (self.ref_flux + self.flux)
            )
        else:
            return None

    @magtot.expression
    def magtot(cls):
        """The total magnitude of the photometry point in the AB system."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                    cls.flux != 'NaN',
                    cls.flux > 0,
                ),  # noqa
                -2.5 * sa.func.log(cls.ref_flux + cls.flux) + PHOT_ZP,
            ),
            else_=None,
        )

    @e_magtot.expression
    def e_magtot(cls):
        """The error on the total magnitude of the photometry point."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux is not None,
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                    cls.ref_fluxerr > 0,
                    cls.flux is not None,
                    cls.flux != 'NaN',
                    cls.flux > 0,
                    cls.fluxerr > 0,
                ),  # noqa: E711
                2.5
                / sa.func.ln(10)
                * sa.func.sqrt(
                    sa.func.pow(cls.ref_fluxerr, 2) + sa.func.pow(cls.fluxerr, 2)
                )
                / (cls.ref_flux + cls.flux),
            ),
            else_=None,
        )

    @hybrid_property
    def tot_flux(self):
        """Total flux, e.g., the combined flux of a variable source."""
        if self.ref_flux is not None and self.ref_flux > 0 and self.flux > 0:
            return self.ref_flux + self.flux
        else:
            return None

    @hybrid_property
    def tot_fluxerr(self):
        """The error on the total flux."""
        if (
            self.ref_fluxerr is not None
            and self.ref_fluxerr > 0
            and self.fluxerr is not None
            and self.fluxerr > 0
        ):
            return np.sqrt(self.ref_fluxerr**2 + self.fluxerr**2)
        else:
            return None

    @tot_flux.expression
    def tot_flux(cls):
        """The total flux of the photometry point."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_flux != None,  # noqa: E711
                    cls.ref_flux != 'NaN',
                    cls.ref_flux > 0,
                    cls.flux != 'NaN',
                    cls.flux > 0,
                ),  # noqa
                cls.ref_flux + cls.flux,
            ),
            else_=None,
        )

    @tot_fluxerr.expression
    def tot_fluxerr(cls):
        """The error on the total flux of the photometry point."""
        return sa.case(
            (
                sa.and_(
                    cls.ref_fluxerr != None,  # noqa: E711
                    cls.ref_fluxerr != 'NaN',
                    cls.ref_fluxerr > 0,
                    cls.fluxerr != None,  # noqa: E711
                    cls.fluxerr != 'NaN',
                    cls.fluxerr > 0,
                ),  # noqa
                sa.func.sqrt(
                    sa.func.pow(cls.ref_fluxerr, 2) + sa.func.pow(cls.fluxerr, 2)
                ),
            ),
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

    def to_dict_public(self):
        from ..handlers.api.photometry import serialize

        serialize_data = serialize(
            self, 'ab', 'mag', created_at=False, groups=False, annotations=False
        )
        return {
            "mjd": serialize_data["mjd"],
            "mag": serialize_data["mag"],
            "magerr": serialize_data["magerr"],
            "filter": serialize_data["filter"],
            "limiting_mag": serialize_data["limiting_mag"],
            "instrument_id": serialize_data["instrument_id"],
            "instrument_name": serialize_data["instrument_name"],
            "origin": serialize_data["origin"],
        }


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

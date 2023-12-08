__all__ = ['MMADetector', 'MMADetectorSpectrum', 'MMADetectorTimeInterval']

import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from sqlalchemy_utils import DateTimeRangeType

from baselayer.app.models import (
    Base,
    CustomUserAccessControl,
    ThreadSession,
    join_model,
    public,
    accessible_by_owner,
)

from ..enum_types import (
    mma_detector_types,
)

from .gcn import GcnEvent

from baselayer.app.env import load_env

from .spectrum import NumpyArray

_, cfg = load_env()


def manage_mmadetector_access_logic(cls, user_or_token):
    if user_or_token.is_system_admin:
        return ThreadSession().query(cls)
    elif 'Manage allocations' in [acl.id for acl in user_or_token.acls]:
        return ThreadSession().query(cls)
    else:
        # return an empty query
        return ThreadSession().query(cls).filter(cls.id == -1)


class MMADetector(Base):
    """Multimessenger Astronomical Detector information"""

    read = public
    create = update = delete = CustomUserAccessControl(manage_mmadetector_access_logic)

    name = sa.Column(
        sa.String,
        unique=True,
        nullable=False,
        doc="Unabbreviated facility name (e.g., LIGO Hanford Observatory.",
    )
    nickname = sa.Column(
        sa.String, nullable=False, doc="Abbreviated facility name (e.g., H1)."
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

    spectra = relationship(
        'MMADetectorSpectrum',
        back_populates='detector',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        order_by="MMADetectorSpectrum.start_time",
        doc="MMADetectorSpectra of the object.",
    )

    time_intervals = relationship(
        'MMADetectorTimeInterval',
        back_populates='detector',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        single_parent=True,
        passive_deletes=True,
        order_by="MMADetectorTimeInterval.time_interval",
        doc="MMADetectorTimeInterval of the object.",
    )


GcnEventMMADetector = join_model(
    "gcnevents_mmadetectors", GcnEvent, MMADetector, overlaps="detectors,events"
)
GcnEventMMADetector.__doc__ = "Join table mapping GcnEvents to MMADetectors."


class MMADetectorSpectrum(Base):
    """Frequency-dependent measurement of the sensitivity the detector."""

    read = public
    update = delete = accessible_by_owner

    __tablename__ = 'detector_spectra'
    # TODO better numpy integration
    frequencies = sa.Column(
        NumpyArray, nullable=False, doc="Frequency of the spectrum [Hz]."
    )
    amplitudes = sa.Column(
        NumpyArray,
        nullable=False,
        doc="Amplitudes of the Spectrum [1/sqrt(Hz)].",
    )

    start_time = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="UTC ISO time stamp at the start in which the MMADetectorSpectrum was acquired.",
    )

    end_time = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="UTC ISO time stamp at the end in which the MMADetectorSpectrum was acquired.",
    )

    detector_id = sa.Column(
        sa.ForeignKey('mmadetectors.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the MMADetector that acquired the Spectrum.",
    )

    detector = relationship(
        'MMADetector',
        back_populates='spectra',
        doc="The MMADetector that acquired the Spectrum.",
    )

    groups = relationship(
        "Group",
        secondary="group_mmadetector_spectra",
        back_populates="mmadetector_spectra",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Groups that can view this detector spectrum.',
    )

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the detector spectrum.",
    )
    owner = relationship(
        'User',
        back_populates='mmadetector_spectra',
        foreign_keys=[owner_id],
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the detector spectrum.",
    )

    original_file_string = sa.Column(
        sa.String,
        doc="Content of original file that was passed to upload the spectrum.",
    )
    original_file_filename = sa.Column(
        sa.String, doc="Original file name that was passed to upload the spectrum."
    )

    @classmethod
    def from_ascii(
        cls,
        file,
        detector_id,
        start_time,
        end_time,
        freq_column=0,
        amplitude_column=1,
    ):
        """Generate an `MMADetectorSpectrum` from an ascii file.

        Parameters
        ----------
        file : str or file-like object
           Name or handle of the ASCII file containing the spectrum.
        detector_id : int
           ID of the MMADetector with which this Spectrum was acquired.
        start_time : datetime
           Start time of the observation with which this Spectrum was acquired.
        end_time : datetime
           End time of the observation with which this Spectrum was acquired.
        freq_column : integer, optional
           The 0-based index of the ASCII column corresponding to the frequencies
           values of the spectrum (default 0).
        amplitude_column : integer, optional
           The 0-based index of the ASCII column corresponding to the amplitude
           values of the spectrum (default 1).
        Returns
        -------
        spec : `skyportal.models.MMADetectorSpectrum`
           The MMADetectorSpectrum generated from the ASCII file.

        """

        try:
            f = open(file, 'rb')  # read as ascii
        except TypeError:
            # it's already a stream
            f = file

        try:
            table = ascii.read(f, comment='#', header_start=None)
        except Exception as e:
            e.args = (f'Error parsing ASCII file: {e.args[0]}',)
            raise
        finally:
            f.close()

        tabledata = np.asarray(table)
        colnames = table.colnames

        # validate the table and some of the input parameters

        # require at least 2 columns (wavel, flux)
        ncol = len(colnames)
        if ncol < 2:
            raise ValueError(
                'Input data must have at least 2 columns (frequency, amplitude), '
            )

        spec_data = {}
        # validate the column indices
        for index, name, dbcol in zip(
            [freq_column, amplitude_column],
            ['freq_column', 'amplitude_column'],
            ['frequencies', 'amplitudes'],
        ):

            # index format / type validation:
            if dbcol in ['frequencies', 'amplitudes']:
                if not isinstance(index, int):
                    raise ValueError(f'{name} must be an int')
            else:
                if index is not None and not isinstance(index, int):
                    # The only other allowed value is that fluxerr_column can be
                    # None. If the value of index is not None, raise.
                    raise ValueError(f'invalid type for {name}')

            # after validating the indices, ensure that the columns they
            # point to exist
            if isinstance(index, int):
                if index >= ncol:
                    raise ValueError(
                        f'index {name} ({index}) is greater than the '
                        f'maximum allowed value ({ncol - 1})'
                    )
                spec_data[dbcol] = tabledata[colnames[index]].astype(float)

        return cls(
            detector_id=detector_id,
            start_time=start_time,
            end_time=end_time,
            **spec_data,
        )


class MMADetectorTimeInterval(Base):
    """Data time interval for the detector. Useful for tracking the on/off state for multi-messenger detectors."""

    read = public
    update = delete = accessible_by_owner

    detector_id = sa.Column(
        sa.ForeignKey('mmadetectors.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the MMADetector that acquired the Time Interval.",
    )

    detector = relationship(
        'MMADetector',
        back_populates='time_intervals',
        doc="The MMADetector that acquired the Time Interval.",
    )

    groups = relationship(
        "Group",
        secondary="group_mmadetector_time_intervals",
        back_populates="mmadetector_time_intervals",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Groups that can view this detector spectrum.',
    )

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the detector time interval.",
    )
    owner = relationship(
        'User',
        back_populates='mmadetector_time_intervals',
        foreign_keys=[owner_id],
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the detector time interval.",
    )

    time_interval = sa.Column(
        DateTimeRangeType, doc="The time interval [start, end] of detector data."
    )

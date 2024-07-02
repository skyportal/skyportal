__all__ = ['Spectrum', 'SpectrumReducer', 'SpectrumObserver', 'SpectrumPI']

import warnings
import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as psql
from sqlalchemy.orm import relationship

import astropy.units as u  # noqa: F401
import numpy as np
import yaml
from astropy.utils.exceptions import AstropyWarning
from astropy.io import fits, ascii

from baselayer.app.models import (
    join_model,
    Base,
    User,
    AccessibleIfUserMatches,
    accessible_by_owner,
)
from baselayer.app.json_util import to_json

from .group import accessible_by_groups_members
from ..enum_types import (
    allowed_spectrum_types,
    default_spectrum_type,
    ALLOWED_SPECTRUM_TYPES,
)


class NumpyArray(sa.types.TypeDecorator):
    """SQLAlchemy representation of a NumPy array."""

    impl = psql.ARRAY(sa.Float)

    def process_result_value(self, value, dialect):
        return np.array(value)


class Spectrum(Base):
    """Wavelength-dependent measurement of the flux of an object through a
    dispersive element."""

    read = accessible_by_groups_members
    update = delete = accessible_by_owner

    __tablename__ = 'spectra'
    # TODO better numpy integration
    wavelengths = sa.Column(
        NumpyArray, nullable=False, doc="Wavelengths of the spectrum [Angstrom]."
    )
    fluxes = sa.Column(
        NumpyArray,
        nullable=False,
        doc="Flux of the Spectrum [F_lambda, arbitrary units].",
    )
    errors = sa.Column(
        NumpyArray,
        doc="Errors on the fluxes of the spectrum [F_lambda, same units as `fluxes`.]",
    )

    units = sa.Column(
        sa.String,
        nullable=True,
        doc="Units of the fluxes/errors. Options are Jy, AB, or erg/s/cm/cm/AA.",
    )

    obj_id = sa.Column(
        sa.ForeignKey('objs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of this Spectrum's Obj.",
    )
    obj = relationship('Obj', back_populates='spectra', doc="The Spectrum's Obj.")
    observed_at = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="Median UTC ISO time stamp of the exposure or exposures in which the Spectrum was acquired.",
    )
    origin = sa.Column(sa.String, nullable=True, doc="Origin of the spectrum.")
    type = sa.Column(
        allowed_spectrum_types,
        nullable=False,
        default=default_spectrum_type,
        doc=f'''Type of spectrum. One of: {', '.join(f"'{t}'" for t in ALLOWED_SPECTRUM_TYPES)}.
                Defaults to 'f{default_spectrum_type}'.''',
    )
    label = sa.Column(
        sa.String,
        nullable=True,
        doc='User defined label (can be used to replace default instrument/date labeling on plot legends).',
    )
    # TODO program?
    instrument_id = sa.Column(
        sa.ForeignKey('instruments.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the Instrument that acquired the Spectrum.",
    )
    instrument = relationship(
        'Instrument',
        back_populates='spectra',
        doc="The Instrument that acquired the Spectrum.",
    )
    groups = relationship(
        "Group",
        secondary="group_spectra",
        back_populates="spectra",
        cascade="save-update, merge, refresh-expire, expunge",
        passive_deletes=True,
        doc='Groups that can view this spectrum.',
    )
    pis = relationship(
        "User",
        secondary="spectrum_pis",
        doc="Users that are PIs of the program, or users to serve as points of contact given an external program PI.",
        overlaps='pis, owner',
    )
    reducers = relationship(
        "User",
        secondary="spectrum_reducers",
        doc="Users that reduced this spectrum, or users to serve as points of contact given an external reducer.",
        overlaps='reducers, owner',
    )
    observers = relationship(
        "User",
        secondary="spectrum_observers",
        doc="Users that observed this spectrum, or users to serve as points of contact given an external observer.",
        overlaps='observers, owner',
    )

    followup_request_id = sa.Column(
        sa.ForeignKey('followuprequests.id', ondelete='SET NULL'), nullable=True
    )
    followup_request = relationship('FollowupRequest', back_populates='spectra')

    assignment_id = sa.Column(
        sa.ForeignKey('classicalassignments.id', ondelete='SET NULL'), nullable=True
    )
    assignment = relationship('ClassicalAssignment', back_populates='spectra')

    altdata = sa.Column(
        psql.JSONB, doc="Miscellaneous alternative metadata.", nullable=True
    )

    original_file_string = sa.Column(
        sa.String,
        doc="Content of original file that was passed to upload the spectrum.",
    )
    original_file_filename = sa.Column(
        sa.String, doc="Original file name that was passed to upload the spectrum."
    )

    owner_id = sa.Column(
        sa.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="ID of the User who uploaded the spectrum.",
    )
    owner = relationship(
        'User',
        back_populates='spectra',
        foreign_keys=[owner_id],
        cascade='save-update, merge, refresh-expire, expunge',
        doc="The User who uploaded the spectrum.",
    )

    comments = relationship(
        'CommentOnSpectrum',
        back_populates='spectrum',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="CommentOnSpectrum.created_at",
        doc="Comments posted about this spectrum.",
    )

    reminders = relationship(
        'ReminderOnSpectrum',
        back_populates='spectrum',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="ReminderOnSpectrum.created_at",
        doc="Reminders about this spectrum.",
    )

    annotations = relationship(
        'AnnotationOnSpectrum',
        back_populates='spectrum',
        cascade='save-update, merge, refresh-expire, expunge, delete',
        passive_deletes=True,
        order_by="AnnotationOnSpectrum.created_at",
        doc="Annotations posted about this spectrum.",
    )

    @property
    def astropy_units(self):
        if self.units == "Jy":
            return u.Jy
        elif self.units == "AB":
            return u.AB
        elif self.units == "erg/s/cm/cm/AA":
            return u.erg / u.s / u.cm / u.cm / u.AA
        else:
            return None

    @classmethod
    def from_ascii(
        cls,
        file,
        obj_id=None,
        instrument_id=None,
        type=None,
        label=None,
        observed_at=None,
        wave_column=0,
        flux_column=1,
        fluxerr_column=None,
    ):
        """Generate a `Spectrum` from an ascii file.

        Parameters
        ----------
        file : str or file-like object
           Name or handle of the ASCII file containing the spectrum.
        obj_id : str
           The id of the Obj that this Spectrum is of, if not present
           in the ASCII header.
        instrument_id : int
           ID of the Instrument with which this Spectrum was acquired,
           if not present in the ASCII header.
        type : str
           What is the underlying source of the spectrum.
           Possible types are defined in the config under spectrum types.
        label : str
            User defined label to show on plot legends.
            If not given, the default displayed label is
            <instrument>-<date taken>.
        observed_at : string or datetime
           Median UTC ISO time stamp of the exposure or exposures in which
           the Spectrum was acquired, if not present in the ASCII header.
        wave_column : integer, optional
           The 0-based index of the ASCII column corresponding to the wavelength
           values of the spectrum (default 0).
        flux_column : integer, optional
           The 0-based index of the ASCII column corresponding to the flux
           values of the spectrum (default 1).
        fluxerr_column : integer or None, optional
           The 0-based index of the ASCII column corresponding to the flux error
           values of the spectrum (default None).
        Returns
        -------
        spec : `skyportal.models.Spectrum`
           The Spectrum generated from the ASCII file.

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

        # require at least 2 columns (wavelength, flux)
        ncol = len(colnames)
        if ncol < 2:
            raise ValueError(
                'Input data must have at least 2 columns (wavelength, '
                'flux, and optionally flux error).'
            )

        spec_data = {}
        # validate the column indices
        for index, name, dbcol in zip(
            [wave_column, flux_column, fluxerr_column],
            ['wave_column', 'flux_column', 'fluxerr_column'],
            ['wavelengths', 'fluxes', 'errors'],
        ):
            # index format / type validation:
            if dbcol in ['wavelengths', 'fluxes']:
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

        # parse the header
        if 'comments' in table.meta:
            # this section matches lines like:
            # XTENSION: IMAGE
            # BITPIX: -32
            # NAXIS: 2
            # NAXIS1: 433
            # NAXIS2: 1

            header = {}
            for line in table.meta['comments']:
                try:
                    result = yaml.load(line, Loader=yaml.FullLoader)
                except yaml.YAMLError:
                    continue
                if isinstance(result, dict):
                    header.update(result)

            # this section matches lines like:
            # FILTER  = 'clear   '           / Filter
            # EXPTIME =              600.003 / Total exposure time (sec); avg. of R&B
            # OBJECT  = 'ZTF20abpuxna'       / User-specified object name
            # TARGNAME= 'ZTF20abpuxna_S1'    / Target name (from starlist)
            # DICHNAME= '560     '           / Dichroic

            cards = []
            with warnings.catch_warnings():
                warnings.simplefilter('error', AstropyWarning)
                for line in table.meta['comments']:
                    # this line does not raise a warning
                    card = fits.Card.fromstring(line)
                    try:
                        # this line warns (exception in this context)
                        card.verify()
                    except AstropyWarning:
                        continue
                    cards.append(card)

            # this ensures lines like COMMENT and HISTORY are properly dealt
            # with by using the astropy.header machinery to coerce them to
            # single strings

            fits_header = fits.Header(cards=cards)
            serialized = dict(fits_header)

            commentary_keywords = ['', 'COMMENT', 'HISTORY', 'END']

            for key in serialized:
                # coerce things to serializable JSON
                if key in commentary_keywords:
                    # serialize as a string - otherwise it returns a
                    # funky astropy type that is not json serializable
                    serialized[key] = str(serialized[key])

                if len(fits_header.comments[key]) > 0:
                    header[key] = {
                        'value': serialized[key],
                        'comment': fits_header.comments[key],
                    }
                else:
                    header[key] = serialized[key]

            # this ensures that the spectra are properly serialized to the
            # database JSONB (database JSONB cant handle datetime/date values)
            header = json.loads(to_json(header))

        else:
            header = None

        return cls(
            obj_id=obj_id,
            instrument_id=instrument_id,
            type=type,
            label=label,
            observed_at=observed_at,
            altdata=header,
            **spec_data,
        )

    def to_dict_public(self):
        return {
            'id': self.id,
            'wavelengths': self.wavelengths.tolist(),
            'fluxes': self.fluxes.tolist(),
            'errors': self.errors.tolist() if self.errors is not None else None,
            'units': self.units,
            'origin': self.origin,
            'type': self.type,
            'label': self.label,
            'instrument': self.instrument.name,
            'telescope': self.instrument.telescope.name,
            'observed_at': self.observed_at.isoformat(),
            'pi': [pi.id for pi in self.pis],
            'reducer': [reducer.id for reducer in self.reducers],
            'observer': [observer.id for observer in self.observers],
            'followup_request_id': self.followup_request_id,
            'assignment_id': self.assignment_id,
            'altdata': self.altdata,
            'comments': [c.to_dict() for c in self.comments],
            'reminders': [r.to_dict() for r in self.reminders],
        }


SpectrumPI = join_model(
    "spectrum_pis", Spectrum, User, new_name='SpectrumPI', overlaps='pis'
)
SpectrumReducer = join_model(
    "spectrum_reducers", Spectrum, User, new_name='SpectrumReducer', overlaps='reducers'
)
SpectrumObserver = join_model(
    "spectrum_observers",
    Spectrum,
    User,
    new_name='SpectrumObserver',
    overlaps='observers',
)
SpectrumPI.create = SpectrumPI.delete = SpectrumPI.update = AccessibleIfUserMatches(
    'spectrum.owner'
)
SpectrumReducer.create = (
    SpectrumReducer.delete
) = SpectrumReducer.update = AccessibleIfUserMatches('spectrum.owner')
SpectrumObserver.create = (
    SpectrumObserver.delete
) = SpectrumObserver.update = AccessibleIfUserMatches('spectrum.owner')

# should be accessible only by spectrumowner ^^
SpectrumPI.external_pi = sa.Column(
    sa.String,
    nullable=True,
    doc="The actual PI for the spectrum, provided as free text if the "
    "PI is not a user in the database. Separate from the point-of-contact "
    "user designated as PI",
)
SpectrumReducer.external_reducer = sa.Column(
    sa.String,
    nullable=True,
    doc="The actual reducer for the spectrum, provided as free text if the "
    "reducer is not a user in the database. Separate from the point-of-contact "
    "user designated as reducer",
)
SpectrumObserver.external_observer = sa.Column(
    sa.String,
    nullable=True,
    doc="The actual observer for the spectrum, provided as free text if the "
    "observer is not a user in the database. Separate from the point-of-contact "
    "user designated as observer",
)

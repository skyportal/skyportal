# This module acts as a placeholder for generated schema.  After
# `setup_schema` is run from `models`, each table will have an
# associated schema here.  E.g., `models.Dog` will be matched by `schema.Dog`.


# From
# https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models

from marshmallow_sqlalchemy import (
    ModelConversionError as _ModelConversionError,
    ModelSchema as _ModelSchema,
)

from marshmallow import (
    Schema as _Schema,
    fields,
    post_load,
    pre_dump,
    ValidationError,
)
from marshmallow_enum import EnumField


from baselayer.app.models import Base as _Base, DBSession as _DBSession

from skyportal.enum_types import (
    py_allowed_bandpasses,
    py_allowed_magsystems,
    py_followup_priorities,
    ALLOWED_BANDPASSES,
    ALLOWED_MAGSYSTEMS,
    force_render_enum_markdown,
)

from astropy.table import Table
import operator

import sys
import inspect
import numpy as np
from enum import Enum


class ApispecEnumField(EnumField):
    """See https://github.com/justanr/marshmallow_enum/issues/24#issue-335162592
    """

    def __init__(self, enum, *args, **kwargs):
        super().__init__(enum, *args, **kwargs)
        self.metadata['enum'] = [e.name for e in enum]


class Response(_Schema):
    status = ApispecEnumField(Enum('status', ['error', 'success']), required=True)
    message = fields.String()
    data = fields.Dict()


class Error(Response):
    status = ApispecEnumField(Enum('status', ['error']), required=True)


class newsFeedPrefs(_Schema):
    numItems = fields.String()


class UserPreferences(_Schema):
    newsFeed = fields.Nested(newsFeedPrefs)


class UpdateUserPreferencesRequestJSON(_Schema):
    preferences = fields.Nested(UserPreferences)


def success(schema_name, base_schema=None):
    schema_fields = {
        'status': ApispecEnumField(Enum('status', ['success']), required=True),
        'message': fields.String(),
    }

    if base_schema is not None:
        if isinstance(base_schema, list):
            schema_fields['data'] = fields.List(fields.Nested(base_schema[0]),)
        else:
            schema_fields['data'] = fields.Nested(base_schema)

    return type(schema_name, (_Schema,), schema_fields)


def setup_schema():
    """For each model, install a marshmallow schema generator as
    `model.__schema__()`, and add an entry to the `schema`
    module.

    """
    for class_ in _Base._decl_class_registry.values():
        if hasattr(class_, '__tablename__'):
            if class_.__name__.endswith('Schema'):
                raise _ModelConversionError(
                    "For safety, setup_schema can not be used when a"
                    "Model class ends with 'Schema'"
                )

            def add_schema(schema_class_name, exclude=[], add_to_model=False):
                """Add schema to module namespace, and, optionally, to model object.

                Parameters
                ----------
                schema_class_name : str
                    Name of schema.
                exclude : list of str, optional
                    List of model attributes to exclude from schema. Defaults to `[]`.
                add_to_model : bool, optional
                    Boolean indicating whether to install this schema generator
                    on the model as `model.__schema__`. Defaults to `False`.
                """
                schema_class_meta = type(
                    f'{schema_class_name}_meta',
                    (),
                    {
                        'model': class_,
                        'sqla_session': _DBSession,
                        'ordered': True,
                        'exclude': [],
                        'include_fk': True,
                        'include_relationships': False,
                    },
                )
                for exclude_attr in exclude:
                    if (
                        hasattr(class_, exclude_attr)
                        and getattr(class_, exclude_attr) is not None
                    ):
                        schema_class_meta.exclude.append(exclude_attr)

                schema_class = type(
                    schema_class_name, (_ModelSchema,), {'Meta': schema_class_meta}
                )

                if add_to_model:
                    setattr(class_, '__schema__', schema_class)

                setattr(sys.modules[__name__], schema_class_name, schema_class())

            schema_class_name = class_.__name__
            add_schema(
                schema_class_name, exclude=['created_at', 'modified'], add_to_model=True
            )
            add_schema(
                f'{schema_class_name}NoID',
                exclude=[
                    'created_at',
                    'id',
                    'modified',
                    'owner_id',
                    'last_modified_by_id',
                ],
            )


class PhotBaseFlexible(object):
    """This is the base class for two classes that are used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    mjd = fields.Field(
        description='MJD of the observation(s). Can be a given as a '
        'scalar or a 1D list. If a scalar, will be '
        'broadcast to all values given as lists. '
        'Null values not allowed.',
        required=True,
    )

    filter = fields.Field(
        required=True,
        description='The bandpass of the observation(s). '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values not allowed. Allowed values: '
        f'{force_render_enum_markdown(ALLOWED_BANDPASSES)}',
    )

    obj_id = fields.Field(
        description='ID of the `Obj`(s) to which the '
        'photometry will be attached. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values are not allowed.',
        required=True,
    )

    instrument_id = fields.Field(
        description='ID of the `Instrument`(s) with which the '
        'photometry was acquired. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values are not allowed.',
        required=True,
    )

    assignment_id = fields.Integer(
        description='ID of the classical assignment which generated the photometry',
        required=False,
        missing=None,
    )

    ra = fields.Field(
        description='ICRS Right Ascension of the centroid '
        'of the photometric aperture [deg]. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed.',
        required=False,
        missing=None,
    )

    dec = fields.Field(
        description='ICRS Declination of the centroid '
        'of the photometric aperture [deg]. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed.',
        required=False,
        missing=None,
    )

    ra_unc = fields.Field(
        description='Uncertainty on RA [arcsec]. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed.',
        required=False,
        missing=None,
    )

    dec_unc = fields.Field(
        description='Uncertainty on dec [arcsec]. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed.',
        required=False,
        missing=None,
    )

    origin = fields.Field(
        description="Provenance of the Photometry. If a record is "
        "already present with identical origin, only the "
        "groups list will be updated (other data assumed "
        "identical). Defaults to None.",
        missing=None,
    )

    group_ids = fields.Field(
        description="List of group IDs to which photometry points will be visible. "
        "If 'all', will be shared with site-wide public group (visible to all users "
        "who can view associated source).",
        required=True,
    )

    altdata = fields.Field(
        description="Misc. alternative metadata stored in JSON "
        "format, e.g. `{'calibration': {'source': 'ps1', "
        "'color_term': 0.012}, 'photometry_method': 'allstar', "
        "'method_reference': 'Masci et al. (2015)'}`",
        missing=None,
        default=None,
        required=False,
    )


class PhotFluxFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = [
        'magsys',
        'mjd',
        'filter',
        'obj_id',
        'instrument_id',
        'fluxerr',
        'zp',
    ]

    magsys = fields.Field(
        required=True,
        description='The magnitude system to which the flux, flux error, '
        'and the zeropoint are tied. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values not allowed. Allowed values: '
        f'{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}',
    )

    flux = fields.Field(
        description='Flux of the observation(s) in counts. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed, to accommodate,'
        'e.g., upper limits from ZTF1, where flux is not provided '
        'for non-detections. For a given photometry '
        'point, if `flux` is null, `fluxerr` is '
        'used to derive a 5-sigma limiting magnitude '
        'when the photometry point is requested in '
        'magnitude space from the Photomety GET api.',
        required=False,
        missing=None,
    )

    fluxerr = fields.Field(
        description='Gaussian error on the flux in counts. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values not allowed.',
        required=True,
    )

    zp = fields.Field(
        description='Magnitude zeropoint, given by `zp` in the '
        'equation `m = -2.5 log10(flux) + zp`. '
        '`m` is the magnitude of the object in the '
        'magnitude system `magsys`. '
        'Can be given as a scalar or a 1D list. '
        'Null values not allowed.',
        required=True,
    )


class PhotMagFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = [
        'magsys',
        'limiting_mag',
        'mjd',
        'filter',
        'obj_id',
        'instrument_id',
    ]

    magsys = fields.Field(
        required=True,
        description='The magnitude system to which the magnitude, '
        'magnitude error, and limiting magnitude are tied. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values not allowed. Allowed values: '
        f'{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}',
    )

    mag = fields.Field(
        description='Magnitude of the observation in the '
        'magnitude system `magsys`. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed for non-detections. '
        'If `mag` is null, the corresponding '
        '`magerr` must also be null.',
        required=False,
        missing=None,
    )

    magerr = fields.Field(
        description='Magnitude of the observation in the '
        'magnitude system `magsys`. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values allowed for non-detections. '
        'If `magerr` is null, the corresponding `mag` '
        'must also be null.',
        required=False,
        missing=None,
    )

    limiting_mag = fields.Field(
        description='Limiting magnitude of the image '
        'in the magnitude system `magsys`. '
        'Can be given as a scalar or a 1D list. '
        'If a scalar, will be broadcast to all values '
        'given as lists. Null values not allowed.',
        required=True,
    )

    limiting_mag_nsigma = fields.Field(
        description='Number of standard deviations '
        'above the background that the limiting '
        'magnitudes correspond to. Null values '
        'not allowed. Default = 5.',
        required=False,
        missing=5,
    )


class PhotBase(object):
    """This is the base class of two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    PhotometryHandler.get`.
    """

    mjd = fields.Number(description='MJD of the observation.', required=True)
    magsys = ApispecEnumField(
        py_allowed_magsystems,
        required=True,
        description='The magnitude system to which the '
        'flux and the zeropoint are tied.',
    )
    filter = ApispecEnumField(
        py_allowed_bandpasses,
        required=True,
        description='The bandpass of the observation.',
    )

    obj_id = fields.String(
        description='ID of the Object to which the ' 'photometry will be attached.',
        required=True,
    )

    instrument_id = fields.Integer(
        description='ID of the instrument with which'
        ' the observation was carried '
        'out.',
        required=True,
    )

    assignment_id = fields.Integer(
        description='ID of the classical assignment which generated the photometry',
        required=False,
        missing=None,
    )

    ra = fields.Number(
        description='ICRS Right Ascension of the centroid '
        'of the photometric aperture [deg].',
        missing=None,
        default=None,
    )
    dec = fields.Number(
        description='ICRS Declination of the centroid '
        'of the photometric aperture [deg].',
        missing=None,
        default=None,
    )

    ra_unc = fields.Number(
        description='Uncertainty on RA [arcsec].', missing=None, default=None
    )

    dec_unc = fields.Number(
        description='Uncertainty on dec [arcsec].', missing=None, default=None
    )

    alert_id = fields.Integer(
        description="Corresponding alert ID. If a record is "
        "already present with identical alert ID, only the "
        "groups list will be updated (other alert data assumed "
        "identical). Defaults to None.",
        missing=None,
        default=None,
    )

    altdata = fields.Dict(
        description="Misc. alternative metadata stored in JSON "
        "format, e.g. `{'calibration': {'source': 'ps1', "
        "'color_term': 0.012}, 'photometry_method': 'allstar', "
        "'method_reference': 'Masci et al. (2015)'}`",
        missing=None,
        default=None,
    )

    @post_load
    def enum_to_string(self, data, **kwargs):
        # convert enumified data back to strings
        data['filter'] = data['filter'].name
        data['magsys'] = data['magsys'].name
        return data


class PhotometryFlux(_Schema, PhotBase):
    """This is one of two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    PhotometryHandler.get`.
    """

    flux = fields.Number(
        description='Flux of the observation in counts. '
        'Can be null to accommodate upper '
        'limits from ZTF1, where no flux is measured '
        'for non-detections. If flux is null, '
        'the flux error is used to derive a '
        'limiting magnitude.',
        required=False,
        missing=None,
        default=None,
    )

    fluxerr = fields.Number(
        description='Gaussian error on the flux in counts.', required=True
    )

    zp = fields.Number(
        description='Magnitude zeropoint, given by `ZP` in the '
        'equation m = -2.5 log10(flux) + `ZP`. '
        'm is the magnitude of the object in the '
        'magnitude system `magsys`.',
        required=True,
    )

    @post_load
    def parse_flux(self, data, **kwargs):
        """Return a `Photometry` object from a `PhotometryFlux` marshmallow
        schema.

        Parameters
        ----------
        data : dict
            The instance of the PhotometryFlux schema to convert to Photometry.

        Returns
        -------
        Photometry
            The Photometry object generated from the PhotometryFlux object.
        """

        from skyportal.models import Instrument, Obj, PHOT_SYS, PHOT_ZP, Photometry
        from sncosmo.photdata import PhotometricData

        # get the instrument
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            raise ValidationError(f'Invalid instrument ID: {data["instrument_id"]}')

        # get the object
        obj = Obj.query.get(data['obj_id'])  # TODO : implement permissions checking
        if not obj:
            raise ValidationError(f'Invalid object ID: {data["obj_id"]}')

        if data["filter"] not in instrument.filters:
            raise ValidationError(
                f"Instrument {instrument.name} has no filter " f"{data['filter']}."
            )

        # convert flux to microJanskies.
        table = Table([data])
        if data['flux'] is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table['flux'] = 0.0

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP, zpsys=PHOT_SYS)

        # replace with null if needed
        final_flux = None if data['flux'] is None else photdata.flux[0]

        p = Photometry(
            obj_id=data['obj_id'],
            mjd=data['mjd'],
            flux=final_flux,
            fluxerr=photdata.fluxerr[0],
            instrument_id=data['instrument_id'],
            assignment_id=data['assignment_id'],
            filter=data['filter'],
            ra=data['ra'],
            dec=data['dec'],
            ra_unc=data['ra_unc'],
            dec_unc=data['dec_unc'],
        )
        if 'alert_id' in data and data['alert_id'] is not None:
            p.alert_id = data['alert_id']
        return p


class PhotometryMag(_Schema, PhotBase):
    """This is one of  two classes that are used for deserializing
     and validating the postprocessed input data of `PhotometryHandler.post`
     and `PhotometryHandler.put` and for generating the API docs of
     `PhotometryHandler.get`.
     """

    mag = fields.Number(
        description='Magnitude of the observation in the '
        'magnitude system `magsys`. Can be null '
        'in the case of a non-detection.',
        required=False,
        missing=None,
        default=None,
    )
    magerr = fields.Number(
        description='Magnitude error of the observation in '
        'the magnitude system `magsys`. Can be '
        'null in the case of a non-detection.',
        required=False,
        missing=None,
        default=None,
    )
    limiting_mag = fields.Number(
        description='Limiting magnitude of the image '
        'in the magnitude system `magsys`.',
        required=True,
    )

    @post_load
    def parse_mag(self, data, **kwargs):
        """Return a `Photometry` object from a `PhotometryMag` marshmallow
        schema.

        Parameters
        ----------
        data : dict
            The instance of the PhotometryMag schema to convert to Photometry.

        Returns
        -------
        Photometry
            The Photometry object generated from the PhotometryMag dict.
        """

        from skyportal.models import Instrument, Obj, PHOT_SYS, PHOT_ZP, Photometry
        from sncosmo.photdata import PhotometricData

        # check that mag and magerr are both null or both not null, not a mix
        ok = any(
            [
                all([op(field, None) for field in [data['mag'], data['magerr']]])
                for op in [operator.is_, operator.is_not]
            ]
        )

        if not ok:
            raise ValidationError(
                f'Error parsing packet "{data}": mag '
                f'and magerr must both be null, or both be '
                f'not null.'
            )

        # get the instrument
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            raise ValidationError(f'Invalid instrument ID: {data["instrument_id"]}')

        # get the object
        obj = Obj.query.get(data['obj_id'])  # TODO: implement permissions checking
        if not obj:
            raise ValidationError(f'Invalid object ID: {data["obj_id"]}')

        if data["filter"] not in instrument.filters:
            raise ValidationError(
                f"Instrument {instrument.name} has no filter " f"{data['filter']}."
            )

        # determine if this is a limit or a measurement
        hasmag = data['mag'] is not None

        if hasmag:
            flux = 10 ** (-0.4 * (data['mag'] - PHOT_ZP))
            fluxerr = data['magerr'] / (2.5 / np.log(10)) * flux
        else:
            fivesigflux = 10 ** (-0.4 * (data['limiting_mag'] - PHOT_ZP))
            flux = None
            fluxerr = fivesigflux / 5

        # convert flux to microJanskies.
        table = Table(
            [
                {
                    'flux': flux,
                    'fluxerr': fluxerr,
                    'magsys': data['magsys'],
                    'zp': PHOT_ZP,
                    'filter': data['filter'],
                    'mjd': data['mjd'],
                }
            ]
        )
        if flux is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table['flux'] = 0.0

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP, zpsys=PHOT_SYS)

        # replace with null if needed
        final_flux = None if flux is None else photdata.flux[0]

        p = Photometry(
            obj_id=data['obj_id'],
            mjd=data['mjd'],
            flux=final_flux,
            fluxerr=photdata.fluxerr[0],
            instrument_id=data['instrument_id'],
            assignment_id=data['assignment_id'],
            filter=data['filter'],
            ra=data['ra'],
            dec=data['dec'],
            ra_unc=data['ra_unc'],
            dec_unc=data['dec_unc'],
        )
        if 'alert_id' in data and data['alert_id'] is not None:
            p.alert_id = data['alert_id']
        return p


class AssignmentSchema(_Schema):
    # For generating API docs and extremely basic validation

    run_id = fields.Integer(required=True)
    obj_id = fields.String(
        required=True, description='The ID of the object to observe.'
    )
    priority = ApispecEnumField(
        py_followup_priorities,
        required=True,
        description='Priority of the request, ' '(lowest = 1, highest = 5).',
    )
    status = fields.String(description='The status of the request')
    comment = fields.String(description='An optional comment describing the request.')


class ObservingRunPost(_Schema):
    instrument_id = fields.Integer(
        required=True, description='The ID of the instrument to be ' 'used in this run.'
    )

    # name of the PI
    pi = fields.String(description='The PI of the observing run.')
    observers = fields.String(description='The names of the observers')
    group_id = fields.Integer(
        description='The ID of the group this run is associated with.'
    )
    calendar_date = fields.Date(
        description='The local calendar date of the run.', required=True
    )


class ObservingRunGet(ObservingRunPost):
    owner_id = fields.Integer(description='The User ID of the owner of this run.')
    ephemeris = fields.Field(description='Observing run ephemeris data.')
    id = fields.Integer(description='Unique identifier for the run.')

    @pre_dump
    def serialize(self, data, **kwargs):
        data.ephemeris = {}
        data.ephemeris['sunrise_utc'] = data.sunrise.isot
        data.ephemeris['sunset_utc'] = data.sunset.isot
        data.ephemeris[
            'twilight_evening_nautical_utc'
        ] = data.twilight_evening_nautical.isot
        data.ephemeris[
            'twilight_morning_nautical_utc'
        ] = data.twilight_morning_nautical.isot
        data.ephemeris[
            'twilight_evening_astronomical_utc'
        ] = data.twilight_evening_astronomical.isot
        data.ephemeris[
            'twilight_morning_astronomical_utc'
        ] = data.twilight_morning_astronomical.isot
        return data


class ObservingRunGetWithAssignments(ObservingRunGet):
    assignments = fields.List(fields.Field())
    instrument = fields.Field()


class PhotometryRangeQuery(_Schema):
    instrument_ids = fields.List(
        fields.Integer,
        description="IDs of the instruments to query "
        "for photometry from. If `None`, "
        "queries all instruments.",
        required=False,
        missing=None,
        default=None,
    )

    min_date = fields.DateTime(
        required=False,
        description='Query for photometry taken after '
        'this UT `DateTime`. For an '
        'open-ended interval use `None`.',
        missing=None,
        default=None,
    )

    max_date = fields.DateTime(
        required=False,
        description='Query for photometry taken before '
        'this UT `DateTime`. For an '
        'open-ended interval use `None`.',
        missing=None,
        default=None,
    )


class SpectrumAsciiFileParseJSON(_Schema):

    wave_column = fields.Integer(
        missing=0,
        description="The 0-based index of the ASCII column corresponding "
        "to the wavelength values of the spectrum (default 0).",
    )
    flux_column = fields.Integer(
        missing=1,
        description="The 0-based index of the ASCII column corresponding to "
        "the flux values of the spectrum (default 1).",
    )
    fluxerr_column = fields.Integer(
        missing=None,
        description="The 0-based index of the ASCII column corresponding to the flux "
        "error values of the spectrum (default 2). If there are only 2 "
        "columns in the input file this value will be ignored. If there are "
        "more than 2 columns in the input file, but none of them correspond to "
        "flux error values, set this parameter to `None`.",
    )

    ascii = fields.String(
        description="""The content of the ASCII file to be parsed.

The file can optionally contain a header which will be parsed and stored.

The lines that make up the ASCII header must appear at the beginning of the \
file and all be formatted the same way within a single file. They can be \
formatted in one of two ways.

```
1) # KEY: VALUE
2) # KEY = VALUE / COMMENT
```

`astropy.io.ascii.read` is used to load the table into Python memory. An \
attempt is made to parse the header first using method 1, then method 2.

Example of format 1:

```
# XTENSION: IMAGE
# BITPIX: -32
# NAXIS: 2
# NAXIS1: 433
# NAXIS2: 1
# RA: 230.14
```

Example of format 2:

```
# FILTER  = 'clear   '           / Filter
# EXPTIME =              600.003 / Total exposure time (sec); avg. of R&B
# OBJECT  = 'ZTF20abpuxna'       / User-specified object name
# TARGNAME= 'ZTF20abpuxna_S1'    / Target name (from starlist)
# DICHNAME= '560     '           / Dichroic
# GRISNAME= '400/3400'           / Blue grism
# GRANAME = '400/8500'           / Red grating
# WAVELEN =        7829.41406250 / Red specified central wavelength
# BLUFILT = 'clear   '           / Blue filter
# REDFILT = 'Clear   '           / Red filter
# SLITNAME= 'long_1.0'           / Slitmask
# INSTRUME= 'LRIS+LRISBLUE'      / Camera
# TELESCOP= 'Keck I  '           / Telescope name
# BLUDET  = 'LRISB   '           / LRIS blue detector
# REDDET  = 'LRISR3  '           / LRIS red detector
# OBSERVER= 'Andreoni Anand De'  / Observer name
# REDUCER = '        '           / Name of reducer
# LPIPEVER= '2020.06 '           / LPipe version number
# HOSTNAME= 'gayatri '           / LPipe host computer name
# IDLVER  = '8.1     '           / IDL version number
# DATE    = '2020-09-15T09:47:10' / UT end of last exposure
```

The data must be at least 2 column ascii (wavelength, flux). If three columns \
are given, they are interpreted as (wavelength, flux, fluxerr). If more than 3 \
columns are given, by default the first three are interpreted as (wavelength, \
flux, fluxerr). The column indices of each of these arguments can be controlled \
by passing the integer column index to the POST JSON.

Examples of valid data sections:

Many-column ASCII:

```
   10295.736  2.62912e-16  1.67798e-15  2.24407e-17    4084    75.956  5.48188e+15  0
   10296.924  2.96887e-16  1.57197e-15  2.21469e-17    4085    75.959  5.42569e+15  0
   10298.112  3.20429e-16  1.45017e-15  2.16863e-17    4086    75.962  5.36988e+15  0
   10299.301  3.33367e-16  1.06116e-15  1.94187e-17    4087    75.965  5.31392e+15  0
   10300.489  3.09943e-16  6.99539e-16  1.67183e-17    4088    75.968  5.25836e+15  0
   10301.678  3.48273e-16  5.56194e-16  1.59555e-17    4089    75.972  5.20314e+15  0
   10302.866  3.48102e-16  5.28483e-16  1.58033e-17    4090    75.975  5.15146e+15  0
   10304.055  3.78640e-16  6.00997e-16  1.67462e-17    4091    75.978  5.10058e+15  0
   10305.243  4.28820e-16  7.18759e-16  1.81534e-17    4092    75.981  5.05032e+15  0
   10306.432  4.13152e-16  7.54203e-16  1.83965e-17    4093    75.984  5.00097e+15  0
```

3-column ASCII:

```
8993.2 1.148e-16 7.919e-34
9018.7 1.068e-16 6.588e-34
9044.3 1.056e-16 5.660e-34
9069.9 9.763e-17 5.593e-34
9095.4 1.048e-16 8.374e-34
9121.0 1.026e-16 8.736e-34
9146.6 8.472e-17 9.505e-34
9172.1 9.323e-17 7.592e-34
9197.7 1.050e-16 7.863e-34
9223.3 8.701e-17 7.135e-34
```

2-column ASCII:

```
      10045.1    0.0217740
      10046.3    0.0182158
      10047.4    0.0204764
      10048.6    0.0231833
      10049.8    0.0207157
      10051.0    0.0185226
      10052.2    0.0200072
      10053.4    0.0205159
      10054.5    0.0199460
      10055.7    0.0210533
```


2-column ASCII:
```
7911.60 1.045683
7920.80 1.046414
7930.00 1.235362
7939.20 0.783466
7948.40 1.116153
7957.60 1.375844
7966.80 1.029127
7976.00 1.019637
7985.20 0.732859
7994.40 1.236514
```

""",
        required=True,
    )


class SpectrumAsciiFilePostJSON(SpectrumAsciiFileParseJSON):
    obj_id = fields.String(
        description='The ID of the object that the spectrum is of.', required=True
    )
    instrument_id = fields.Integer(
        description='The ID of the instrument that took the spectrum.', required=True
    )
    observed_at = fields.DateTime(
        description='The ISO UTC time the spectrum was taken.', required=True
    )
    group_ids = fields.List(
        fields.Integer, description="The IDs of the groups to share this spectrum with."
    )
    filename = fields.String(
        description="The original filename (for bookkeeping purposes).", required=True,
    )
    reduced_by = fields.List(
        fields.Integer,
        description="IDs of the Users who reduced this Spectrum.",
        missing=[],
    )
    observed_by = fields.List(
        fields.Integer,
        description="IDs of the Users who observed this Spectrum.",
        missing=[],
    )


class SpectrumPost(_Schema):

    wavelengths = fields.List(
        fields.Float,
        required=True,
        description="Wavelengths of the spectrum [Angstrom].",
    )

    fluxes = fields.List(
        fields.Float,
        required=True,
        description="Flux of the Spectrum [F_lambda, arbitrary units].",
    )

    errors = fields.List(
        fields.Float,
        description="Errors on the fluxes of the spectrum [F_lambda, same units as `fluxes`.]",
    )

    obj_id = fields.String(required=True, description="ID of this Spectrum's Obj.",)

    observed_at = fields.DateTime(
        description='The ISO UTC time the spectrum was taken.', required=True
    )

    reduced_by = fields.List(
        fields.Integer,
        description="IDs of the Users who reduced this Spectrum.",
        missing=[],
    )

    observed_by = fields.List(
        fields.Integer,
        description="IDs of the Users who observed this Spectrum.",
        missing=[],
    )

    origin = fields.String(required=False, description="Origin of the spectrum.")

    instrument_id = fields.Integer(
        required=True, description="ID of the Instrument that acquired the Spectrum.",
    )

    group_ids = fields.Field(
        missing=[],
        description='IDs of the Groups to share this spectrum with. Set to "all"'
        ' to make this spectrum visible to all users.',
    )

    followup_request_id = fields.Integer(
        required=False,
        description='ID of the Followup request that generated this spectrum, '
        'if any.',
    )

    assignment_id = fields.Integer(
        required=False,
        description='ID of the classical assignment that generated this spectrum, '
        'if any.',
    )

    altdata = fields.Field(description='Miscellaneous alternative metadata.')


class GroupIDList(_Schema):

    group_ids = fields.List(fields.Integer, required=True)


def register_components(spec):
    print('Registering schemas with APISpec')

    schemas = inspect.getmembers(
        sys.modules[__name__], lambda m: isinstance(m, _Schema)
    )

    for (name, schema) in schemas:
        spec.components.schema(name, schema=schema)

        single = 'Single' + name
        arrayOf = 'ArrayOf' + name + 's'
        spec.components.schema(single, schema=success(single, schema))
        spec.components.schema(arrayOf, schema=success(arrayOf, [schema]))


# Replace schemas by instantiated versions
# These are picked up in `setup_schema` for the registry
Response = Response()
Error = Error()
Success = success('Success')
SinglePhotometryFlux = success('SinglePhotometryFlux', PhotometryFlux)
SinglePhotometryMag = success('SinglePhotometryMag', PhotometryMag)
PhotometryFlux = PhotometryFlux()
PhotometryMag = PhotometryMag()
PhotMagFlexible = PhotMagFlexible()
PhotFluxFlexible = PhotFluxFlexible()
ObservingRunPost = ObservingRunPost()
ObservingRunGet = ObservingRunGet()
AssignmentSchema = AssignmentSchema()
ObservingRunGetWithAssignments = ObservingRunGetWithAssignments()
PhotometryRangeQuery = PhotometryRangeQuery()
SpectrumAsciiFilePostJSON = SpectrumAsciiFilePostJSON()
SpectrumAsciiFileParseJSON = SpectrumAsciiFileParseJSON()
SpectrumPost = SpectrumPost()
GroupIDList = GroupIDList()

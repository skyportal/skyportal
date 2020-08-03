# This module acts as a placeholder for generated schema.  After
# `setup_schema` is run from `models`, each table will have an
# associated schema here.  E.g., `models.Dog` will be matched by `schema.Dog`.


# From
# https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models

from marshmallow_sqlalchemy import (
    ModelConversionError as _ModelConversionError,
    ModelSchema as _ModelSchema
)

from marshmallow import (Schema as _Schema, fields, validate, post_load,
                         ValidationError)
from marshmallow_enum import EnumField

import sqlalchemy as sa
from sqlalchemy.orm import mapper

from baselayer.app.models import (
    Base as _Base,
    DBSession as _DBSession
)

from skyportal.phot_enum import (
    py_allowed_bandpasses,
    py_allowed_magsystems,
    py_thumbnail_types,
    ALLOWED_BANDPASSES,
    ALLOWED_MAGSYSTEMS,
    force_render_enum_markdown
)

from astropy.table import Table
import operator

import sys
import inspect
import numpy as np
from uuid import uuid4
from enum import Enum
from typing import Any
import base64


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
            schema_fields['data'] = fields.List(
                fields.Nested(base_schema[0]),
            )
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
                schema_class_meta = type(f'{schema_class_name}_meta', (),
                                         {'model': class_, 'sqla_session': _DBSession,
                                          'ordered': True, 'exclude': [], 'include_fk': True,
                                          'include_relationships': False}
                                         )
                for exclude_attr in exclude:
                    if hasattr(class_, exclude_attr) and getattr(class_, exclude_attr) is not None:
                        schema_class_meta.exclude.append(exclude_attr)

                schema_class = type(schema_class_name, (_ModelSchema,),
                                    {'Meta': schema_class_meta}
                                    )

                if add_to_model:
                    setattr(class_, '__schema__', schema_class)

                setattr(sys.modules[__name__], schema_class_name,
                        schema_class())

            schema_class_name = class_.__name__
            add_schema(schema_class_name, exclude=['created_at', 'modified'],
                       add_to_model=True)
            add_schema(f'{schema_class_name}NoID',
                       exclude=['created_at', 'id', 'modified', 'single_user_group'])


class PhotBaseFlexible(object):
    """This is the base class for two classes that are used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""
    mjd = fields.Field(description='MJD of the observation(s). Can be a given as a '
                                   'scalar or a 1D list. If a scalar, will be '
                                   'broadcast to all values given as lists. '
                                   'Null values not allowed.',
                       required=True)

    filter = fields.Field(required=True,
                          description='The bandpass of the observation(s). '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values not allowed. Allowed values: '
                                      f'{force_render_enum_markdown(ALLOWED_BANDPASSES)}')

    obj_id = fields.Field(description='ID of the `Obj`(s) to which the '
                                      'photometry will be attached. '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values are not allowed.',
                          required=True)

    instrument_id = fields.Field(description='ID of the `Instrument`(s) with which the '
                                 'photometry was acquired. '
                                 'Can be given as a scalar or a 1D list. '
                                 'If a scalar, will be broadcast to all values '
                                 'given as lists. Null values are not allowed.',
                                 required=True)

    ra = fields.Field(description='ICRS Right Ascension of the centroid '
                                  'of the photometric aperture [deg]. '
                                  'Can be given as a scalar or a 1D list. '
                                  'If a scalar, will be broadcast to all values '
                                  'given as lists. Null values allowed.',
                      required=False, missing=None)

    dec = fields.Field(description='ICRS Declination of the centroid '
                                   'of the photometric aperture [deg]. '
                                   'Can be given as a scalar or a 1D list. '
                                   'If a scalar, will be broadcast to all values '
                                   'given as lists. Null values allowed.',
                       required=False, missing=None)

    ra_unc = fields.Field(description='Uncertainty on RA [arcsec]. '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values allowed.',
                          required=False, missing=None)

    dec_unc = fields.Field(description='Uncertainty on dec [arcsec]. '
                                       'Can be given as a scalar or a 1D list. '
                                       'If a scalar, will be broadcast to all values '
                                       'given as lists. Null values allowed.',
                           required=False, missing=None)

    alert_id = fields.Field(description="Corresponding alert ID. If a record is "
                            "already present with identical alert ID, only the "
                            "groups list will be updated (other alert data assumed "
                            "identical). Defaults to None.")

    group_ids = fields.List(fields.Integer(),
                            description="List of group IDs to which photometry "
                                        "points will be visible.",
                            required=True)

    altdata = fields.Field(description="Misc. alternative metadata stored in JSON "
                           "format, e.g. `{'calibration': {'source': 'ps1', "
                           "'color_term': 0.012}, 'photometry_method': 'allstar', "
                           "'method_reference': 'Masci et al. (2015)'}`",
                           missing=None, default=None, required=False)


class PhotFluxFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = ['magsys', 'mjd', 'filter', 'obj_id', 'instrument_id',
                     'fluxerr', 'zp']

    magsys = fields.Field(required=True,
                          description='The magnitude system to which the flux, flux error, '
                                      'and the zeropoint are tied. '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values not allowed. Allowed values: '
                                      f'{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}')

    flux = fields.Field(description='Flux of the observation(s) in counts. '
                                    'Can be given as a scalar or a 1D list. '
                                    'If a scalar, will be broadcast to all values '
                                    'given as lists. Null values allowed, to accommodate,'
                                    'e.g., upper limits from ZTF1, where flux is not provided '
                                    'for non-detections. For a given photometry '
                                    'point, if `flux` is null, `fluxerr` is '
                                    'used to derive a 5-sigma limiting magnitude '
                                    'when the photometry point is requested in '
                                    'magnitude space from the Photomety GET api.',
                        required=False, missing=None)

    fluxerr = fields.Field(description='Gaussian error on the flux in counts. '
                                       'Can be given as a scalar or a 1D list. '
                                       'If a scalar, will be broadcast to all values '
                                       'given as lists. Null values not allowed.',
                           required=True)

    zp = fields.Field(description='Magnitude zeropoint, given by `zp` in the '
                      'equation `m = -2.5 log10(flux) + zp`. '
                      '`m` is the magnitude of the object in the '
                      'magnitude system `magsys`. '
                      'Can be given as a scalar or a 1D list. '
                      'Null values not allowed.',
                      required=True)


class PhotMagFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = ['magsys', 'limiting_mag', 'mjd', 'filter',
                     'obj_id', 'instrument_id']

    magsys = fields.Field(required=True,
                          description='The magnitude system to which the magnitude, '
                                      'magnitude error, and limiting magnitude are tied. '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values not allowed. Allowed values: '
                                      f'{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}')

    mag = fields.Field(description='Magnitude of the observation in the '
                                   'magnitude system `magsys`. '
                                   'Can be given as a scalar or a 1D list. '
                                   'If a scalar, will be broadcast to all values '
                                   'given as lists. Null values allowed for non-detections. '
                                   'If `mag` is null, the corresponding '
                                   '`magerr` must also be null.',
                       required=False, missing=None)

    magerr = fields.Field(description='Magnitude of the observation in the '
                                      'magnitude system `magsys`. '
                                      'Can be given as a scalar or a 1D list. '
                                      'If a scalar, will be broadcast to all values '
                                      'given as lists. Null values allowed for non-detections. '
                                      'If `magerr` is null, the corresponding `mag` '
                                      'must also be null.',
                          required=False, missing=None)

    limiting_mag = fields.Field(description='Limiting magnitude of the image '
                                            'in the magnitude system `magsys`. '
                                            'Can be given as a scalar or a 1D list. '
                                            'If a scalar, will be broadcast to all values '
                                            'given as lists. Null values not allowed.',
                                required=True)

    limiting_mag_nsigma = fields.Field(description='Number of standard deviations '
                                                   'above the background that the limiting '
                                                   'magnitudes correspond to. Null values '
                                                   'not allowed. Default = 5.',
                                       required=False, missing=5)


class PhotBase(object):
    """This is the base class of two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    PhotometryHandler.get`.
    """

    mjd = fields.Number(description='MJD of the observation.', required=True)
    magsys = ApispecEnumField(py_allowed_magsystems, required=True,
                              description='The magnitude system to which the '
                                          'flux and the zeropoint are tied.')
    filter = ApispecEnumField(py_allowed_bandpasses, required=True,
                              description='The bandpass of the observation.')

    obj_id = fields.String(description='ID of the Object to which the '
                                       'photometry will be attached.',
                           required=True)
    instrument_id = fields.Integer(description='ID of the instrument with which'
                                               ' the observation was carried '
                                               'out.', required=True)

    ra = fields.Number(description='ICRS Right Ascension of the centroid '
                                   'of the photometric aperture [deg].',
                       missing=None, default=None)
    dec = fields.Number(description='ICRS Declination of the centroid '
                                    'of the photometric aperture [deg].',
                        missing=None, default=None)

    ra_unc = fields.Number(description='Uncertainty on RA [arcsec].',
                           missing=None, default=None)

    dec_unc = fields.Number(description='Uncertainty on dec [arcsec].',
                            missing=None, default=None)

    alert_id = fields.Integer(description="Corresponding alert ID. If a record is "
                              "already present with identical alert ID, only the "
                              "groups list will be updated (other alert data assumed "
                              "identical). Defaults to None.",
                              missing=None, default=None)

    altdata = fields.Dict(description="Misc. alternative metadata stored in JSON "
                          "format, e.g. `{'calibration': {'source': 'ps1', "
                          "'color_term': 0.012}, 'photometry_method': 'allstar', "
                          "'method_reference': 'Masci et al. (2015)'}`",
                          missing=None, default=None)

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

    flux = fields.Number(description='Flux of the observation in counts. '
                                     'Can be null to accommodate upper '
                                     'limits from ZTF1, where no flux is measured '
                                     'for non-detections. If flux is null, '
                                     'the flux error is used to derive a '
                                     'limiting magnitude.', required=False,
                         missing=None, default=None)
    fluxerr = fields.Number(description='Gaussian error on the flux in counts.',
                            required=True)
    zp = fields.Number(description='Magnitude zeropoint, given by `ZP` in the '
                                   'equation m = -2.5 log10(flux) + `ZP`. '
                                   'm is the magnitude of the object in the '
                                   'magnitude system `magsys`.',
                       required=True)

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
            raise ValidationError(f"Instrument {instrument.name} has no filter "
                                  f"{data['filter']}.")

        # convert flux to microJanskies.
        table = Table([data])
        if data['flux'] is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table['flux'] = 0.

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP,
                                                     zpsys=PHOT_SYS)

        # replace with null if needed
        final_flux = None if data['flux'] is None else photdata.flux[0]

        p = Photometry(obj_id=data['obj_id'],
                       mjd=data['mjd'],
                       flux=final_flux,
                       fluxerr=photdata.fluxerr[0],
                       instrument_id=data['instrument_id'],
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

    mag = fields.Number(description='Magnitude of the observation in the '
                                    'magnitude system `magsys`. Can be null '
                                    'in the case of a non-detection.',
                        required=False, missing=None, default=None)
    magerr = fields.Number(description='Magnitude error of the observation in '
                                       'the magnitude system `magsys`. Can be '
                                       'null in the case of a non-detection.',
                           required=False, missing=None, default=None)
    limiting_mag = fields.Number(description='Limiting magnitude of the image '
                                             'in the magnitude system `magsys`.',
                                 required=True)

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
                all(
                    [
                        op(field, None) for field in [data['mag'], data['magerr']]
                    ]
                ) for op in [operator.is_, operator.is_not]
            ]
        )

        if not ok:
            raise ValidationError(f'Error parsing packet "{data}": mag '
                                  f'and magerr must both be null, or both be '
                                  f'not null.')

        # get the instrument
        instrument = Instrument.query.get(data['instrument_id'])
        if not instrument:
            raise ValidationError(f'Invalid instrument ID: {data["instrument_id"]}')

        # get the object
        obj = Obj.query.get(data['obj_id'])  # TODO: implement permissions checking
        if not obj:
            raise ValidationError(f'Invalid object ID: {data["obj_id"]}')

        if data["filter"] not in instrument.filters:
            raise ValidationError(f"Instrument {instrument.name} has no filter "
                                  f"{data['filter']}.")

        # determine if this is a limit or a measurement
        hasmag = data['mag'] is not None

        if hasmag:
            flux = 10**(-0.4 * (data['mag'] - PHOT_ZP))
            fluxerr = data['magerr'] / (2.5 / np.log(10)) * flux
        else:
            fivesigflux = 10**(-0.4 * (data['limiting_mag'] - PHOT_ZP))
            flux = None
            fluxerr = fivesigflux / 5

        # convert flux to microJanskies.
        table = Table([{'flux': flux,
                        'fluxerr': fluxerr,
                        'magsys': data['magsys'],
                        'zp': PHOT_ZP,
                        'filter': data['filter'],
                        'mjd': data['mjd']}])
        if flux is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table['flux'] = 0.

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP,
                                                     zpsys=PHOT_SYS)

        # replace with null if needed
        final_flux = None if flux is None else photdata.flux[0]

        p = Photometry(obj_id=data['obj_id'],
                       mjd=data['mjd'],
                       flux=final_flux,
                       fluxerr=photdata.fluxerr[0],
                       instrument_id=data['instrument_id'],
                       filter=data['filter'],
                       ra=data['ra'],
                       dec=data['dec'],
                       ra_unc=data['ra_unc'],
                       dec_unc=data['dec_unc'],
                       )
        if 'alert_id' in data and data['alert_id'] is not None:
            p.alert_id = data['alert_id']
        return p


def register_components(spec):
    print('Registering schemas with APISpec')

    schemas = inspect.getmembers(
        sys.modules[__name__],
        lambda m: isinstance(m, _Schema)
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

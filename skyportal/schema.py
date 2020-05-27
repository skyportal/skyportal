# This module acts as a placeholder for generated schema.  After
# `setup_schema` is run from `models`, each table will have an
# associated schema here.  E.g., `models.Dog` will be matched by `schema.Dog`.


# From
# https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models

from marshmallow_sqlalchemy import (
    ModelConversionError as _ModelConversionError,
    ModelSchema as _ModelSchema
)

from marshmallow import (Schema as _Schema, fields, validate)
from marshmallow_enum import EnumField

import sqlalchemy as sa
from sqlalchemy.orm import mapper

from baselayer.app.models import (
    Base as _Base,
    DBSession as _DBSession
)

from skyportal.enum import (
    py_allowed_bandpasses,
    py_allowed_magsystems,
    py_thumbnail_types
)

import sys
import inspect
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
            add_schema(f'{schema_class_name}NoID', exclude=['created_at', 'id', 'modified'])


class Bytes(fields.Field):
    """
    A Marshmallow Field that serializes bytes to a base64-encoded string, and deserializes
    a base64-encoded string to bytes.
    Args:
        - *args (Any): the arguments accepted by `marshmallow.Field`
        - **kwargs (Any): the keyword arguments accepted by `marshmallow.Field`
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):  # type: ignore
        if value is not None:
            return base64.b64encode(value).decode("utf-8")

    def _deserialize(self, value, attr, data, **kwargs):  # type: ignore
        if value is not None:
            return base64.b64decode(value)


class TypeMixin(object):
    ttype = ApispecEnumField(py_thumbnail_types, required=True,
                             description='Thumbnail type.')


class PhotometryThumbnailData(_Schema, TypeMixin):
    data = Bytes(description='Base64-encoded bytestring of thumbnail PNG image.'
                             'Only thumbnails between (16, 16) and (500, 500) '
                             'pixels are allowed.',
                 required=True)


class PhotometryThumbnailURL(_Schema, TypeMixin):
    url = fields.String(description='URL of the thumbnail PNG image.',
                        required=True)


class PhotBase(object):
    # Mixin class containing columns common to PhotometryFlux and PhotometryMag
    mjd = fields.Number(description='MJD of the observation.', required=True)
    magsys = ApispecEnumField(py_allowed_magsystems, required=True,
                              description='The magnitude system to which the '
                                          'flux and the zeropoint are tied.')
    filter = ApispecEnumField(py_allowed_bandpasses, required=True,
                              description='The bandpass of the observation.')

    obj_id = fields.Integer(description='ID of the Object to which the '
                                        'photometry will be attached.',
                            required=True)
    instrument_id = fields.Integer(description='ID of the instrument with which'
                                               ' the observation was carried '
                                               'out.', required=True)


class PhotometryFlux(_Schema, PhotBase):

    flux = fields.Number(description='Flux of the observation in counts. '
                                     'Can be null to accommodate upper '
                                     'limits from ZTF1, where no flux is measured '
                                     'for non-detections. If flux is null, '
                                     'the flux error is used to derive a '
                                     'limiting magnitude.', required=False)
    fluxerr = fields.Number(description='Gaussian error on the flux in counts.',
                            required=True)
    zp = fields.Number(description='Magnitude zeropoint, given by `ZP` in the '
                                   'equation m = -2.5 log10(flux) + `ZP`. '
                                   'm is the magnitude of the object in the '
                                   'magnitude system `zpsys`.',
                       required=True)

class PhotometryMag(_Schema, PhotBase):
    mag = fields.Number(description='Magnitude of the observation in the '
                                    'magnitude system `magsys`. Can be null '
                                    'in the case of a non-detection.',
                        required=False)
    magerr = fields.Number(description='Magnitude error of the observation in '
                                       'the magnitude system `magsys`. Can be '
                                       'null in the case of a non-detection.',
                           required=False)
    limiting_mag = fields.Number(description='Limiting magnitude of the image '
                                             'in the magnituee system `magsys`.',
                                 required=True)


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
PhotometryFlux = PhotometryFlux()
PhotometryMag = PhotometryMag()
PhotometryThumbnailURL = PhotometryThumbnailURL()
PhotometryThumbnailData = PhotometryThumbnailData()

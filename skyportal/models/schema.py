# This module acts as a placeholder for generated schema.  After
# `setup_schema` is run from `models`, each table will have an
# associated schema here.  E.g., `models.Dog` will be matched by `schema.Dog`.


# From
# https://marshmallow-sqlalchemy.readthedocs.io/en/latest/recipes.html#automatically-generating-schemas-for-sqlalchemy-models

import inspect
import operator
import sys
from enum import Enum

import numpy as np
from astropy.table import Table
from marshmallow import (
    Schema as _Schema,
)
from marshmallow import (
    ValidationError,
    fields,
    post_load,
    pre_dump,
    validate,
)
from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import (
    ModelConversionError as _ModelConversionError,
)
from marshmallow_sqlalchemy import (
    SQLAlchemyAutoSchema as _SQLAlchemyAutoSchema,
)

from baselayer.app.env import load_env
from baselayer.app.models import Base as _Base
from baselayer.app.models import DBSession as _DBSession
from skyportal.enum_types import (
    ALLOWED_BANDPASSES,
    ALLOWED_MAGSYSTEMS,
    ALLOWED_SPECTRUM_TYPES,
    default_spectrum_type,
    force_render_enum_markdown,
    py_allowed_bandpasses,
    py_allowed_magsystems,
    py_followup_priorities,
)

_, cfg = load_env()
# The default lim mag n-sigma to consider a photometry point as a detection
PHOT_DETECTION_THRESHOLD = cfg["misc.photometry_detection_threshold_nsigma"]


def validate_fluxerr(fluxerr):
    try:
        if isinstance(fluxerr, float | int | str):
            return float(fluxerr) >= 0
        return all(float(el) >= 0 for el in fluxerr)
    except ValueError:
        raise ValidationError("fluxerr must be a number or list of numbers")


class ApispecEnumField(EnumField):
    """See https://github.com/justanr/marshmallow_enum/issues/24#issue-335162592"""

    def __init__(self, enum, *args, **kwargs):
        super().__init__(enum, *args, **kwargs)
        self.metadata["enum"] = [e.name for e in enum]


class Response(_Schema):
    status = ApispecEnumField(Enum("status", ["error", "success"]), required=True)
    message = fields.String()
    data = fields.Dict()


class Error(Response):
    status = ApispecEnumField(Enum("status", ["error"]), required=True)


class newsFeedPrefs(_Schema):
    numItems = fields.String()


class UserPreferences(_Schema):
    newsFeed = fields.Nested(newsFeedPrefs)


class UpdateUserPreferencesRequestJSON(_Schema):
    preferences = fields.Nested(UserPreferences)


def success(schema_name, base_schema=None):
    schema_fields = {
        "status": ApispecEnumField(Enum("status", ["success"]), required=True),
        "message": fields.String(),
    }

    if base_schema is not None:
        if isinstance(base_schema, list):
            schema_fields["data"] = fields.List(
                fields.Nested(base_schema[0]),
            )
        else:
            schema_fields["data"] = fields.Nested(base_schema)

    return type(schema_name, (_Schema,), schema_fields)


def setup_schema():
    """For each model, install a marshmallow schema generator as
    `model.__schema__()`, and add an entry to the `schema`
    module.

    """
    # for class_ in _Base._decl_class_registry.values():
    for mapper in _Base.registry.mappers:
        class_ = mapper.class_
        if hasattr(class_, "__tablename__"):
            if class_.__name__.endswith("Schema"):
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
                    f"{schema_class_name}_meta",
                    (),
                    {
                        "model": class_,
                        "sqla_session": _DBSession,
                        "load_instance": True,
                        "ordered": True,
                        "exclude": [],
                        "include_fk": True,
                        "include_relationships": True,
                    },
                )
                for exclude_attr in exclude:
                    if (
                        hasattr(class_, exclude_attr)
                        and getattr(class_, exclude_attr) is not None
                    ):
                        schema_class_meta.exclude.append(exclude_attr)

                schema_class = type(
                    schema_class_name,
                    (_SQLAlchemyAutoSchema,),
                    {"Meta": schema_class_meta},
                )

                if add_to_model:
                    setattr(class_, "__schema__", schema_class)

                setattr(sys.modules[__name__], schema_class_name, schema_class())

            schema_class_name = class_.__name__
            add_schema(
                schema_class_name,
                exclude=["time_interval", "healpix", "created_at", "modified"],
                add_to_model=True,
            )
            add_schema(
                f"{schema_class_name}NoID",
                exclude=[
                    "created_at",
                    "id",
                    "modified",
                    "owner_id",
                    "last_modified_by_id",
                    "healpix",
                    "time_interval",
                ],
            )
            if schema_class_name == "Obj":
                add_schema(
                    f"{schema_class_name}Post",
                    exclude=[
                        "created_at",
                        "redshift_history",
                        "modified",
                        "internal_key",
                    ],
                )


class PhotBaseFlexible:
    """This is the base class for two classes that are used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    mjd = fields.Raw(
        metadata={
            "description": (
                "MJD of the observation(s). Can be a given as a "
                "scalar or a 1D list. If a scalar, will be "
                "broadcast to all values given as lists. "
                "Null values not allowed."
            ),
        },
        required=True,
    )

    filter = fields.Raw(
        required=True,
        metadata={
            "description": (
                "The bandpass of the observation(s). "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values not allowed. Allowed values: "
                f"{force_render_enum_markdown(ALLOWED_BANDPASSES)}"
            )
        },
    )

    obj_id = fields.Raw(
        metadata={
            "description": (
                "ID of the `Obj`(s) to which the "
                "photometry will be attached. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values are not allowed."
            )
        },
        required=True,
    )

    instrument_id = fields.Raw(
        metadata={
            "description": (
                "ID of the `Instrument`(s) with which the "
                "photometry was acquired. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values are not allowed."
            ),
        },
        required=True,
    )

    assignment_id = fields.Integer(
        metadata={
            "description": "ID of the classical assignment which generated the photometry"
        },
        required=False,
        load_default=None,
    )

    ra = fields.Raw(
        metadata={
            "description": (
                "ICRS Right Ascension of the centroid "
                "of the photometric aperture [deg]. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values allowed."
            )
        },
        required=False,
        load_default=None,
    )

    dec = fields.Raw(
        metadata={
            "description": (
                "ICRS Declination of the centroid "
                "of the photometric aperture [deg]. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values allowed."
            )
        },
        required=False,
        load_default=None,
    )

    ra_unc = fields.Raw(
        metadata={
            "description": "Uncertainty on RA [arcsec]. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
    )

    dec_unc = fields.Raw(
        metadata={
            "description": "Uncertainty on dec [arcsec]. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
    )

    origin = fields.Raw(
        metadata={
            "description": "Provenance of the Photometry. If a record is "
            "already present with identical origin, only the "
            "groups or streams list will be updated (other data assumed "
            "identical). Defaults to None."
        },
        load_default=None,
    )

    group_ids = fields.Raw(
        metadata={
            "description": "List of group IDs to which photometry points will be visible. "
            "If 'all', will be shared with site-wide public group (visible to all users "
            "who can view associated source)."
        },
        required=False,
        load_default=[],
    )

    stream_ids = fields.Raw(
        metadata={
            "description": "List of stream IDs to which photometry points will be visible."
        },
        required=False,
        load_default=[],
    )

    altdata = fields.Dict(
        metadata={
            "description": (
                "Misc. alternative metadata stored in JSON "
                "format, e.g. `{'calibration': {'source': 'ps1',"
                "'color_term': 0.012}, 'photometry_method': 'allstar', "
                "'method_reference': 'Masci et al. (2015)'}`. Can be a list of "
                "dicts or a single dict which will be broadcast to all values."
            )
        },
        load_default=None,
        dump_default=None,
        required=False,
    )


class PhotFluxFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = [
        "magsys",
        "mjd",
        "filter",
        "obj_id",
        "instrument_id",
        "fluxerr",
        "zp",
    ]

    magsys = fields.Raw(
        required=True,
        metadata={
            "description": (
                "The magnitude system to which the flux, flux error, "
                "and the zeropoint are tied. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values not allowed. Allowed values: "
                f"{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}"
            ),
        },
    )

    flux = fields.Raw(
        metadata={
            "description": (
                "Flux of the observation(s) in counts. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. Null values allowed, to accommodate,"
                "e.g., upper limits from ZTF1, where flux is not provided "
                "for non-detections. For a given photometry "
                "point, if `flux` is null, `fluxerr` is "
                "used to derive a n-sigma limiting magnitude "
                "(where n is configurable; 3.0 by default) "
                "when the photometry point is requested in "
                "magnitude space from the Photomety GET api."
            ),
        },
        required=False,
        load_default=None,
    )

    fluxerr = fields.Raw(
        metadata={
            "description": "Gaussian error on the flux in counts. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values not allowed."
        },
        required=True,
        validate=validate_fluxerr,
    )

    zp = fields.Raw(
        metadata={
            "description": "Magnitude zeropoint, given by `zp` in the "
            "equation `m = -2.5 log10(flux) + zp`. "
            "`m` is the magnitude of the object in the "
            "magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "Null values not allowed."
        },
        required=True,
    )

    ref_flux = fields.Raw(
        metadata={
            "description": (
                "Flux of the reference image in counts. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. "
                "Null values allowed if no reference is given. "
            ),
        },
        required=False,
        load_default=None,
    )

    ref_fluxerr = fields.Raw(
        metadata={
            "description": "Gaussian error on the reference flux in counts. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
        validate=validate_fluxerr,
    )

    ref_zp = fields.Raw(
        metadata={
            "description": "Magnitude zeropoint for the reference flux, "
            "given by `zp` in the "
            "equation `m = -2.5 log10(flux) + zp`. "
            "`m` is the magnitude of the object in the "
            "magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "If Null or not given, will be set to the "
            "default zeropoint of 23.9. "
        },
        required=False,
    )


class PhotMagFlexible(_Schema, PhotBaseFlexible):
    """This is one of two classes used for rendering the
    input data to `PhotometryHandler.post` in redoc. These classes are only
    used for generating documentation and not for validation, serialization,
    or deserialization."""

    required_keys = [
        "magsys",
        "limiting_mag",
        "mjd",
        "filter",
        "obj_id",
        "instrument_id",
    ]

    magsys = fields.Raw(
        required=True,
        metadata={
            "description": "The magnitude system to which the magnitude, "
            "magnitude error, and limiting magnitude are tied. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values not allowed. Allowed values: "
            f"{force_render_enum_markdown(ALLOWED_MAGSYSTEMS)}"
        },
    )

    mag = fields.Raw(
        metadata={
            "description": "Magnitude of the observation in the "
            "magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed for non-detections. "
            "If `mag` is null, the corresponding "
            "`magerr` must also be null."
        },
        required=False,
        load_default=None,
    )

    magerr = fields.Raw(
        metadata={
            "description": "Error on the magnitude in the "
            "magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed for non-detections. "
            "If `magerr` is null, the corresponding `mag` "
            "must also be null."
        },
        required=False,
        load_default=None,
    )

    limiting_mag = fields.Raw(
        metadata={
            "description": "Limiting magnitude of the image "
            "in the magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values not allowed."
        },
        required=True,
    )

    limiting_mag_nsigma = fields.Raw(
        metadata={
            "description": "Number of standard deviations "
            "above the background that the limiting "
            "magnitudes correspond to. Null values "
            f"not allowed. Default = {PHOT_DETECTION_THRESHOLD}."
        },
        required=False,
        load_default=PHOT_DETECTION_THRESHOLD,
    )

    magref = fields.Raw(
        metadata={
            "description": (
                "Magnitude of the reference image. "
                "in the magnitude system `magsys`. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. "
                "Null values allowed if no reference is given. "
            ),
        },
        required=False,
        load_default=None,
    )

    e_magref = fields.Raw(
        metadata={
            "description": "Gaussian error on the reference magnitude. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
    )


class PhotBase:
    """This is the base class of two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    PhotometryHandler.get`.
    """

    mjd = fields.Float(
        metadata={"description": "MJD of the observation."}, required=True
    )
    magsys = ApispecEnumField(
        py_allowed_magsystems,
        required=True,
        metadata={
            "description": "The magnitude system to which the "
            "flux and the zeropoint are tied."
        },
    )
    filter = ApispecEnumField(
        py_allowed_bandpasses,
        required=True,
        metadata={"description": "The bandpass of the observation."},
    )

    obj_id = fields.String(
        metadata={
            "description": "ID of the Object to which the photometry will be attached."
        },
        required=True,
    )

    instrument_id = fields.Integer(
        metadata={
            "description": "ID of the instrument with which"
            " the observation was carried "
            "out."
        },
        required=True,
    )

    assignment_id = fields.Integer(
        metadata={
            "description": "ID of the classical assignment which generated the photometry"
        },
        required=False,
        load_default=None,
    )

    origin = fields.Raw(
        metadata={
            "description": (
                "Provenance of the Photometry. If a record is "
                "already present with identical origin, only the "
                "groups or streams list will be updated (other data assumed "
                "identical). Defaults to None."
            )
        },
        load_default=None,
    )

    ra = fields.Float(
        metadata={
            "description": (
                "ICRS Right Ascension of the centroid "
                "of the photometric aperture [deg]."
            )
        },
        load_default=None,
        dump_default=None,
    )
    dec = fields.Float(
        metadata={
            "description": "ICRS Declination of the centroid "
            "of the photometric aperture [deg]."
        },
        load_default=None,
        dump_default=None,
    )

    ra_unc = fields.Float(
        metadata={"description": "Uncertainty on RA [arcsec]."},
        load_default=None,
        dump_default=None,
    )

    dec_unc = fields.Float(
        metadata={"description": "Uncertainty on dec [arcsec]."},
        load_default=None,
        dump_default=None,
    )

    alert_id = fields.Integer(
        metadata={
            "description": (
                "Corresponding alert ID. If a record is "
                "already present with identical alert ID, only the "
                "groups list will be updated (other alert data assumed "
                "identical). Defaults to None."
            )
        },
        load_default=None,
        dump_default=None,
    )

    altdata = fields.Dict(
        metadata={
            "description": (
                "Misc. alternative metadata stored in JSON "
                "format, e.g. `{'calibration': {'source': 'ps1',"
                "'color_term': 0.012}, 'photometry_method': 'allstar', "
                "'method_reference': 'Masci et al. (2015)'}`"
            )
        },
        load_default=None,
        dump_default=None,
    )

    @post_load
    def enum_to_string(self, data, **kwargs):
        # convert enumified data back to strings
        data["filter"] = data["filter"].name
        data["magsys"] = data["magsys"].name
        return data


class PhotometryFlux(_Schema, PhotBase):
    """This is one of two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    PhotometryHandler.get`.
    """

    flux = fields.Float(
        metadata={
            "description": "Flux of the observation in counts. "
            "Can be null to accommodate upper "
            "limits from ZTF1, where no flux is measured "
            "for non-detections. If flux is null, "
            "the flux error is used to derive a "
            "limiting magnitude."
        },
        required=False,
        load_default=None,
        dump_default=None,
    )

    fluxerr = fields.Float(
        metadata={"description": "Gaussian error on the flux in counts."}, required=True
    )

    zp = fields.Float(
        metadata={
            "description": "Magnitude zeropoint, given by `ZP` in the "
            "equation m = -2.5 log10(flux) + `ZP`. "
            "m is the magnitude of the object in the "
            "magnitude system `magsys`."
        },
        required=True,
    )

    ref_flux = fields.Raw(
        metadata={
            "description": (
                "Flux of the reference image in counts. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. "
                "Null values allowed if no reference is given. "
            ),
        },
        required=False,
        load_default=None,
    )

    ref_fluxerr = fields.Raw(
        metadata={
            "description": "Gaussian error on the reference flux in counts. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
        validate=validate_fluxerr,
    )

    ref_zp = fields.Raw(
        metadata={
            "description": "Magnitude zeropoint of the reference image, "
            "given by `ZP` in the equation m = -2.5 log10(flux) + `ZP`. "
            "m is the magnitude of the object in the "
            "magnitude system `magsys`. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values assume the "
            "standard zero point of 23.9. "
        },
        required=False,
        load_default=None,
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

        from sncosmo.photdata import PhotometricData

        from skyportal.models import PHOT_SYS, PHOT_ZP, Instrument, Obj, Photometry

        # get the instrument
        instrument = Instrument.query.get(data["instrument_id"])
        if not instrument:
            raise ValidationError(f"Invalid instrument ID: {data['instrument_id']}")

        # get the object
        obj = Obj.query.get(data["obj_id"])  # TODO : implement permissions checking
        if not obj:
            raise ValidationError(f"Invalid object ID: {data['obj_id']}")

        if data["filter"] not in instrument.filters:
            raise ValidationError(
                f"Instrument {instrument.name} has no filter {data['filter']}."
            )

        # convert flux to microJanskies.
        table = Table([data])
        if data["flux"] is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table["flux"] = 0.0

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP, zpsys=PHOT_SYS)

        # replace with null if needed
        final_flux = None if data["flux"] is None else photdata.flux[0]

        if data.get("ref_flux") is not None and data.get("ref_fluxerr") is not None:
            ref_flux = data["ref_flux"]
            ref_fluxerr = data["ref_fluxerr"]

            if "ref_zp" in data and data["ref_zp"] is not None:
                ref_zp = data["ref_zp"]
            else:
                ref_zp = PHOT_ZP

            ref_table = Table(
                [
                    {
                        "flux": ref_flux,
                        "fluxerr": ref_fluxerr,
                        "magsys": data["magsys"],
                        "zp": ref_zp,
                        "filter": data["filter"],
                        "mjd": data["mjd"],
                    }
                ]
            )

            # conversion of reference flux happens here
            ref_photdata = PhotometricData(ref_table).normalized(
                zp=PHOT_ZP, zpsys=PHOT_SYS
            )
            ref_flux = ref_photdata.flux[0]
            ref_fluxerr = ref_photdata.fluxerr[0]
        else:
            ref_flux = None
            ref_fluxerr = None

        p = Photometry(
            obj_id=data["obj_id"],
            mjd=data["mjd"],
            flux=final_flux,
            fluxerr=photdata.fluxerr[0],
            instrument_id=data["instrument_id"],
            assignment_id=data["assignment_id"],
            filter=data["filter"],
            ra=data["ra"],
            dec=data["dec"],
            ra_unc=data["ra_unc"],
            dec_unc=data["dec_unc"],
            ref_flux=ref_flux,
            ref_fluxerr=ref_fluxerr,
        )
        if "alert_id" in data and data["alert_id"] is not None:
            p.alert_id = data["alert_id"]
        return p


class PhotometryMag(_Schema, PhotBase):
    """This is one of  two classes that are used for deserializing
    and validating the postprocessed input data of `PhotometryHandler.post`
    and `PhotometryHandler.put` and for generating the API docs of
    `PhotometryHandler.get`.
    """

    mag = fields.Float(
        metadata={
            "description": "Magnitude of the observation in the "
            "magnitude system `magsys`. Can be null "
            "in the case of a non-detection."
        },
        required=False,
        load_default=None,
        dump_default=None,
    )
    magerr = fields.Float(
        metadata={
            "description": "Magnitude error of the observation in "
            "the magnitude system `magsys`. Can be "
            "null in the case of a non-detection."
        },
        required=False,
        load_default=None,
        dump_default=None,
    )
    limiting_mag = fields.Float(
        metadata={
            "description": "Limiting magnitude of the image "
            "in the magnitude system `magsys`."
        },
        required=True,
    )
    magref = fields.Raw(
        metadata={
            "description": (
                "Magnitude of the reference image. "
                "in the magnitude system `magsys`. "
                "Can be given as a scalar or a 1D list. "
                "If a scalar, will be broadcast to all values "
                "given as lists. "
                "Null values allowed if no reference is given. "
            ),
        },
        required=False,
        load_default=None,
    )

    e_magref = fields.Raw(
        metadata={
            "description": "Gaussian error on the reference magnitude. "
            "Can be given as a scalar or a 1D list. "
            "If a scalar, will be broadcast to all values "
            "given as lists. Null values allowed."
        },
        required=False,
        load_default=None,
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

        from sncosmo.photdata import PhotometricData

        from skyportal.models import PHOT_SYS, PHOT_ZP, Instrument, Obj, Photometry

        # check that mag and magerr are both null or both not null, not a mix
        ok = any(
            all(op(field, None) for field in [data["mag"], data["magerr"]])
            for op in [operator.is_, operator.is_not]
        )

        if not ok:
            raise ValidationError(
                f'Error parsing packet "{data}": mag '
                f"and magerr must both be null, or both be "
                f"not null."
            )

        # get the instrument
        instrument = Instrument.query.get(data["instrument_id"])
        if not instrument:
            raise ValidationError(f"Invalid instrument ID: {data['instrument_id']}")

        # get the object
        obj = Obj.query.get(data["obj_id"])  # TODO: implement permissions checking
        if not obj:
            raise ValidationError(f"Invalid object ID: {data['obj_id']}")

        if "mjd" not in data or data["mjd"] is None:
            raise ValidationError("mjd must be provided and non-null.")

        if data["filter"] not in instrument.filters:
            raise ValidationError(
                f"Instrument {instrument.name} has no filter {data['filter']}."
            )

        if data["mag"] is not None:  # measurement
            flux = 10 ** (-0.4 * (data["mag"] - PHOT_ZP))
            fluxerr = data["magerr"] / (2.5 / np.log(10)) * flux
        else:  # upper limit
            nsigflux = 10 ** (-0.4 * (data["limiting_mag"] - PHOT_ZP))
            flux = None
            fluxerr = nsigflux / PHOT_DETECTION_THRESHOLD

        # convert flux to microJanskies.
        table = Table(
            [
                {
                    "flux": flux,
                    "fluxerr": fluxerr,
                    "magsys": data["magsys"],
                    "zp": PHOT_ZP,
                    "filter": data["filter"],
                    "mjd": data["mjd"],
                }
            ]
        )
        if flux is None:
            # this needs to be non-null for the conversion step
            # will be replaced later with null
            table["flux"] = 0.0

        # conversion happens here
        photdata = PhotometricData(table).normalized(zp=PHOT_ZP, zpsys=PHOT_SYS)

        if data.get("magref") is not None and data.get("e_magref") is not None:
            ref_flux = 10 ** (-0.4 * (data["magref"] - PHOT_ZP))
            ref_fluxerr = data["e_magref"] * ref_flux * np.log(10) / 2.5

            ref_table = Table(
                [
                    {
                        "flux": ref_flux,
                        "fluxerr": ref_fluxerr,
                        "magsys": data["magsys"],
                        "zp": PHOT_ZP,
                        "filter": data["filter"],
                        "mjd": data["mjd"],
                    }
                ]
            )

            # conversion of reference flux happens here
            ref_photdata = PhotometricData(ref_table).normalized(
                zp=PHOT_ZP, zpsys=PHOT_SYS
            )
            ref_flux = ref_photdata.flux[0]
            ref_fluxerr = ref_photdata.fluxerr[0]

        else:
            ref_flux = None
            ref_fluxerr = None

        # replace with null if needed
        final_flux = None if flux is None else photdata.flux[0]

        p = Photometry(
            obj_id=data["obj_id"],
            mjd=data["mjd"],
            flux=final_flux,
            fluxerr=photdata.fluxerr[0],
            ref_flux=ref_flux,
            ref_fluxerr=ref_fluxerr,
            instrument_id=data["instrument_id"],
            assignment_id=data["assignment_id"],
            filter=data["filter"],
            ra=data["ra"],
            dec=data["dec"],
            ra_unc=data["ra_unc"],
            dec_unc=data["dec_unc"],
        )
        if "alert_id" in data and data["alert_id"] is not None:
            p.alert_id = data["alert_id"]
        return p


class AssignmentSchema(_Schema):
    # For generating API docs and extremely basic validation

    run_id = fields.Integer(required=True)
    obj_id = fields.String(
        required=True, metadata={"description": "The ID of the object to observe."}
    )
    priority = ApispecEnumField(
        py_followup_priorities,
        required=True,
        metadata={
            "description": ("Priority of the request, (lowest = 1, highest = 5).")
        },
    )
    status = fields.String(metadata={"description": "The status of the request"})
    comment = fields.String(
        metadata={"description": "An optional comment describing the request."}
    )


class ObservationHandlerPost(_Schema):
    telescopeName = fields.String(
        required=True,
        metadata={"description": ("The telescope name associated with the fields")},
    )
    instrumentName = fields.String(
        required=True,
        metadata={"description": ("The instrument name associated with the fields")},
    )
    observationData = fields.Dict(
        metadata={"description": "Observation data dictionary list"}
    )


class ObservationExternalAPIHandlerPost(_Schema):
    start_date = fields.Raw(
        required=True, metadata={"description": "start date of the request."}
    )

    end_date = fields.Raw(
        required=True, metadata={"description": "end date of the request."}
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Followup request allocation ID."},
    )


class SkymapQueueAPIHandlerPost(_Schema):
    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Followup request allocation ID."},
    )

    localization_id = fields.Integer(
        required=True,
        metadata={"description": "Localization ID."},
    )

    integrated_probability = fields.Float(
        required=False,
        metadata={"description": "Integrated probability within skymap."},
    )


class ObservationASCIIFileHandlerPost(_Schema):
    instrumentID = fields.String(
        required=True,
        metadata={"description": ("The instrument ID associated with the fields")},
    )
    observationData = fields.Dict(
        metadata={"description": "Observation data Ascii string"}
    )


class ObservingRunPost(_Schema):
    instrument_id = fields.Integer(
        required=True,
        metadata={"description": ("The ID of the instrument to be used in this run.")},
    )

    # name of the PI
    pi = fields.String(metadata={"description": "The PI of the observing run."})
    observers = fields.String(metadata={"description": "The names of the observers"})
    duration = fields.Integer(
        metadata={"description": "Number of nights in the observing run"}
    )
    group_id = fields.Integer(
        metadata={"description": "The ID of the group this run is associated with."}
    )
    calendar_date = fields.Date(
        metadata={"description": "The local calendar date of the run."}, required=True
    )


class GcnHandlerPut(_Schema):
    dateobs = fields.Raw(metadata={"description": "UTC event timestamp"})
    xml = fields.String(metadata={"description": "VOEvent XML content."})
    json = fields.String(metadata={"description": "JSON notice content."})


class GcnEventHandlerGet(_Schema):
    tags = fields.List(fields.Raw(), metadata={"description": "Event tags"})
    dateobs = fields.Raw(metadata={"description": "UTC event timestamp"})
    localizations = fields.List(
        fields.Raw(), metadata={"description": "Healpix localizations"}
    )
    notices = fields.List(fields.Raw(), metadata={"description": "VOEvent XML notices"})
    lightcurve = fields.String(metadata={"description": "URL for light curve"})


class GcnEventTagPost(_Schema):
    dateobs = fields.Raw(metadata={"description": "UTC event timestamp"})
    text = fields.String(metadata={"description": "GCN Event tag"})


class LocalizationHandlerGet(_Schema):
    localization_name = fields.String(metadata={"description": "Localization name"})
    dateobs = fields.String(metadata={"description": "UTC event timestamp"})
    flat_2d = fields.List(
        fields.Float, metadata={"description": "Flattened 2D healpix map"}
    )
    contour = fields.Raw(metadata={"description": "GeoJSON contours of healpix map"})


class GcnEventViewsHandlerGet(_Schema):
    tags = fields.List(fields.Raw(), metadata={"description": "Event list"})


class FollowupRequestPost(_Schema):
    obj_id = fields.String(
        required=True,
        metadata={"description": "ID of the target Obj."},
    )

    payload = fields.Dict(
        required=False, metadata={"description": "Content of the followup request."}
    )

    status = fields.String(
        load_default="pending submission",
        metadata={"description": "The status of the request."},
        required=False,
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Followup request allocation ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the followup request with."
            )
        },
    )

    not_if_duplicates = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If true, the followup request will not be executed if the object already has a pending or completed request of the same allocation."
            )
        },
    )

    source_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to which there must be a source for the object associated with the followup request."
            )
        },
    )

    not_if_classified = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If true, the followup request will not be executed if there are any sources within radius with (human-only) classifications."
            )
        },
    )

    not_if_spectra_exist = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If true, the followup request will not be executed if there are any sources within radius that have spectra."
            )
        },
    )

    not_if_tns_classified = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If true, the followup request will not be executed if any object within radius is already classified as SN in TNS."
            )
        },
    )

    not_if_tns_reported = fields.Float(
        required=False,
        metadata={
            "description": (
                "If there are any sources within radius with TNS reports, and the source has been discovered within before this many hours from the current time, the followup request will not be executed."
            )
        },
    )

    not_if_assignment_exists = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If there are any sources within radius that are assigned to an observing run, the followup request will not be executed."
            )
        },
    )

    ignore_source_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "If there are any sources within radius saved to any of these groups, the followup request will not be executed."
            )
        },
    )

    radius = fields.Float(
        required=False,
        metadata={"description": "Radius of to use when checking constraints."},
    )

    ignore_allocation_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "If there are any existing requests from the allocations that are pending or completed, the followup request will not be executed."
            )
        },
    )


class ObservationPlanPost(_Schema):
    gcnevent_id = fields.Integer(
        required=True,
        metadata={"description": "ID of the GcnEvent."},
    )

    payload = fields.Dict(
        required=False,
        metadata={"description": "Content of the observation plan request."},
    )

    status = fields.String(
        load_default="pending submission",
        metadata={"description": "The status of the request."},
        required=False,
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Observation plan request allocation ID."},
    )

    localization_id = fields.Integer(
        required=True,
        metadata={"description": "Localization ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the observation plan request with."
            )
        },
    )

    requester_id = fields.Integer(
        required=False,
        metadata={"description": "ID of the user making the request."},
    )


class ObservationPlanManualHandlerPost(_Schema):
    gcnevent_id = fields.Integer(
        required=True,
        metadata={"description": "ID of the GcnEvent."},
    )

    status = fields.String(
        load_default="pending submission",
        metadata={"description": "The status of the request."},
        required=False,
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Observation plan request allocation ID."},
    )

    localization_id = fields.Integer(
        required=True,
        metadata={"description": "Localization ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the observation plan request with."
            )
        },
    )

    observation_plan_data = fields.Dict(
        metadata={"description": "Observation plan data json"}
    )


class CatalogQueryPost(_Schema):
    payload = fields.Dict(
        required=False,
        metadata={"description": "Content of the catalog query request."},
    )

    status = fields.String(
        load_default="pending submission",
        metadata={"description": "The status of the request."},
        required=False,
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Catalog query request allocation ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the observation plan request with."
            )
        },
    )


class DefaultGcnTagPost(_Schema):
    filters = fields.Raw(
        required=True,
        metadata={
            "description": "Filters to determine which of the default gcn tags get executed for which events"
        },
    )

    default_tag_name = fields.String(
        required=True,
        metadata={"description": "Default tag name."},
    )


class DefaultObservationPlanPost(_Schema):
    payload = fields.Dict(
        required=False,
        metadata={"description": "Content of the default observation plan request."},
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Observation plan request allocation ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the default observation plan request with."
            )
        },
    )


class DefaultFollowupRequestPost(_Schema):
    payload = fields.Dict(
        required=False,
        metadata={"description": "Content of the default follow-up request."},
    )

    allocation_id = fields.Integer(
        required=True,
        metadata={"description": "Follow-up request allocation ID."},
    )

    target_group_ids = fields.List(
        fields.Integer,
        required=False,
        metadata={
            "description": (
                "IDs of groups to share the results of the default follow-up request with."
            )
        },
    )


class DefaultSurveyEfficiencyPost(_Schema):
    payload = fields.Dict(
        required=False,
        metadata={"description": "Content of the default survey efficiency analysis."},
    )

    default_observationplan_request_id = fields.Integer(
        required=True,
        metadata={"description": "Default observation plan request ID."},
    )


class ObservingRunGet(ObservingRunPost):
    owner_id = fields.Integer(
        metadata={"description": "The User ID of the owner of this run."}
    )
    ephemeris = fields.Raw(metadata={"description": "Observing run ephemeris data."})
    id = fields.Integer(metadata={"description": "Unique identifier for the run."})

    @pre_dump
    def serialize(self, data, **kwargs):
        data.ephemeris = data.instrument.telescope.ephemeris(data.calendar_noon)
        return data


class ObservingRunGetWithAssignments(ObservingRunGet):
    assignments = fields.List(fields.Raw())
    instrument = fields.Raw()


class PhotometryRangeQuery(_Schema):
    instrument_ids = fields.List(
        fields.Integer,
        metadata={
            "description": (
                "IDs of the instruments to query "
                "for photometry from. If `None`, "
                "queries all instruments."
            )
        },
        required=False,
        load_default=None,
        dump_default=None,
    )

    min_date = fields.DateTime(
        required=False,
        metadata={
            "description": (
                "Query for photometry taken after "
                "this UT `DateTime`. For an "
                "open-ended interval use `None`."
            )
        },
        load_default=None,
        dump_default=None,
    )

    max_date = fields.DateTime(
        required=False,
        metadata={
            "description": (
                "Query for photometry taken before "
                "this UT `DateTime`. For an "
                "open-ended interval use `None`."
            )
        },
        load_default=None,
        dump_default=None,
    )


class SpectrumAsciiFileParseJSON(_Schema):
    wave_column = fields.Integer(
        load_default=0,
        metadata={
            "description": (
                "The 0-based index of the ASCII column corresponding "
                "to the wavelength values of the spectrum (default 0)."
            )
        },
    )
    flux_column = fields.Integer(
        load_default=1,
        metadata={
            "description": (
                "The 0-based index of the ASCII column corresponding to "
                "the flux values of the spectrum (default 1)."
            )
        },
    )
    fluxerr_column = fields.Integer(
        load_default=None,
        metadata={
            "description": (
                "The 0-based index of the ASCII column corresponding to the flux "
                "error values of the spectrum (default None). If a column for errors "
                "is provided, set to the corresponding 0-based column number, "
                "otherwise, it will be ignored."
            )
        },
    )

    ascii = fields.String(
        metadata={
            "description": """The content of the ASCII file to be parsed.

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

The data must be at least 2 column ascii (wavelength, flux). If flux errors are \
provided in an additional column, the column must be specified in the call. \
If more than 2 columns are given, by default the first two are interpreted as \
(wavelength, flux). The column indices of each of these arguments can be controlled \
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

"""
        },
        required=True,
    )


class SpectrumAsciiFilePostJSON(SpectrumAsciiFileParseJSON):
    obj_id = fields.String(
        metadata={"description": "The ID of the object that the spectrum is of."},
        required=True,
    )

    instrument_id = fields.Integer(
        metadata={"description": "The ID of the instrument that took the spectrum."},
        required=True,
    )

    type = fields.String(
        validate=validate.OneOf(ALLOWED_SPECTRUM_TYPES),
        required=False,
        metadata={
            "by_value": True,
            "description": f"""Type of spectrum. One of: {", ".join(f"'{t}'" for t in ALLOWED_SPECTRUM_TYPES)}.
                    Defaults to 'f{default_spectrum_type}'.""",
        },
    )

    label = fields.String(
        metadata={
            "description": "User defined label to be placed in plot legends, "
            "instead of the default <instrument>-<date taken>."
        },
        required=False,
    )

    observed_at = fields.DateTime(
        metadata={"description": "The ISO UTC time the spectrum was taken."},
        required=True,
    )

    group_ids = fields.List(
        fields.Integer,
        metadata={"description": "The IDs of the groups to share this spectrum with."},
    )

    filename = fields.String(
        metadata={"description": "The original filename (for bookkeeping purposes)."},
        required=True,
    )

    pi = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who are PI of this Spectrum, or to use as points of contact given an external PI."
        },
        load_default=[],
    )

    external_pi = fields.String(
        metadata={"description": "Free text provided as an external PI"},
        required=False,
        load_default=None,
    )

    reduced_by = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who reduced this Spectrum, or to use as points of contact given an external reducer."
        },
        load_default=[],
    )

    external_reducer = fields.String(
        metadata={"description": "Free text provided as an external reducer"},
        required=False,
        load_default=None,
    )

    observed_by = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who observed this Spectrum, or to use as points of contact given an external observer."
        },
        load_default=[],
    )

    external_observer = fields.String(
        metadata={"description": "Free text provided as an external observer"},
        required=False,
        load_default=None,
    )

    followup_request_id = fields.Integer(
        required=False,
        metadata={
            "description": (
                "ID of the Followup request that generated this spectrum, if any."
            )
        },
    )

    assignment_id = fields.Integer(
        required=False,
        metadata={
            "description": (
                "ID of the classical assignment that generated this spectrum, if any."
            )
        },
    )


class SpectrumPost(_Schema):
    wavelengths = fields.List(
        fields.Float,
        required=True,
        metadata={"description": "Wavelengths of the spectrum [Angstrom]."},
    )

    fluxes = fields.List(
        fields.Float,
        required=True,
        metadata={"description": "Flux of the Spectrum [F_lambda, arbitrary units]."},
    )

    errors = fields.List(
        fields.Float,
        metadata={
            "description": "Errors on the fluxes of the spectrum [F_lambda, same units as `fluxes`.]"
        },
    )

    units = fields.String(
        metadata={
            "description": "Units of the fluxes/errors. Options are Jy, AB, or erg/s/cm/cm/AA).",
        },
    )

    obj_id = fields.String(
        required=True,
        metadata={"description": "ID of this Spectrum's Obj."},
    )

    observed_at = fields.DateTime(
        metadata={"description": "The ISO UTC time the spectrum was taken."},
        required=True,
    )

    pi = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who are PI of this Spectrum, or to use as points of contact given an external PI."
        },
        load_default=[],
    )

    external_pi = fields.String(
        metadata={"description": "Free text provided as an external PI"},
        required=False,
        load_default=None,
    )

    reduced_by = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who reduced this Spectrum, or to use as points of contact given an external reducer."
        },
        load_default=[],
    )

    external_reducer = fields.String(
        metadata={"description": "Free text provided as an external reducer"},
        required=False,
        load_default=None,
    )

    observed_by = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who observed this Spectrum, or to use as points of contact given an external observer."
        },
        load_default=[],
    )

    external_observer = fields.String(
        metadata={"description": "Free text provided as an external observer"},
        required=False,
        load_default=None,
    )

    origin = fields.String(
        required=False, metadata={"description": "Origin of the spectrum."}
    )

    type = fields.String(
        validate=validate.OneOf(ALLOWED_SPECTRUM_TYPES),
        required=False,
        metadata={
            "description": f"""Type of spectrum. One of: {"".join(f"'{t}'" for t in ALLOWED_SPECTRUM_TYPES)}.
                         Defaults to 'f{default_spectrum_type}'."""
        },
    )

    label = fields.String(
        required=False,
        metadata={
            "description": "User defined label (can be used to replace default instrument/date labeling on plot legends)."
        },
    )

    instrument_id = fields.Integer(
        required=True,
        metadata={"description": "ID of the Instrument that acquired the Spectrum."},
    )

    group_ids = fields.Raw(
        load_default=[],
        metadata={
            "description": 'IDs of the Groups to share this spectrum with. Set to "all"'
            " to make this spectrum visible to all users."
        },
    )

    followup_request_id = fields.Integer(
        required=False,
        metadata={
            "description": "ID of the Followup request that generated this spectrum, "
            "if any."
        },
    )

    assignment_id = fields.Integer(
        required=False,
        metadata={
            "description": "ID of the classical assignment that generated this spectrum, "
            "if any."
        },
    )

    altdata = fields.Dict(
        metadata={"description": "Miscellaneous alternative metadata."}
    )


class SpectrumHead(_Schema):
    obj_id = fields.String(
        required=True,
        metadata={"description": "ID of this Spectrum's Obj."},
    )

    observed_at = fields.DateTime(
        metadata={"description": "The ISO UTC time the spectrum was taken."},
        required=True,
    )

    pi = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who are PI of this Spectrum, or to use as points of contact given an external PI."
        },
        load_default=[],
    )

    external_pi = fields.String(
        metadata={"description": "Free text provided as an external PI"},
        required=False,
        load_default=None,
    )

    reducers = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who reduced this Spectrum, "
            "or to use as points of contact given an external reducer."
        },
        load_default=[],
    )

    external_reducer = fields.String(
        metadata={"description": "Free text provided as an external reducer"},
        required=False,
        load_default=None,
    )

    observers = fields.List(
        fields.Integer,
        metadata={
            "description": "IDs of the Users who observed this Spectrum, "
            "or to use as points of contact given an external observer."
        },
        load_default=[],
    )

    external_observer = fields.String(
        metadata={"description": "Free text provided as an external observer"},
        required=False,
        load_default=None,
    )

    origin = fields.String(
        required=False, metadata={"description": "Origin of the spectrum."}
    )

    type = fields.String(
        validate=validate.OneOf(ALLOWED_SPECTRUM_TYPES),
        required=False,
        metadata={
            "description": f"""Type of spectrum. One of: {"".join(f"'{t}'" for t in ALLOWED_SPECTRUM_TYPES)}.
                         Defaults to 'f{default_spectrum_type}'."""
        },
    )

    label = fields.String(
        required=False,
        metadata={
            "description": "User defined label (can be used to replace default instrument/date labeling on plot legends)."
        },
    )

    instrument_id = fields.Integer(
        required=True,
        metadata={"description": "ID of the Instrument that acquired the Spectrum."},
    )
    instrument_name = fields.String(
        required=True,
        metadata={"description": "Name of the Instrument that acquired the Spectrum."},
    )

    group_ids = fields.Raw(
        load_default=[],
        metadata={
            "description": 'IDs of the Groups to share this spectrum with. Set to "all"'
            " to make this spectrum visible to all users."
        },
    )

    followup_request_id = fields.Integer(
        required=False,
        metadata={
            "description": "ID of the Followup request that generated this spectrum, "
            "if any."
        },
    )

    assignment_id = fields.Integer(
        required=False,
        metadata={
            "description": "ID of the classical assignment that generated this spectrum, "
            "if any."
        },
    )

    altdata = fields.Dict(
        metadata={"description": "Miscellaneous alternative metadata."}
    )


class MMADetectorSpectrumPost(_Schema):
    frequencies = fields.List(
        fields.Float,
        required=True,
        metadata={"description": "Frequencies of the spectrum [Hz]."},
    )

    amplitudes = fields.List(
        fields.Float,
        required=True,
        metadata={"description": "Amplitude of the Spectrum [1/sqrt(Hz)."},
    )

    start_time = fields.DateTime(
        metadata={"description": "The ISO UTC start time the spectrum was taken."},
        required=True,
    )

    end_time = fields.DateTime(
        metadata={"description": "The ISO UTC end time the spectrum was taken."},
        required=True,
    )

    detector_id = fields.Integer(
        required=True,
        metadata={"description": "ID of the MMADetector that acquired the Spectrum."},
    )

    group_ids = fields.Raw(
        load_default=[],
        metadata={
            "description": 'IDs of the Groups to share this spectrum with. Set to "all"'
            " to make this spectrum visible to all users."
        },
    )


class GroupIDList(_Schema):
    group_ids = fields.List(fields.Integer, required=True)


class GalaxyHandlerPost(_Schema):
    catalog_name = fields.String(
        metadata={"description": "Galaxy catalog name."}, required=True
    )
    catalog_description = fields.String(
        metadata={"description": "Galaxy catalog description."},
        required=False,
        load_default=None,
    )
    catalog_url = fields.String(
        metadata={"description": "Galaxy catalog URL."},
        required=False,
        load_default=None,
    )
    catalog_data = fields.List(
        fields.Dict(), metadata={"description": "Galaxy catalog data"}, required=True
    )


class GalaxyASCIIFileHandlerPost(_Schema):
    catalogName = fields.String(
        metadata={"description": "Galaxy catalog name."}, required=True
    )
    catalogDescription = fields.String(
        metadata={"description": "Galaxy catalog description."},
        required=False,
        load_default=None,
    )
    catalogURL = fields.String(
        metadata={"description": "Galaxy catalog URL."},
        required=False,
        load_default=None,
    )

    catalogData = fields.String(
        metadata={"description": "Catalog data Ascii string"}, required=True
    )


class SpatialCatalogHandlerPost(_Schema):
    catalog_name = fields.String(metadata={"description": "Spatial catalog name."})
    catalog_data = fields.List(
        fields.Dict(), metadata={"description": "Spatial catalog data"}
    )


class SpatialCatalogASCIIFileHandlerPost(_Schema):
    catalogName = fields.String(metadata={"description": "Spatial catalog name."})
    catalogData = fields.Dict(metadata={"description": "Catalog data Ascii string"})


def register_components(spec):
    print("Registering schemas with APISpec")

    schemas = inspect.getmembers(
        sys.modules[__name__], lambda m: isinstance(m, _Schema)
    )

    for name, schema in schemas:
        spec.components.schema(name, schema=schema)

        single = "Single" + name
        arrayOf = "ArrayOf" + name + "s"
        spec.components.schema(single, schema=success(single, schema))
        spec.components.schema(arrayOf, schema=success(arrayOf, [schema]))


# Replace schemas by instantiated versions
# These are picked up in `setup_schema` for the registry
Response = Response()
Error = Error()
Success = success("Success")
SinglePhotometryFlux = success("SinglePhotometryFlux", PhotometryFlux)
SinglePhotometryMag = success("SinglePhotometryMag", PhotometryMag)
CatalogQueryPost = CatalogQueryPost()
MMADetectorSpectrumPost = MMADetectorSpectrumPost()
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
FollowupRequestPost = FollowupRequestPost()
ObservationPlanPost = ObservationPlanPost()
ObservationExternalAPIHandlerPost = ObservationExternalAPIHandlerPost()
SpectrumAsciiFileParseJSON = SpectrumAsciiFileParseJSON()
SpectrumPost = SpectrumPost()
SpectrumHead = SpectrumHead()
GroupIDList = GroupIDList()

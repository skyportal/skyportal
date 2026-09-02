"""Response models for photometry."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.annotations import AnnotationDetailResponse
from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.streams import StreamResponse
from skyportal_py_models.users import UserResponse


class PhotometryValidationResponse(BaseModel):
    """A validated/rejected mark on a photometry point."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    photometry_id: int | None = None
    validated: bool | None = None
    validator_id: int | None = None
    explanation: str | None = None
    notes: str | None = None


class _SerializedPhotometryResponse(BaseModel):
    """A photometry point as built by the ``serialize`` helper."""

    # ``serialize`` never returns ``Photometry.to_dict()``: it hand-builds a
    # dict whose keys depend on the ``format`` query parameter. ``mag``,
    # ``magerr`` and ``limiting_mag`` are only present for ``format="mag"``,
    # ``flux``, ``fluxerr`` and ``zp`` only for ``format="flux"``, and both
    # sets for ``format="both"``. The ``ref_*``/``tot_*``/``mag(ref|tot)``
    # block is only present when the point has a reference flux, and the
    # ``extinction``/``mag_corr``/``flux_corr`` keys only when the caller
    # asked for extinction. ``groups``, ``annotations``, ``owner``,
    # ``streams`` and ``validations`` are each opt-in per endpoint, and the
    # ``owner``/``groups``/``streams`` entries are trimmed to a few columns.

    model_config = ConfigDict(extra="forbid")

    id: int
    obj_id: str | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    filter: str | None = None
    mjd: float | None = None
    snr: float | None = None
    instrument_id: int | None = None
    instrument_name: str | None = None
    origin: str | None = None
    # The duplicate-resolution upload path can leave the literal string
    # "NaN" in place of a point's altdata dict.
    altdata: dict[str, Any] | str | None = None
    created_at: datetime | None = None
    groups: list[GroupResponse] = Field(default_factory=list)
    annotations: list[AnnotationDetailResponse] = Field(default_factory=list)
    owner: UserResponse | None = None
    streams: list[StreamResponse] = Field(default_factory=list)
    validations: list[PhotometryValidationResponse] = Field(default_factory=list)
    magsys: str | None = None
    mag: float | None = None
    magerr: float | None = None
    limiting_mag: float | None = None
    flux: float | None = None
    fluxerr: float | None = None
    zp: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    tot_flux: float | None = None
    tot_fluxerr: float | None = None
    magref: float | None = None
    magtot: float | None = None
    e_magref: float | None = None
    e_magtot: float | None = None
    extinction: float | None = None
    mag_corr: float | None = None
    flux_corr: float | None = None


class PhotometryPointResponse(_SerializedPhotometryResponse):
    """A single photometry point of a source."""

    # ``GET /api/sources/{obj_id}/photometry`` returns individual photometry
    # points *and* the rows of the object's photometric series in one list, so
    # this model also carries the extra keys a series row has: ``instrument``
    # and ``telescope`` (names, not objects) and, when the caller asked to
    # phase-fold, ``phase``. ``format="plot"`` returns a strict subset.
    #
    # extra="allow" because a series row also carries whatever auxiliary
    # columns the uploaded data file had (PhotometricSeries.data is free-form);
    # forbidding them would reject valid payloads.
    model_config = ConfigDict(extra="allow")

    instrument: str | None = None
    telescope: str | None = None
    phase: float | None = None


class PhotometryRangePointResponse(_SerializedPhotometryResponse):
    """A photometry point as serialized by the date-range query."""


class PhotometryPost(BaseModel):
    """Payload for posting one or many photometry points.

    Provide either ``mag``/``magerr`` (magnitude space) or
    ``flux``/``fluxerr``/``zp`` (flux space). For non-detections, leave the
    measurement fields unset and provide ``limiting_mag``. Every measurement
    field also accepts a 1D list to upload many points at once; scalars are
    broadcast across the lists, and a None entry inside a ``mag``/``flux``
    list marks that point as a non-detection.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | list[str]
    mjd: float | list[float]
    instrument_id: int | list[int]
    filter: str | list[str]
    magsys: str | list[str] = "ab"
    mag: float | list[float | None] | None = None
    magerr: float | list[float | None] | None = None
    limiting_mag: float | list[float | None] | None = None
    limiting_mag_nsigma: float | list[float | None] | None = None
    magref: float | list[float | None] | None = None
    e_magref: float | list[float | None] | None = None
    flux: float | list[float | None] | None = None
    fluxerr: float | list[float | None] | None = None
    zp: float | list[float | None] | None = None
    ref_flux: float | list[float | None] | None = None
    ref_fluxerr: float | list[float | None] | None = None
    ref_zp: float | list[float | None] | None = None
    ra: float | list[float | None] | None = None
    dec: float | list[float | None] | None = None
    ra_unc: float | list[float | None] | None = None
    dec_unc: float | list[float | None] | None = None
    origin: str | list[str | None] | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | list[dict[str, Any] | None] | None = None
    extinction_corrected: bool | None = None
    group_ids: list[int] | Literal["all"] | None = None
    stream_ids: list[int] | None = None


class PhotometryUpdate(BaseModel):
    """Payload for updating an existing photometry point.

    Every field is optional: the server loads the point, applies the given
    fields, and re-validates the result as either a flux-space
    (``flux``/``fluxerr``/``zp``) or magnitude-space (``mag``/``magerr``)
    measurement. Only the fields explicitly set on the payload are sent, so
    passing ``None`` explicitly (e.g. ``mag=None, magerr=None`` to turn a
    detection into a non-detection) sends a null, while omitting a field
    leaves it unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = None
    mjd: float | None = None
    instrument_id: int | None = None
    filter: str | None = None
    magsys: str | None = None
    mag: float | None = None
    magerr: float | None = None
    limiting_mag: float | None = None
    magref: float | None = None
    e_magref: float | None = None
    flux: float | None = None
    fluxerr: float | None = None
    zp: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    ref_zp: float | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    origin: str | None = None
    alert_id: int | None = None
    assignment_id: int | None = None
    altdata: dict[str, Any] | None = None
    group_ids: list[int] | None = None
    stream_ids: list[int] | None = None


REFRESH_DESCRIPTION = (
    "If true, triggers a refresh of the object's photometry on the web page, "
    "only for the users that have the object's source page open."
)


class PhotometryGetQuery(BaseModel):
    """Query parameters for getting a single photometry point."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["mag", "flux", "both"] = Field(
        default="mag",
        description=(
            "Return the photometry in flux or magnitude space? "
            "If a value for this query parameter is not provided, the result "
            "will be returned in magnitude space."
        ),
    )
    magsys: Literal["jla1", "ab", "vega", "bd17", "csp", "ab-b12"] = Field(
        default="ab",
        description="The magnitude or zeropoint system of the output. (Default AB)",
    )


class PhotometryPostQuery(BaseModel):
    """Query parameters for uploading photometry."""

    model_config = ConfigDict(extra="forbid")

    refresh: bool = Field(default=False, description=REFRESH_DESCRIPTION)


class PhotometryPutQuery(BaseModel):
    """Query parameters for updating and/or uploading photometry."""

    model_config = ConfigDict(extra="forbid")

    refresh: bool = Field(default=False, description=REFRESH_DESCRIPTION)
    duplicate_ignore_flux: bool = Field(
        default=False,
        description=(
            "If true, will not use the flux/fluxerr of existing rows when looking "
            "for duplicates but only mjd, instrument_id, filter, and origin. "
            "Reserved to super admin users only, to avoid misuse and permanent "
            "data loss."
        ),
    )
    overwrite_flux: bool = Field(
        default=False,
        description=(
            "If true and duplicate_ignore_flux is also true, will update the "
            "flux/fluxerr of existing rows (duplicates) with the new values. "
            "Applies only to rows with an origin already specified. If existing "
            "duplicates have no origin, the update will be skipped."
        ),
    )


class PhotometryPatchQuery(BaseModel):
    """Query parameters for updating a photometry point."""

    model_config = ConfigDict(extra="forbid")

    refresh: bool = Field(default=False, description=REFRESH_DESCRIPTION)


# Per-field types are permissive unions (scalar-or-1D-list) because the bulk
# photometry payload broadcasts scalars across list-valued fields. This model
# only enforces the top-level shape + extra="forbid"; the deep validation
# (required fields, flux vs. mag space, finite/non-null checks, filter/magsys
# enums) is still done by the marshmallow PhotFluxFlexible/PhotMagFlexible
# schemas in standardize_photometry_data. Every field is optional here so those
# schemas keep emitting their exact error messages for missing/invalid fields.
class PhotometryFlexibleBody(BaseModel):
    """Request body for bulk photometry upload (POST/PUT).

    Union of the flux-space and magnitude-space payloads; a valid request must
    match one of them (enforced downstream by the marshmallow schemas).
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | int | list[str | int | None] | None = Field(
        default=None,
        description="ID of the `Obj`(s) to which the photometry will be "
        "attached. Can be given as a scalar or a 1D list. If a scalar, will be "
        "broadcast to all values given as lists. Null values are not allowed.",
    )
    mjd: float | list[float | None] | None = Field(
        default=None,
        description="MJD of the observation(s). Can be given as a scalar or a "
        "1D list. If a scalar, will be broadcast to all values given as lists. "
        "Null values not allowed.",
    )
    instrument_id: int | str | list[int | str | None] | None = Field(
        default=None,
        description="ID of the `Instrument`(s) with which the photometry was "
        "acquired. Can be given as a scalar or a 1D list. If a scalar, will be "
        "broadcast to all values given as lists. Null values are not allowed.",
    )
    filter: str | list[str | None] | None = Field(
        default=None,
        description="The bandpass of the observation(s). Can be given as a "
        "scalar or a 1D list. If a scalar, will be broadcast to all values "
        "given as lists. Null values not allowed.",
    )
    magsys: str | list[str | None] | None = Field(
        default=None,
        description="The magnitude system to which the flux/mag, error, and "
        "zeropoint are tied. Can be given as a scalar or a 1D list. If a "
        "scalar, will be broadcast to all values given as lists. Null values "
        "not allowed.",
    )
    assignment_id: int | None = Field(
        default=None,
        description="ID of the classical assignment which generated the photometry.",
    )
    ra: float | list[float | None] | None = Field(
        default=None,
        description="ICRS Right Ascension of the centroid of the photometric "
        "aperture [deg]. Can be given as a scalar or a 1D list. Null values "
        "allowed.",
    )
    dec: float | list[float | None] | None = Field(
        default=None,
        description="ICRS Declination of the centroid of the photometric "
        "aperture [deg]. Can be given as a scalar or a 1D list. Null values "
        "allowed.",
    )
    ra_unc: float | list[float | None] | None = Field(
        default=None,
        description="Uncertainty on RA [arcsec]. Can be given as a scalar or a "
        "1D list. Null values allowed.",
    )
    dec_unc: float | list[float | None] | None = Field(
        default=None,
        description="Uncertainty on dec [arcsec]. Can be given as a scalar or a "
        "1D list. Null values allowed.",
    )
    origin: str | list[str | None] | None = Field(
        default=None,
        description="Provenance of the Photometry. If a record is already "
        "present with identical origin, only the groups or streams list will be "
        "updated (other data assumed identical). Defaults to None.",
    )
    group_ids: list | str | None = Field(
        default=None,
        description="List of group IDs to which photometry points will be "
        "visible. If 'all', will be shared with sitewide public group (visible "
        "to all users who can view associated source).",
    )
    stream_ids: list | None = Field(
        default=None,
        description="List of stream IDs to which photometry points will be visible.",
    )
    altdata: dict | list | None = Field(
        default=None,
        description="Misc. alternative metadata stored in JSON format. Can be a "
        "list of dicts or a single dict which will be broadcast to all values.",
    )
    extinction_corrected: bool | str | None = Field(
        default=None,
        description="If true, input magnitudes are already MW-extinction "
        "corrected; SkyPortal re-reddens them so stored photometry stays "
        "observed. Defaults to false.",
    )
    flux: float | list[float | None] | None = Field(
        default=None,
        description="Flux of the observation(s) in counts. Can be given as a "
        "scalar or a 1D list. Null values allowed (e.g. upper limits, where "
        "fluxerr is used to derive a limiting magnitude).",
    )
    fluxerr: float | list[float | None] | None = Field(
        default=None,
        description="Gaussian error on the flux in counts. Can be given as a "
        "scalar or a 1D list. Null values not allowed.",
    )
    zp: float | list[float | None] | None = Field(
        default=None,
        description="Magnitude zeropoint, given by `zp` in the equation "
        "`m = -2.5 log10(flux) + zp`. Can be given as a scalar or a 1D list. "
        "Null values not allowed.",
    )
    ref_flux: float | list[float | None] | None = Field(
        default=None,
        description="Flux of the reference image in counts. Can be given as a "
        "scalar or a 1D list. Null values allowed if no reference is given.",
    )
    ref_fluxerr: float | list[float | None] | None = Field(
        default=None,
        description="Gaussian error on the reference flux in counts. Can be "
        "given as a scalar or a 1D list. Null values allowed.",
    )
    ref_zp: float | list[float | None] | None = Field(
        default=None,
        description="Magnitude zeropoint for the reference flux. Can be given as "
        "a scalar or a 1D list. If Null or not given, will be set to the default "
        "zeropoint of 23.9.",
    )
    mag: float | list[float | None] | None = Field(
        default=None,
        description="Magnitude of the observation in the magnitude system "
        "`magsys`. Can be given as a scalar or a 1D list. Null values allowed "
        "for non-detections. If `mag` is null, the corresponding `magerr` must "
        "also be null.",
    )
    magerr: float | list[float | None] | None = Field(
        default=None,
        description="Error on the magnitude in the magnitude system `magsys`. "
        "Can be given as a scalar or a 1D list. Null values allowed for "
        "non-detections. If `magerr` is null, the corresponding `mag` must also "
        "be null.",
    )
    limiting_mag: float | list[float | None] | None = Field(
        default=None,
        description="Limiting magnitude of the image in the magnitude system "
        "`magsys`. Can be given as a scalar or a 1D list. Null values not "
        "allowed.",
    )
    limiting_mag_nsigma: float | list[float | None] | None = Field(
        default=None,
        description="Number of standard deviations above the background that "
        "the limiting magnitudes correspond to. Null values not allowed.",
    )
    magref: float | list[float | None] | None = Field(
        default=None,
        description="Magnitude of the reference image in the magnitude system "
        "`magsys`. Can be given as a scalar or a 1D list. Null values allowed if "
        "no reference is given.",
    )
    e_magref: float | list[float | None] | None = Field(
        default=None,
        description="Gaussian error on the reference magnitude. Can be given as "
        "a scalar or a 1D list. Null values allowed.",
    )


class PhotometryPostBody(PhotometryFlexibleBody):
    """Request body for uploading photometry (POST)."""


class PhotometryPutBody(PhotometryFlexibleBody):
    """Request body for updating and/or uploading photometry (PUT)."""


class PhotometryPatchBody(BaseModel):
    """Request body for updating a single photometry point (PATCH).

    Single-point (scalar) counterpart of the bulk body; the deep validation is
    still done by the marshmallow PhotometryFlux/PhotometryMag schemas. Every
    field is optional so those schemas keep emitting their exact error messages.
    """

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(
        default=None,
        description="ID of the Object to which the photometry will be attached.",
    )
    mjd: float | None = Field(default=None, description="MJD of the observation.")
    instrument_id: int | None = Field(
        default=None,
        description="ID of the instrument with which the observation was carried out.",
    )
    filter: str | None = Field(
        default=None, description="The bandpass of the observation."
    )
    magsys: str | None = Field(
        default=None,
        description="The magnitude system to which the flux and the zeropoint "
        "are tied.",
    )
    assignment_id: int | None = Field(
        default=None,
        description="ID of the classical assignment which generated the photometry.",
    )
    alert_id: int | None = Field(
        default=None,
        description="Corresponding alert ID. If a record is already present with "
        "identical alert ID, only the groups list will be updated. Defaults to None.",
    )
    origin: str | None = Field(
        default=None,
        description="Provenance of the Photometry. If a record is already "
        "present with identical origin, only the groups or streams list will be "
        "updated (other data assumed identical). Defaults to None.",
    )
    ra: float | None = Field(
        default=None,
        description="ICRS Right Ascension of the centroid of the photometric "
        "aperture [deg].",
    )
    dec: float | None = Field(
        default=None,
        description="ICRS Declination of the centroid of the photometric "
        "aperture [deg].",
    )
    ra_unc: float | None = Field(
        default=None, description="Uncertainty on RA [arcsec]."
    )
    dec_unc: float | None = Field(
        default=None, description="Uncertainty on dec [arcsec]."
    )
    altdata: dict | None = Field(
        default=None,
        description="Misc. alternative metadata stored in JSON format.",
    )
    group_ids: list | None = Field(
        default=None,
        description="List of group IDs to which the photometry point is visible.",
    )
    stream_ids: list | None = Field(
        default=None,
        description="List of stream IDs to which the photometry point is visible.",
    )
    flux: float | None = Field(
        default=None,
        description="Flux of the observation in counts. Can be null to "
        "accommodate upper limits, where the flux error is used to derive a "
        "limiting magnitude.",
    )
    fluxerr: float | None = Field(
        default=None, description="Gaussian error on the flux in counts."
    )
    zp: float | None = Field(
        default=None,
        description="Magnitude zeropoint, given by `ZP` in the equation "
        "m = -2.5 log10(flux) + `ZP`.",
    )
    ref_flux: float | None = Field(
        default=None, description="Flux of the reference image in counts."
    )
    ref_fluxerr: float | None = Field(
        default=None,
        description="Gaussian error on the reference flux in counts.",
    )
    ref_zp: float | None = Field(
        default=None, description="Magnitude zeropoint of the reference image."
    )
    mag: float | None = Field(
        default=None,
        description="Magnitude of the observation in the magnitude system "
        "`magsys`. Can be null in the case of a non-detection.",
    )
    magerr: float | None = Field(
        default=None,
        description="Magnitude error of the observation in the magnitude system "
        "`magsys`. Can be null in the case of a non-detection.",
    )
    limiting_mag: float | None = Field(
        default=None,
        description="Limiting magnitude of the image in the magnitude system `magsys`.",
    )
    magref: float | None = Field(
        default=None, description="Magnitude of the reference image."
    )
    e_magref: float | None = Field(
        default=None, description="Gaussian error on the reference magnitude."
    )


class PhotometryPostResponse(BaseModel):
    """Data payload returned when uploading photometry (POST)."""

    ids: list[int] = Field(description="List of new photometry IDs")
    upload_id: str = Field(
        description="Upload ID associated with all photometry points added in "
        "the request. Can be used to later delete all points in a single request."
    )


class PhotometryPutResponse(BaseModel):
    """Data payload returned when updating and/or uploading photometry (PUT)."""

    ids: list[int] = Field(description="List of photometry IDs")


class ObjPhotometryGetQuery(BaseModel):
    """Query parameters for getting an object's photometry."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["mag", "flux", "both", "plot"] = Field(
        default="mag",
        description=(
            "Return the photometry in flux or magnitude space? "
            "If a value for this query parameter is not provided, the result "
            "will be returned in magnitude space. "
            '"plot" returns a slim per-point payload '
            "(id, obj_id, filter, mjd, origin, mag, magerr, limiting_mag) "
            "intended for lightcurve plotting; all per-point auxiliary "
            "joins (groups, annotations, instrument, owner, streams, "
            "validations) and the ref/tot/extinction blocks are skipped, "
            "regardless of the corresponding ``include*`` flags."
        ),
    )
    magsys: Literal["jla1", "ab", "vega", "bd17", "csp", "ab-b12"] = Field(
        default="ab",
        description="The magnitude or zeropoint system of the output. (Default AB)",
    )
    individualOrSeries: Literal["individual", "series", "both"] = Field(
        default="both",
        description=(
            "Whether to return individual photometry points, "
            "photometric series, or both (Default)."
        ),
    )
    phaseFoldData: bool = Field(
        default=False,
        description="Boolean indicating whether to phase fold the light curve. Defaults to false.",
    )
    deduplicatePhotometry: bool = Field(
        default=False,
        description="Boolean indicating whether to deduplicate photometry. Defaults to false.",
    )
    includeOwnerInfo: bool = Field(
        default=False,
        description="Boolean indicating whether to include photometry owner. Defaults to false.",
    )
    includeStreamInfo: bool = Field(
        default=False,
        description="Boolean indicating whether to include photometry stream information. Defaults to false.",
    )
    includeValidationInfo: bool = Field(
        default=False,
        description="Boolean indicating whether to include photometry validation information. Defaults to false.",
    )
    includeAnnotationInfo: bool = Field(
        default=False,
        description="Boolean indicating whether to include photometry annotations. Defaults to false.",
    )
    includeExtinction: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to include Galactic extinction values "
            "and extinction-corrected magnitudes/fluxes. Defaults to false."
        ),
    )
    includeSuperObjsPhotometry: bool = Field(
        default=False,
        description=(
            "Boolean indicating whether to also include photometry of any "
            "super-objects containing this object. Defaults to false."
        ),
    )


class PhotometryRangeGetQuery(BaseModel):
    """Query parameters for getting photometry over a date range."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["mag", "flux"] = Field(
        default="mag",
        description=(
            "Return the photometry in flux or magnitude space? "
            "If a value for this query parameter is not provided, the "
            "result will be returned in magnitude space."
        ),
    )
    magsys: Literal["jla1", "ab", "vega", "bd17", "csp", "ab-b12"] = Field(
        default="ab",
        description="The magnitude or zeropoint system of the output. (Default AB)",
    )


class PhotometryValidationResponse(BaseModel):
    """Data payload returned when validating/rejecting a photometry point."""

    id: int = Field(description="The id of the photometry_validation.")

"""Response models for ``/api/objs`` and related endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class ObjPositionResponse(BaseModel):
    """An object's photometry-derived position, with the discovery position it
    is measured against."""

    model_config = ConfigDict(extra="forbid")

    ra: float | None = None
    dec: float | None = None
    gal_lon: float | None = None
    gal_lat: float | None = None
    ebv: float | None = None
    separation: float | None = None
    discovery_ra: float | None = None
    discovery_dec: float | None = None


class SuperObjMemberResponse(BaseModel):
    """An object linked to a super-object, with its position."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ra: float | None = None
    dec: float | None = None


class SuperObjResponse(BaseModel):
    """Several objects that are one astrophysical source."""

    # super_obj_to_dict builds this by hand: modified and the full Obj rows
    # behind objs exist on the model but are not returned.

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    is_roid: bool | None = None
    created_at: datetime | None = None
    objs: list[SuperObjMemberResponse] = Field(default_factory=list)


class SuperObjPostResponse(BaseModel):
    """Result of creating a super-object."""

    model_config = ConfigDict(extra="forbid")

    id: int


class ObjMPCPostBody(BaseModel):
    """Request body for crossmatching an object with the Minor Planet Center."""

    model_config = ConfigDict(extra="forbid")

    obscode: str = Field(
        default="500",
        description="Minor planet center observatory code. "
        "Defaults to 500, corresponds to geocentric.",
    )
    date: str | None = Field(
        default=None,
        description="Time to check MPC for. Defaults to current time.",
    )
    limiting_magnitude: float = Field(
        default=24.0,
        description="Limiting magnitude down which to search. Defaults to 24.0.",
    )
    search_radius: float = Field(
        default=1,
        description="Search radius for MPC [in arcmin]. Defaults to 1 arcminute.",
    )


class ObjBody(BaseModel):
    """Shared optional `Obj` fields accepted by the Obj marshmallow schema
    (``Obj.__schema__()``) on source/candidate writes. Deep validation and
    coercion are still performed by that schema; this only constrains the
    top-level shape."""

    # Survey ids (e.g. LSST diaObject) arrive as JSON numbers, but Obj.id is a
    # string column; pydantic rejects int for `str` unless told to coerce.
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    ra: float | None = Field(None, description="ICRS Right Ascension [deg].")
    dec: float | None = Field(None, description="ICRS Declination [deg].")
    ra_dis: float | None = Field(
        None, description="J2000 Right Ascension at discovery time [deg]."
    )
    dec_dis: float | None = Field(
        None, description="J2000 Declination at discovery time [deg]."
    )
    ra_err: float | None = Field(
        None, description="Error on J2000 Right Ascension at discovery time [deg]."
    )
    dec_err: float | None = Field(
        None, description="Error on J2000 Declination at discovery time [deg]."
    )
    offset: float | None = Field(
        None, description="Offset from nearest static object [arcsec]."
    )
    t0: float | None = Field(None, description="Reference time.")
    redshift: float | None = Field(None, description="Redshift.")
    redshift_error: float | None = Field(None, description="Redshift error.")
    redshift_origin: str | None = Field(None, description="Redshift source.")
    redshift_history: Any = Field(
        None, description="Record of who set which redshift values and when."
    )
    host_id: int | None = Field(
        None, description="The ID of the Galaxy to which this Obj is associated."
    )
    summary: str | None = Field(None, description="Summary of the obj.")
    summary_history: Any = Field(
        None,
        description="Record of the summaries generated and written about this obj",
    )
    altdata: Any = Field(
        None,
        description="Misc. alternative metadata stored in JSON format, e.g. "
        "`{'gaia': {'info': {'Teff': 5780}}}`",
    )
    dist_nearest_source: float | None = Field(
        None, description="Distance to the nearest Obj [arcsec]."
    )
    mag_nearest_source: float | None = Field(
        None, description="Magnitude of the nearest Obj [AB]."
    )
    e_mag_nearest_source: float | None = Field(
        None, description="Error on magnitude of the nearest Obj [mag]."
    )
    transient: bool | None = Field(
        None,
        description="Boolean indicating whether the object is an astrophysical transient.",
    )
    varstar: bool | None = Field(
        None,
        description="Boolean indicating whether the object is a variable star.",
    )
    is_roid: bool | None = Field(
        None,
        description="Boolean indicating whether the object is a moving object.",
    )
    mpc_name: str | None = Field(None, description="Minor planet center name.")
    tns_name: str | None = Field(None, description="Transient Name Server name.")
    tns_info: Any = Field(None, description="TNS info in JSON format")
    score: float | None = Field(None, description="Machine learning score.")
    origin: str | None = Field(None, description="Origin of the object.")
    alias: list[str] | None = Field(
        None, description="Alternative names for this object."
    )


class ObjPositionGetQuery(BaseModel):
    """Query parameters for computing an Obj's photometry-based position."""

    model_config = ConfigDict(extra="forbid")

    instrument_ids: list[int] | None = Field(
        default=None,
        description="Only use photometry from these instrument IDs.",
    )
    stream_ids: list[int] | None = Field(
        default=None,
        description="Only use photometry from these stream IDs.",
    )
    stream_only: bool = Field(
        default=False,
        description="If true, only use photometry that belongs to at least one stream. Ignored when `stream_ids` is given.",
    )
    snr_threshold: float = Field(
        default=3.0,
        description="Only use photometry with a signal-to-noise ratio above this threshold. Defaults to 3.0.",
    )
    method: Literal["snr2", "invvar"] = Field(
        default="snr2",
        description="Weighting method used to combine the photometry positions. Defaults to snr2.",
    )


class ObjAcknowledgmentGetQuery(BaseModel):
    """Which detected components to include in the assembled text."""

    model_config = ConfigDict(extra="forbid")

    exclude_filter_ids: list[int] | None = Field(
        default=None,
        description="Filters not to cite. Omit to cite every one detected.",
    )
    exclude_instrument_ids: list[int] | None = Field(
        default=None,
        description="Instruments not to cite. Omit to cite every one detected.",
    )
    exclude_allocation_ids: list[int] | None = Field(
        default=None,
        description="Allocations not to cite. Omit to cite every one detected.",
    )


class SuperObjGetQuery(BaseModel):
    """Query parameters for retrieving SuperObjs."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset()

    name: str | None = Field(
        default=None,
        description="Filter by (partial) name",
    )
    isRoid: bool | None = Field(
        default=None,
        description="Filter by moving-object status",
    )
    objID: str | None = Field(
        default=None,
        description="Only SuperObjs linking this Obj",
    )


class SuperObjPostBody(BaseModel):
    """Request body for creating a SuperObj."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    name: str | None = Field(
        default=None, description="Name of the super-object, e.g. an MPC designation."
    )
    is_roid: bool = Field(
        default=False, description="Whether the super-object is a moving object."
    )
    obj_ids: list[str] = Field(
        default_factory=list, description="IDs of the Objs to link."
    )


class SuperObjPatchBody(BaseModel):
    """Request body for updating a SuperObj."""

    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)

    name: str | None = Field(default=None, description="Name of the super-object.")
    is_roid: bool | None = Field(
        default=None, description="Whether the super-object is a moving object."
    )
    obj_ids: list[str] | None = Field(
        default=None, description="IDs of the Objs to link, replacing the current ones."
    )
    add_obj_ids: list[str] | None = Field(
        default=None, description="IDs of Objs to add to the current ones."
    )
    remove_obj_ids: list[str] | None = Field(
        default=None, description="IDs of Objs to remove from the current ones."
    )


class ObjTNSGetQuery(BaseModel):
    """Query parameters for retrieving TNS information for an object."""

    model_config = ConfigDict(extra="forbid")

    radius: float = Field(
        default=2.0,
        description="Search radius, in arcsec, around the object. Defaults to 2.0.",
    )

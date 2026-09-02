"""Response models for ``/api/photometric_series``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from skyportal_py_models.groups import GroupResponse
from skyportal_py_models.streams import StreamResponse


class PhotometricSeriesDetailResponse(BaseModel):
    """A photometric series: one light curve of one object in one series."""

    # ``PhotometricSeries.to_dict`` returns the mapper columns plus ``data``
    # (the light curve in the requested ``dataFormat``), ``group_ids``,
    # ``stream_ids``, ``groups`` and ``streams``; the group/stream entries are
    # trimmed to a few columns. ``obj``, ``instrument``, ``owner``,
    # ``followup_request`` and ``assignment`` are lazy-loaded relationships that
    # these endpoints never touch, so they are never returned.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    series_name: str | None = None
    series_obj_id: str | None = None
    filter: str | None = None
    channel: str | None = None
    origin: str | None = None
    filename: str | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    mjd_first: float | None = None
    mjd_mid: float | None = None
    mjd_last: float | None = None
    mjd_last_detected: float | None = None
    mag_first: float | None = None
    mag_last: float | None = None
    mag_last_detected: float | None = None
    is_detected: bool | None = None
    exp_time: float | None = None
    frame_rate: float | None = None
    num_exp: int | None = None
    time_stamp_alignment: Literal["start", "middle", "end"] | None = None
    limiting_mag: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    mean_mag: float | None = None
    rms_mag: float | None = None
    robust_mag: float | None = None
    robust_rms: float | None = None
    median_snr: float | None = None
    best_snr: float | None = None
    worst_snr: float | None = None
    medians: dict[str, Any] | None = None
    maxima: dict[str, Any] | None = None
    minima: dict[str, Any] | None = None
    stds: dict[str, Any] | None = None
    altdata: dict[str, Any] | None = None
    hash: str | None = None
    autodelete: bool | None = None
    instrument_id: int | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    owner_id: int | None = None
    group_ids: list[int] = Field(default_factory=list)
    stream_ids: list[int] = Field(default_factory=list)
    groups: list[GroupResponse] = Field(default_factory=list)
    streams: list[StreamResponse] = Field(default_factory=list)
    data: dict[str, list[Any]] | str | None = None


class PhotometricSeriesPageResponse(BaseModel):
    """One page of results from a photometric series query."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    series: list[PhotometricSeriesDetailResponse] = Field(default_factory=list)
    total_matches: int = Field(alias="totalMatches", default=0)
    page_number: int = Field(alias="pageNumber", default=1)
    num_per_page: int = Field(alias="numPerPage", default=100)


class PhotometricSeriesPost(BaseModel):
    """Payload for uploading or updating a photometric series.

    ``data`` is either a mapping of column name to list of values, or a
    base64-encoded HDF5 bytestream written with ``pandas.HDFStore``. It must
    contain an ``mjd`` column and either a ``flux`` or a ``mag`` column.
    ``ra``, ``dec``, ``exp_time`` and ``filter`` are inferred from the data
    columns when not given explicitly. ``data`` is required when creating a
    series and optional when updating one.
    """

    model_config = ConfigDict(extra="forbid")

    data: dict[str, list[Any]] | str | None = None
    series_name: str | None = None
    series_obj_id: str | None = None
    obj_id: str | None = None
    instrument_id: int | None = None
    group_ids: list[int] | str | None = None
    stream_ids: list[int] | None = None
    ra: float | None = None
    dec: float | None = None
    ra_unc: float | None = None
    dec_unc: float | None = None
    exp_time: float | None = None
    filter: str | None = None
    channel: str | None = None
    origin: str | None = None
    limiting_mag: float | None = None
    magref: float | None = None
    e_magref: float | None = None
    ref_flux: float | None = None
    ref_fluxerr: float | None = None
    followup_request_id: int | None = None
    assignment_id: int | None = None
    time_stamp_alignment: Literal["start", "middle", "end"] | None = None
    altdata: dict[str, Any] | None = None


DEFAULT_SERIES_PER_PAGE = 100


class PhotometricSeriesPostBody(BaseModel):
    """Request body for uploading a photometric series.

    Every field is optional at this layer; the required set and per-value
    type coercion are enforced downstream by ``verify_data`` / ``verify_metadata``
    and the handler (which errors if ``data`` is missing).
    """

    model_config = ConfigDict(extra="forbid")

    data: dict | str | None = Field(
        default=None,
        description=(
            "The data to upload. Can be a string or a dict. If a dict (i.e., a "
            "json object) will assume each key is a column name and each value "
            "is a list of values for that column. That dictionary will be passed "
            "into a pandas DataFrame constructor, so the keys must be valid and "
            "the length of each value must be the same. If a string, will be "
            "converted to a bytes array and de-serialized by the pandas HDF5 "
            "reader. Use the HDFStore to create a file that includes a single "
            "key/group with the photometric data. Additional information, "
            "including any of the parameters specified below, can be stored in "
            'the HDFStore as well, inside the attributes under the key "metadata". '
            'In any case the DataFrame must have the following columns: "mjd", '
            'and either "flux" or "mag". Additional columns like "fluxerr" or '
            '"magerr" can be added, to plot errorbars on the frontend. Columns '
            'like "RA" or "exp_time" can be added to keep track of the values for '
            "individual observations, and the median value of these columns can "
            "be used instead of specifying the values in the metadata. Other "
            "information can be added as additional columns that will be saved to "
            "disk. That information will not be used by SkyPortal, but will be "
            "available for download."
        ),
    )
    series_name: str | None = Field(
        default=None,
        description=(
            "Name of the photometric series. Each series can contain light "
            "curves for multiple objects, and is usually continuous in some "
            "sense. Each series has a single instrument/filter, and generally a "
            "single pointing. Some examples would be a TESS sector or a single "
            "pointing with a fast photometer. The series name is used as the path "
            "to the file containing the photometric data, and can contain slashes "
            "(can also include underscores, + and -)."
        ),
    )
    series_obj_id: str | int | None = Field(
        default=None,
        description=(
            "Name or number of the object inside the photometric series. This can "
            "be a global object ID from the specific survey (e.g., a TESS TIC ID), "
            "or a casual index of the object in the series (e.g., star number 3). "
            "This does not have to correspond to the object ID in SkyPortal. It "
            "must be a unique identifier inside the series to be able to upload "
            "multiple light curves for different objects in the same series."
        ),
    )
    obj_id: str | int | None = Field(default=None, description="SkyPortal object ID.")
    instrument_id: int | None = Field(
        default=None,
        description="SkyPortal ID of the instrument used to take the photometric series.",
    )
    group_ids: list | int | str | None = Field(
        default=None,
        description=(
            "List of group IDs to associate with the photometric series. If not "
            "specified, defaults to the user's single user group. Can also specify "
            '"all" to share with all groups.'
        ),
    )
    stream_ids: list | str | None = Field(
        default=None,
        description="List of stream IDs to associate with the photometric series.",
    )
    ra: float | str | None = Field(
        default=None,
        description=(
            "Right ascension of the photometric series (degrees). Can specify the "
            'value for the entire series, or add an "RA" column to the data file. '
            "If not specified, the median RA from the data will be used as the "
            "coordinate for this object. If specified, will override the median "
            "value, but will not affect the individual measured RA. If no ra is "
            "given and no such column exists in the data file, the photometric "
            "series will not be posted."
        ),
    )
    dec: float | str | None = Field(
        default=None,
        description=(
            "Declination of the photometric series (degrees). Same as the RA "
            "column, only using the Dec column."
        ),
    )
    exp_time: float | str | None = Field(
        default=None,
        description=(
            "Exposure time of each measurement in the photometric series "
            "(seconds). If not specified, the median value of the "
            '"exp_time" column in the data file will be used instead. If no such '
            "column exists and the exp_time is not given, the photometric series "
            "will not be posted."
        ),
    )
    filter: str | None = Field(
        default=None,
        description=(
            "Name of the filter used to take the photometric series. If not "
            "specified, the filter name will be inferred from the data file. If no "
            "filter name is given and no such column exists in the data file, the "
            "photometric series will not be posted. Filter must be one of the "
            "allowed band passes."
        ),
    )
    channel: str | None = Field(
        default=None,
        description=(
            "Name of the channel used to take the photometric series. This is "
            "useful for multi-band simultaneous photometry, or for mosiaced CCD "
            "images where each tile has its own channel ID. This allows multiple "
            "series to be saved with the same series name but different channels, "
            "without violating the uniqueness constraint. Series with different "
            "channels can have the same or different filters. This field is "
            "entirely optional."
        ),
    )
    origin: str | None = Field(
        default=None,
        description="Provenance string for the photometric series.",
    )
    limiting_mag: float | str | None = Field(
        default=None,
        description=(
            "The limiting magnitude of the photometric series. Can specify the "
            'value for the entire series, or add a "limiting_mag" column to the '
            "data file. If not specified, the median limit from the data will be "
            "used as the representative limiting mag for this series. If specified, "
            "will override the median value, but will not affect the individual "
            "measured limits. If no limit is given and no such column exists in "
            "the data file, the photometric series will be posted with None as the "
            "limit."
        ),
    )
    magref: float | str | None = Field(
        default=None,
        description=(
            "Reference magnitude for the photometric series. This is used when the "
            "photometry is relative (e.g., based on subtraction images) and the "
            "magnitude of the object when it is not active is measured separately. "
            "This would be the magnitude before/after a transient, or the mean "
            "magnitude of a variable. For absolute photometry this is left as None."
        ),
    )
    e_magref: float | str | None = Field(
        default=None, description="Uncertainty on the magref."
    )
    ref_flux: float | str | None = Field(
        default=None, description="Reference flux for the photometric series."
    )
    ref_fluxerr: float | str | None = Field(
        default=None, description="Uncertainty on the reference flux."
    )
    ra_unc: float | str | None = Field(
        default=None, description="Uncertainty on the ra."
    )
    dec_unc: float | str | None = Field(
        default=None, description="Uncertainty on the dec."
    )
    followup_request_id: int | None = Field(
        default=None,
        description=(
            "ID of the followup request that generated this photometric series. "
            "This is used to link the photometric series to the followup request "
            "in the SkyPortal database."
        ),
    )
    assignment_id: int | None = Field(
        default=None,
        description=(
            "ID of the assignment that generated this photometric series. This is "
            "used to link the photometric series to the assignment in the "
            "SkyPortal database."
        ),
    )
    time_stamp_alignment: str | None = Field(
        default=None,
        description=(
            "Specify when the time stamp for each measurement was taken inside "
            'each exposure. Possible values are "start", "middle", "end". This is '
            'optional, and defaults to "middle".'
        ),
    )
    altdata: dict | str | None = Field(
        default=None,
        description=(
            "Additional information to store in the photometric series. This can "
            "be any valid JSON object, and will be stored in the database as a "
            "JSON string. This can hold various information that does not fit into "
            "any of the other inputs, but will still be useful to keep track of."
        ),
    )


class PhotometricSeriesPatchBody(PhotometricSeriesPostBody):
    """Request body for updating a photometric series (all inputs optional)."""


class PhotometricSeriesResponse(BaseModel):
    """Data payload returned when creating/updating a photometric series."""

    id: int = Field(description="Photometric series ID")


class PhotometricSeriesGetQuery(BaseModel):
    """Query parameters for retrieving photometric series."""

    model_config = ConfigDict(extra="forbid")

    single_fields: ClassVar[frozenset[str]] = frozenset({"dataFormat"})

    dataFormat: Literal["json", "hdf5", "none"] | None = Field(
        default=None,
        description=(
            "Format of the data to return. If `none`, the data will not be returned. "
            "If `hdf5`, the data will be returned as a bytestream in HDF5 format. "
            "(to see how to unpack this data format, look at `photometric_series.md`) "
            "If `json`, the data will be returned as a JSON object, where each key "
            "is a list of values for that column. "
            "Defaults to `json` when retrieving a single series, and to `none` when "
            "querying multiple series. To specifically request the data when querying "
            "multiple series, use `dataFormat=json` or `dataFormat=hdf5`. Keep in mind "
            "this could be a large amount of data if the query arguments do not "
            "filter down the number of returned series."
        ),
    )
    ra: float | None = Field(
        default=None,
        description="RA for spatial filtering (in decimal degrees)",
    )
    dec: float | None = Field(
        default=None,
        description="Declination for spatial filtering (in decimal degrees)",
    )
    radius: float | None = Field(
        default=None,
        description="Radius for spatial filtering if ra & dec are provided (in decimal degrees)",
    )
    objectID: str | None = Field(
        default=None,
        description="Portion of ID to filter on",
    )
    rejectedObjectID: str | None = Field(
        default=None,
        description=(
            "Comma-separated string of object IDs not to be returned, "
            "useful in cases where you are looking for new objects passing a query."
        ),
    )
    seriesName: str | None = Field(
        default=None,
        description=(
            "Get series that match this name. The match must be exact. "
            "This is useful when getting photometry for multiple objects "
            "taken at the same time (e.g., for calibrating against each other). "
            "The series name can be, e.g., a TESS sector, or a date/field name "
            "identifier. Generally a series name is shared only by data taken "
            "over that same time period."
        ),
    )
    seriesObjID: str | None = Field(
        default=None,
        description=(
            "Get only photometry for the objects named by this object id. "
            "This is the internal naming used inside each photometric series, "
            "i.e., the index used for each source in the images that were "
            "used to create the photometric series. Not the same as the SkyPortal "
            "object ID. E.g., this could be a TESS TIC ID, or some internal "
            "numbering used in the specific field that was observed."
        ),
    )
    filter: str | None = Field(
        default=None,
        description='Retrieve only series matching this filter, e.g., "ztfg".',
    )
    channel: str | None = Field(
        default=None,
        description="The channel name/id to filter on.",
    )
    origin: str | None = Field(
        default=None,
        description=(
            "The origin can be anything that gives an idea of the provenance "
            "of the photometric series. This can be, e.g., the name of the "
            "pipeline that produced the photometry from the images, or the "
            "level of calibration, or any other pre-defined string that "
            "identifies where the data came from that isn't covered by the "
            "other fields (like channel or filter or instrument)."
        ),
    )
    filename: str | None = Field(
        default=None,
        description=(
            "Portion of filename to filter on. If the filename is a relative "
            "path, will append the data directory from the config file to the "
            "beginning of the filename. "
            "(by default that is 'persistentdata/phot_series')."
        ),
    )
    startBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series that started before this time."
        ),
    )
    startAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series that started after this time."
        ),
    )
    midBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series where the middle of the series was observed before this time."
        ),
    )
    midAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series where the middle of the series was observed after this time."
        ),
    )
    endBefore: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series that ended before this time."
        ),
    )
    endAfter: str | None = Field(
        default=None,
        description=(
            "Arrow-parseable date string (e.g. 2020-01-01). If provided, return "
            "only series that ended after this time."
        ),
    )
    detected: bool | None = Field(
        default=None,
        description=(
            "If true, get only series with one or more detections. "
            "If false, get only series with no detections. "
            "If left out, do not filter at all on detection status."
        ),
    )
    expTime: float | None = Field(
        default=None,
        description="Get only series with this exact exposure time (seconds).",
    )
    minExpTime: float | None = Field(
        default=None,
        description=(
            "Get only series with an exposure time above/equal to this. "
            "If the series was not uploaded with one specific number, "
            "the exposure time for the series is the median of the "
            "exposure times of the individual images."
        ),
    )
    maxExpTime: float | None = Field(
        default=None,
        description=(
            "Get only series with an exposure time under/equal to this. "
            "If the series was not uploaded with one specific number, "
            "the exposure time for the series is the median of the "
            "exposure times of the individual images."
        ),
    )
    minFrameRate: float | None = Field(
        default=None,
        description=(
            "Get only series with a frame rate higher/equal to than this. "
            "Frame rates are the inverse of the median time between "
            "exposures, in units of 1/s (Hz)."
        ),
    )
    maxFrameRate: float | None = Field(
        default=None,
        description=(
            "Get only series with a frame rate lower/equal to than this. "
            "Frame rates are the inverse of the median time between "
            "exposures, in units of 1/s (Hz)."
        ),
    )
    minNumExposures: int | None = Field(
        default=None,
        description="Get only series with this many exposures, or more.",
    )
    maxNumExposures: int | None = Field(
        default=None,
        description="Get only series with this many exposures, or less.",
    )
    instrumentID: int | None = Field(
        default=None,
        description="get only series taken with this instrument.",
    )
    followupRequestID: int | None = Field(
        default=None,
        description="get only series taken with this followup request.",
    )
    assignmentID: int | None = Field(
        default=None,
        description="get only series taken with this assignment.",
    )
    ownerID: int | None = Field(
        default=None,
        description="get only series uploaded by this user.",
    )
    magBrighterThan: float | None = Field(
        default=None,
        description="get only series with mean_mag brighter or equal to this value.",
    )
    magFainterThan: float | None = Field(
        default=None,
        description="get only series with mean_mag fainter or equal to this value.",
    )
    limitingMagBrighterThan: float | None = Field(
        default=None,
        description="Retrieve only series with limiting mags brighter or equal to this value.",
    )
    limitingMagFainterThan: float | None = Field(
        default=None,
        description="Retrieve only series with limiting mags fainter or equal to this value.",
    )
    limitingMagIsNaN: bool = Field(
        default=False,
        description="Retrieve only series that do not have limiting mag.",
    )
    magrefBrighterThan: float | None = Field(
        default=None,
        description=(
            "Get only series that have a magref, "
            "and that the magref is brighter or equal to this value."
        ),
    )
    magrefFainterThan: float | None = Field(
        default=None,
        description=(
            "Get only series that have a magref, "
            "and that the magref is fainter or equal to this value."
        ),
    )
    maxRMS: float | None = Field(
        default=None,
        description="get only series with rms_mag less than this.",
    )
    minRMS: float | None = Field(
        default=None,
        description="get only series with rms_mag more than this.",
    )
    useRobustMagAndRMS: bool = Field(
        default=False,
        description=(
            "If true, will use the robust_mag and robust_rms values "
            "instead of mean_mag and rms_mag when filtering on mean "
            "magnitude or RMS. Does not affect the magref query."
        ),
    )
    maxMedianSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the median S/N is less than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    minMedianSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the median S/N is more than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    maxBestSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the maximum S/N is less than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    minBestSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the maximum S/N is more than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    maxWorstSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the lowest S/N is less than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    minWorstSNR: float | None = Field(
        default=None,
        description=(
            "Get only series where the lowest S/N is more than this. "
            "The S/N is calculated using the robust RMS."
        ),
    )
    hash: str | None = Field(
        default=None,
        description=(
            "Get only a series that matches this file hash. "
            "This is useful if you have an HDF5 file downloaded "
            "from the SkyPortal backend, and want to associate it "
            "with a PhotometrySeries object. "
            "We use an MD5 hash of the file contents."
        ),
    )
    sortBy: str = Field(
        default="obj_id",
        description="The column of the photometric series to sort by. Defaults to obj_id.",
    )
    sortOrder: Literal["asc", "desc"] = Field(
        default="asc",
        description='The sort order - either "asc" or "desc". Defaults to "asc"',
    )
    numPerPage: int = Field(
        default=DEFAULT_SERIES_PER_PAGE,
        description="Number of sources to return per paginated request. Defaults to 100. Max 500.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1",
    )

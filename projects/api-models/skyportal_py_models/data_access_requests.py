"""Request and response models for SkyPortal data access requests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_DATA_ACCESS_REQUESTS = 500


class DataAccessRequestPostBody(BaseModel):
    """Request body for asking an owner for data on an object."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object the data is attached to")
    photometry: list[PhotometryDataset] = Field(
        default_factory=list,
        description="Photometry datasets being asked for, as returned by the "
        "data availability endpoint.",
    )
    spectrumIDs: list[int] = Field(
        default_factory=list, description="IDs of the spectra being asked for"
    )
    message: str | None = Field(
        default=None, description="Note to the owner explaining the request"
    )


class DataAccessRequestPatchBody(BaseModel):
    """Request body for answering a request."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Either 'accepted' or 'declined'")
    groupID: int | None = Field(
        default=None,
        description="Group to share the data into when accepting. Defaults to "
        "the requester's single user group.",
    )


class DataAccessRequestGetQuery(BaseModel):
    """Query parameters for listing data access requests."""

    model_config = ConfigDict(extra="forbid")

    objId: str | None = Field(default=None, description="Only requests on this object")
    status: str | None = Field(
        default=None, description="Only requests with this status"
    )
    direction: str | None = Field(
        default=None,
        description="'incoming' for requests to answer, 'outgoing' for requests "
        "made by the calling user. Both when omitted.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of requests to return per paginated request. Defaults to "
            f"25. Max {MAX_DATA_ACCESS_REQUESTS}."
        ),
    )


MAX_DATA_ACCESS_REQUESTS = 500


class DataAccessRequestPostBody(BaseModel):
    """Request body for asking an owner for data on an object."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object the data is attached to")
    photometry: list[PhotometryDataset] = Field(
        default_factory=list,
        description="Photometry datasets being asked for, as returned by the "
        "data availability endpoint.",
    )
    spectrumIDs: list[int] = Field(
        default_factory=list, description="IDs of the spectra being asked for"
    )
    message: str | None = Field(
        default=None, description="Note to the owner explaining the request"
    )


class DataAccessRequestPatchBody(BaseModel):
    """Request body for answering a request."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Either 'accepted' or 'declined'")
    groupID: int | None = Field(
        default=None,
        description="Group to share the data into when accepting. Defaults to "
        "the requester's single user group.",
    )


class DataAccessRequestGetQuery(BaseModel):
    """Query parameters for listing data access requests."""

    model_config = ConfigDict(extra="forbid")

    objId: str | None = Field(default=None, description="Only requests on this object")
    status: str | None = Field(
        default=None, description="Only requests with this status"
    )
    direction: str | None = Field(
        default=None,
        description="'incoming' for requests to answer, 'outgoing' for requests "
        "made by the calling user. Both when omitted.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of requests to return per paginated request. Defaults to "
            f"25. Max {MAX_DATA_ACCESS_REQUESTS}."
        ),
    )


MAX_DATA_ACCESS_REQUESTS = 500


class DataAccessRequestGetQuery(BaseModel):
    """Query parameters for listing data access requests."""

    model_config = ConfigDict(extra="forbid")

    objId: str | None = Field(default=None, description="Only requests on this object")
    status: str | None = Field(
        default=None, description="Only requests with this status"
    )
    direction: str | None = Field(
        default=None,
        description="'incoming' for requests to answer, 'outgoing' for requests "
        "made by the calling user. Both when omitted.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of requests to return per paginated request. Defaults to "
            f"25. Max {MAX_DATA_ACCESS_REQUESTS}."
        ),
    )


MAX_DATA_ACCESS_REQUESTS = 500


class PhotometryDataset(BaseModel):
    """One owner's photometry on an object in a single instrument/filter."""

    model_config = ConfigDict(extra="forbid")

    ownerID: int = Field(description="ID of the User who owns the photometry")
    instrumentID: int = Field(description="ID of the instrument it was taken with")
    filter: str = Field(description="Bandpass the photometry was taken in")


class DataAccessRequestPostBody(BaseModel):
    """Request body for asking an owner for data on an object."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object the data is attached to")
    photometry: list[PhotometryDataset] = Field(
        default_factory=list,
        description="Photometry datasets being asked for, as returned by the "
        "data availability endpoint.",
    )
    spectrumIDs: list[int] = Field(
        default_factory=list, description="IDs of the spectra being asked for"
    )
    message: str | None = Field(
        default=None, description="Note to the owner explaining the request"
    )


class DataAccessRequestPatchBody(BaseModel):
    """Request body for answering a request."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="Either 'accepted' or 'declined'")
    groupID: int | None = Field(
        default=None,
        description="Group to share the data into when accepting. Defaults to "
        "the requester's single user group.",
    )


class DataAccessRequestGetQuery(BaseModel):
    """Query parameters for listing data access requests."""

    model_config = ConfigDict(extra="forbid")

    objId: str | None = Field(default=None, description="Only requests on this object")
    status: str | None = Field(
        default=None, description="Only requests with this status"
    )
    direction: str | None = Field(
        default=None,
        description="'incoming' for requests to answer, 'outgoing' for requests "
        "made by the calling user. Both when omitted.",
    )
    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=25,
        description=(
            "Number of requests to return per paginated request. Defaults to "
            f"25. Max {MAX_DATA_ACCESS_REQUESTS}."
        ),
    )

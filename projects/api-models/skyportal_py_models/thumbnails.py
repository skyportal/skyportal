"""Response models for ``/api/thumbnail``."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ThumbnailResponse(BaseModel):
    """A thumbnail image centered on an object."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    obj_id: str | None = None
    type: (
        Literal[
            "new",
            "ref",
            "sub",
            "sdss",
            "dr8",
            "ls",
            "ps1",
            "sm",
            "hst",
            "chandra",
            "jwst",
            "new_gz",
            "ref_gz",
            "sub_gz",
        ]
        | None
    ) = None
    file_uri: str | None = None
    public_url: str | None = None
    origin: str | None = None
    survey: str | None = None
    is_grayscale: bool | None = None


class ThumbnailPathReportResponse(BaseModel):
    """Counts of thumbnails found in the correct and incorrect folders."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    total_matches: int | None = Field(alias="totalMatches", default=None)
    in_correct_folder: int | None = Field(alias="inCorrectFolder", default=None)
    in_wrong_folder: int | None = Field(alias="inWrongFolder", default=None)
    num_moved: int | None = Field(alias="numMoved", default=None)


ThumbnailType = Literal[
    "new",
    "ref",
    "sub",
    "sdss",
    "dr8",
    "ls",
    "ps1",
    "sm",
    "hst",
    "chandra",
    "jwst",
    "new_gz",
    "ref_gz",
    "sub_gz",
]


class ThumbnailPost(BaseModel):
    """Payload for uploading a thumbnail."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str
    data: str
    ttype: ThumbnailType
    survey: str | None = None


class ThumbnailPostBody(BaseModel):
    """Request body for uploading a thumbnail."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str = Field(description="ID of object associated with thumbnails.")
    data: str = Field(
        description="base64-encoded PNG image file contents. Image size must "
        "be between 16px and 500px on a side."
    )
    ttype: str = Field(
        description="Thumbnail type. Must be one of 'new', 'ref', 'sub', "
        "'sdss', 'dr8', 'new_gz', 'ref_gz', 'sub_gz'"
    )
    survey: str | None = Field(
        default=None,
        description="Survey the cutout came from (e.g. ZTF, LSST). NULL for "
        "all-sky archival thumbnails.",
    )


class ThumbnailPostResponse(BaseModel):
    """Data payload returned when uploading a thumbnail."""

    id: int = Field(description="New thumbnail ID")


class ThumbnailPutBody(BaseModel):
    """Request body for updating a thumbnail."""

    model_config = ConfigDict(extra="forbid")

    obj_id: str | None = Field(default=None, description="ID of the thumbnail's obj.")
    type: str | None = Field(
        default=None, description="Thumbnail type (e.g., ref, new, sub, ls, ps1, ...)"
    )
    file_uri: str | None = Field(
        default=None,
        description="Path of the Thumbnail on the machine running SkyPortal.",
    )
    public_url: str | None = Field(
        default=None, description="Publically accessible URL of the thumbnail."
    )
    origin: str | None = Field(default=None, description="Origin of the Thumbnail.")
    is_grayscale: bool | None = Field(
        default=None, description="Whether the thumbnail is (mostly) grayscale."
    )


class ThumbnailPathGetQuery(BaseModel):
    """Query parameters for checking thumbnail paths."""

    model_config = ConfigDict(extra="forbid")

    types: list[str] = Field(
        default=["new", "ref", "sub"],
        description=(
            "types of thumbnails to check. The default is ['new', 'ref', 'sub'] "
            "which are all the thumbnail types stored locally."
        ),
    )
    requiredDepth: int = Field(
        default=2,
        description=(
            "number of subdirectories that are desired for thumbnails. For example "
            "if requiredDepth is 2, then thumbnails will be stored in a folder like "
            "/skyportal/static/thumbnails/ab/cd/<source_name>_<type>.png where 'ab' "
            "and 'cd' are the first characters of the hash of the source name. "
            "If requiredDepth is 0, then thumbnails are expected to be all in one "
            "folder under /skyportal/static/thumbnails."
        ),
    )


class ThumbnailPathPatchQuery(ThumbnailPathGetQuery):
    """Query parameters for updating thumbnail paths (same filters as the
    check, plus pagination over the rows to move)."""

    pageNumber: int = Field(
        default=1,
        description="Page number for paginated query results. Defaults to 1.",
    )
    numPerPage: int = Field(
        default=100,
        description=(
            "Number of thumbnails to update per paginated request. Defaults to "
            "100. Capped at 1000."
        ),
    )

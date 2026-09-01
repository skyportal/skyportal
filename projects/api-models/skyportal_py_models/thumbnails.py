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

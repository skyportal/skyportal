"""Request and response models for SkyPortal sharing."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SharingPostBody(BaseModel):
    """Request body for sharing data with additional groups/users."""

    model_config = ConfigDict(extra="forbid")

    groupIDs: list[int] = Field(
        min_length=1,
        description="List of IDs of groups data will be shared with. To share "
        "data with a single user, specify their single user group ID here.",
    )
    photometryIDs: list[int] | None = Field(
        default=None,
        description="IDs of the photometry data to be shared. If `spectrumIDs` "
        "is not provided, this is required.",
    )
    spectrumIDs: list[int] | None = Field(
        default=None,
        description="IDs of the spectra to be shared. If `photometryIDs` is "
        "not provided, this is required.",
    )


class SharingPostBody(BaseModel):
    """Request body for sharing data with additional groups/users."""

    model_config = ConfigDict(extra="forbid")

    groupIDs: list[int] = Field(
        min_length=1,
        description="List of IDs of groups data will be shared with. To share "
        "data with a single user, specify their single user group ID here.",
    )
    photometryIDs: list[int] | None = Field(
        default=None,
        description="IDs of the photometry data to be shared. If `spectrumIDs` "
        "is not provided, this is required.",
    )
    spectrumIDs: list[int] | None = Field(
        default=None,
        description="IDs of the spectra to be shared. If `photometryIDs` is "
        "not provided, this is required.",
    )


class SharingPostBody(BaseModel):
    """Request body for sharing data with additional groups/users."""

    model_config = ConfigDict(extra="forbid")

    groupIDs: list[int] = Field(
        min_length=1,
        description="List of IDs of groups data will be shared with. To share "
        "data with a single user, specify their single user group ID here.",
    )
    photometryIDs: list[int] | None = Field(
        default=None,
        description="IDs of the photometry data to be shared. If `spectrumIDs` "
        "is not provided, this is required.",
    )
    spectrumIDs: list[int] | None = Field(
        default=None,
        description="IDs of the spectra to be shared. If `photometryIDs` is "
        "not provided, this is required.",
    )


class SharingPostBody(BaseModel):
    """Request body for sharing data with additional groups/users."""

    model_config = ConfigDict(extra="forbid")

    groupIDs: list[int] = Field(
        min_length=1,
        description="List of IDs of groups data will be shared with. To share "
        "data with a single user, specify their single user group ID here.",
    )
    photometryIDs: list[int] | None = Field(
        default=None,
        description="IDs of the photometry data to be shared. If `spectrumIDs` "
        "is not provided, this is required.",
    )
    spectrumIDs: list[int] | None = Field(
        default=None,
        description="IDs of the spectra to be shared. If `photometryIDs` is "
        "not provided, this is required.",
    )

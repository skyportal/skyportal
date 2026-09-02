"""Request models for ``/api/source_groups``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceGroupsPost(BaseModel):
    """Payload for saving or unsaving a source to or from groups."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    obj_id: str = Field(alias="objId")
    invite_group_ids: list[int] = Field(alias="inviteGroupIds", default_factory=list)
    unsave_group_ids: list[int] = Field(alias="unsaveGroupIds", default_factory=list)


class SourceGroupsPostBody(BaseModel):
    """Request body for saving/unsaving a source to/from groups."""

    model_config = ConfigDict(extra="forbid")

    objId: str = Field(description="ID of the object in question.")
    inviteGroupIds: list[int] = Field(
        default_factory=list,
        description="List of group IDs to save or invite to save specified source.",
    )
    unsaveGroupIds: list[int] = Field(
        default_factory=list,
        description="List of group IDs from which specified source is to be unsaved.",
    )


class SourceGroupsPatchBody(BaseModel):
    """Request body for updating a Source table row."""

    model_config = ConfigDict(extra="forbid")

    groupID: int = Field(description="ID of the group whose Source row to update.")
    active: bool = Field(description="Whether the source is saved to the group.")
    requested: bool = Field(
        description="Whether the source is requested to be saved to the group."
    )

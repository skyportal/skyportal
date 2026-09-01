"""Request models for ``/api/source_groups``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceGroupsPost(BaseModel):
    """Payload for saving or unsaving a source to or from groups."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    obj_id: str = Field(alias="objId")
    invite_group_ids: list[int] = Field(alias="inviteGroupIds", default_factory=list)
    unsave_group_ids: list[int] = Field(alias="unsaveGroupIds", default_factory=list)

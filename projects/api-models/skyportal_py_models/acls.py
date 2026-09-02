"""Request and response models for SkyPortal acls."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserACLPostBody(BaseModel):
    """Request body for granting ACLs to a user."""

    model_config = ConfigDict(extra="forbid")

    aclIds: list[str] = Field(
        description="Array of ACL IDs (strings) to be granted to user"
    )


class UserACLPostBody(BaseModel):
    """Request body for granting ACLs to a user."""

    model_config = ConfigDict(extra="forbid")

    aclIds: list[str] = Field(
        description="Array of ACL IDs (strings) to be granted to user"
    )


class UserACLPostBody(BaseModel):
    """Request body for granting ACLs to a user."""

    model_config = ConfigDict(extra="forbid")

    aclIds: list[str] = Field(
        description="Array of ACL IDs (strings) to be granted to user"
    )

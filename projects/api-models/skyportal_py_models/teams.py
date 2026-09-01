"""Response models for ``/api/teams``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamGroupResponse(BaseModel):
    """A group belonging to a team, as assembled by the team handler."""

    model_config = ConfigDict(extra="forbid")

    id: int
    name: str | None = None
    nickname: str | None = None


class TeamMemberResponse(BaseModel):
    """A user who is a member of one of a team's groups."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TeamResponse(BaseModel):
    """A collaboration-level grouping of groups (``Team``)."""

    # ``groups``, ``num_members`` and ``users`` are hand-built by the handler's
    # ``team_to_dict``; ``users`` is omitted from the list endpoint.

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    name: str | None = None
    nickname: str | None = None
    description: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    logo_url: str | None = None
    background_url: str | None = None
    groups: list[TeamGroupResponse] = Field(default_factory=list)
    num_members: int | None = None
    users: list[TeamMemberResponse] | None = None


class TeamsResponse(BaseModel):
    """Every team the requesting user can access."""

    model_config = ConfigDict(extra="forbid")

    teams: list[TeamResponse] = Field(default_factory=list)


class TeamPost(BaseModel):
    """Payload for creating a team."""

    model_config = ConfigDict(extra="forbid")

    name: str
    nickname: str | None = None
    description: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    logo_url: str | None = None
    background_url: str | None = None
    group_ids: list[int] | None = None


class TeamPut(BaseModel):
    """Payload for updating a team."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    nickname: str | None = None
    description: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    logo_url: str | None = None
    background_url: str | None = None
    group_ids: list[int] | None = None

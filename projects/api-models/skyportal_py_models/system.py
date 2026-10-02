"""Response models for the instance introspection endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DBInfoResponse(BaseModel):
    """Basic health information about the instance's database."""

    model_config = ConfigDict(extra="forbid")

    source_table_empty: bool | None = None
    postgres_version: str | None = None


class GitLogEntryResponse(BaseModel):
    """One parsed commit from the deployed SkyPortal git log."""

    model_config = ConfigDict(extra="forbid")

    time: str | None = None
    sha: str | None = None
    email: str | None = None
    description: str | None = None
    pr_nr: str | None = None
    pr_url: str | None = None
    commit_url: str | None = None
    name: str | None = None


class SysInfoResponse(BaseModel):
    """System and deployment information for the SkyPortal instance."""

    model_config = ConfigDict(extra="forbid")

    gitlog: list[GitLogEntryResponse] = Field(default_factory=list)


class DeploymentResponse(BaseModel):
    """One version of the code that started serving the instance."""

    model_config = ConfigDict(extra="forbid")

    id: int
    version: str
    commit: GitLogEntryResponse | None = None
    created_at: datetime = Field(description="When this version started (UTC)")
    changes: list[GitLogEntryResponse] | None = Field(
        default=None,
        description="Commits brought over the previous deployment, newest first "
        "(capped); null when either commit is not in the running git log",
    )
    n_changes: int | None = None
    rollback: bool = Field(
        default=False, description="Whether this deployed an older commit"
    )


class SupervisorProcessResponse(BaseModel):
    """A process run by supervisor on the instance host."""

    model_config = ConfigDict(extra="forbid")

    name: str
    group: str
    state: str
    pid: int | None = None
    memory: int | None = Field(
        default=None,
        description="Proportional memory of the service process and its children, in bytes",
    )
    started_at: datetime | None = None


class ServiceResponse(BaseModel):
    """A service of the instance and the processes supervisor runs for it."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: Literal["enabled", "disabled", "not_configured"] = Field(
        description="`disabled` in `services.disabled`; `not_configured` when "
        "enabled but supervisor runs no program for it, as its template only "
        "defines one when the config calls for the service"
    )
    processes: list[SupervisorProcessResponse] = Field(default_factory=list)


class HostResourcesResponse(BaseModel):
    """CPU, memory and disk of the instance host (the node, in a container)."""

    model_config = ConfigDict(extra="forbid")

    cpu_count: int | None = None
    load_average: list[float] | None = None
    memory_total: int | None = None
    memory_available: int | None = None
    disk_total: int | None = None
    disk_free: int | None = None


class InstanceSystemResponse(BaseModel):
    """Host, database and service details, only returned to system admins."""

    model_config = ConfigDict(extra="forbid")

    hostname: str
    platform: str
    python_version: str
    packages: dict[str, str] = Field(default_factory=dict)
    supervisor_available: bool = False
    services: list[ServiceResponse] = Field(default_factory=list)
    resources: HostResourcesResponse | None = None
    database_name: str | None = None
    postgres_version: str | None = None
    database_size: str | None = None
    migration: str | None = None


class DeploymentsResponse(BaseModel):
    """Running version and deployment history of the instance."""

    model_config = ConfigDict(extra="forbid")

    title: str
    version: str
    commit: GitLogEntryResponse | None = None
    started_at: datetime = Field(description="When this app process started (UTC)")
    deployed_at: datetime | None = None
    deployments: list[DeploymentResponse] = Field(default_factory=list)
    system: InstanceSystemResponse | None = None


class LogPostBody(BaseModel):
    """Request body for logging a frontend error."""

    model_config = ConfigDict(extra="forbid")

    error: str | None = Field(default=None, description="Error message to log")
    stack: str | None = Field(
        default=None, description="Component stack trace of the error"
    )


__all__ = [
    "DBInfoResponse",
    "DeploymentResponse",
    "DeploymentsResponse",
    "GitLogEntryResponse",
    "HostResourcesResponse",
    "InstanceSystemResponse",
    "LogPostBody",
    "ServiceResponse",
    "SupervisorProcessResponse",
    "SysInfoResponse",
]

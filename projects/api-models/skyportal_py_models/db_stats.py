"""Response models for ``/api/db_stats`` and ``/api/db_stats/history``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CronJobRunSummaryResponse(BaseModel):
    """The latest run of one cron job script."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    output: str | None = None


class DBStatsResponse(BaseModel):
    """Row counts of the major tables plus the cron job run log.

    The wire keys are the human-readable labels the handler builds, spaces
    and all, hence the aliases.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    photometry: int | None = Field(alias="Number of photometry (approx)", default=None)
    candidates: int | None = Field(alias="Number of candidates", default=None)
    sources: int | None = Field(alias="Number of sources", default=None)
    source_views: int | None = Field(alias="Number of source views", default=None)
    objs: int | None = Field(alias="Number of objs", default=None)
    spectra: int | None = Field(alias="Number of spectra", default=None)
    groups: int | None = Field(alias="Number of groups", default=None)
    users: int | None = Field(alias="Number of users", default=None)
    tokens: int | None = Field(alias="Number of tokens", default=None)
    filters: int | None = Field(alias="Number of filters", default=None)
    telescopes: int | None = Field(alias="Number of telescopes", default=None)
    instruments: int | None = Field(alias="Number of instruments", default=None)
    comments: int | None = Field(alias="Number of comments", default=None)
    annotations: int | None = Field(alias="Number of annotations", default=None)
    thumbnails: int | None = Field(alias="Number of thumbnails", default=None)
    gcn_events: int | None = Field(alias="Number of GCN events", default=None)
    cron_job_runs: list[CronJobRunSummaryResponse] = Field(
        alias="Latest cron job run times & statuses", default_factory=list
    )


class DBStatsHistoryResponse(BaseModel):
    """Bucketed row counts over time.

    ``tables`` lists every table the endpoint can count; ``counts`` only
    carries the tables the query asked for, each list aligned with ``bins``.
    The dates and bins are naive UTC ISO-8601 strings.
    """

    model_config = ConfigDict(extra="forbid", validate_by_name=True)

    interval: Literal["hour", "day", "week", "month"]
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    bins: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    counts: dict[str, list[int]] = Field(default_factory=dict)


__all__ = [
    "CronJobRunSummaryResponse",
    "DBStatsHistoryResponse",
    "DBStatsResponse",
]

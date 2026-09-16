"""Response models for ``/api/data_sharing/bulk`` and
``/api/spectra/{spectrum_id}/groups/{group_id}``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BulkDataShareResponse(BaseModel):
    """Result of bulk-sharing data between groups.

    ``counts`` maps each requested data type (``spectra``/``photometry``) to
    the number of rows inserted or deleted.
    """

    model_config = ConfigDict(extra="forbid")

    action: Literal["add", "remove"]
    counts: dict[str, int] = Field(default_factory=dict)


class SpectrumGroupRemovalResponse(BaseModel):
    """Result of removing a group from a spectrum.

    ``message`` only appears on the no-op path, when the group was not on the
    spectrum; the removal itself returns no data.
    """

    model_config = ConfigDict(extra="forbid")

    message: str | None = None


__all__ = [
    "BulkDataShareResponse",
    "SpectrumGroupRemovalResponse",
]

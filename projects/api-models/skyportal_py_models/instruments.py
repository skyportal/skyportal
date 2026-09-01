"""Response models for ``/api/instrument``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from skyportal_py_models._cyclic import InstrumentFieldResponse, InstrumentResponse


class InstrumentLogResponse(BaseModel):
    """A log uploaded for an instrument."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime | None = None
    modified: datetime | None = None
    instrument_id: int | None = None
    instrument: InstrumentResponse | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    log: dict[str, Any] | None = None


__all__ = [
    "InstrumentFieldResponse",
    "InstrumentLogResponse",
    "InstrumentResponse",
]

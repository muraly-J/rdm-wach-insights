from __future__ import annotations

"""
models/cmms_event.py
────────────────────
Pydantic value-object for a single CMMS maintenance event.

CMMSEvent is immutable (frozen=True) and uses strict mode so callers cannot
accidentally pass the wrong type and have it silently coerced.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# The six accepted event categories.
EventType = Literal[
    "filter_change",
    "coil_clean",
    "belt_replace",
    "corrective_failure",
    "planned_pm",
    "other",
]

VALID_EVENT_TYPES: frozenset[str] = frozenset(EventType.__args__)  # type: ignore[attr-defined]


class CMMSEvent(BaseModel):
    """
    A single CMMS maintenance event record.

    Fields
    ------
    event_id    : Unique identifier (PK in the cache DB).
    ahu_id      : AHU device identifier (e.g. ``e0101``).
    ts          : Event timestamp.  Naive timestamps are treated as UTC by the
                  ingestion layer and stored/returned as UTC-aware datetimes.
    event_type  : One of the six canonical maintenance categories.
    notes       : Free-text technician notes; ``None`` when absent.
    source      : Data-origin label, defaults to ``"manual"`` for CSV imports.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    event_id: str
    ahu_id: str
    ts: datetime
    event_type: EventType
    notes: str | None = None
    source: str = "manual"

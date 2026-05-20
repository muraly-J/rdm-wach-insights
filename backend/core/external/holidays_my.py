from __future__ import annotations

"""
core/external/holidays_my.py
────────────────────────────
Malaysian public holiday calendar, backed by the ``holidays`` package.

Public API
----------
    is_holiday(d, *, subdivision=None) -> bool
        True if *d* is a Malaysian public holiday (federal, or also state-level
        when *subdivision* is set to a valid ISO 3166-2:MY subdivision code,
        e.g. ``"KUL"``, ``"SGR"``, ``"PNG"``).

    holiday_name(d, *, subdivision=None) -> str | None
        Canonical name string from the ``holidays`` package, or ``None`` if
        *d* is not a public holiday.

Both functions accept either a ``datetime.date`` or a ``datetime.datetime``
(the datetime is coerced to its ``.date()`` component automatically).

The holidays object is built once per subdivision key and reused for all
subsequent calls (``functools.lru_cache`` on the internal factory). The
``holidays`` package performs lazy year-expansion, so there is no need to
specify a year window.
"""

import functools
from datetime import date, datetime
from typing import Any

import holidays

from config import settings

__all__ = ["is_holiday", "holiday_name"]

# Private sentinel — used so that the `subdivision` default is re-read from
# `settings` on every call rather than frozen at module import time.
_UNSET: Any = object()


# ── Internal helpers ──────────────────────────────────────────────────────────


def _to_date(d: date | datetime) -> date:
    """Normalise a date or datetime to a plain date."""
    if isinstance(d, datetime):
        return d.date()
    return d


@functools.lru_cache(maxsize=32)
def _calendar(subdivision: str | None) -> holidays.HolidayBase:
    """
    Return a (cached) Malaysian holiday calendar for *subdivision*.

    Passing ``subdivision=None`` returns the federal-only calendar.
    State-level holidays are included when a valid subdivision code is given
    (e.g. ``"KUL"``, ``"SGR"``, ``"PNG"``).

    The object is built once and cached indefinitely; the ``holidays`` package
    expands years lazily on each ``__contains__`` / ``get()`` call.
    """
    return holidays.country_holidays("MY", subdiv=subdivision, language="en_US")


# ── Public API ────────────────────────────────────────────────────────────────


def is_holiday(d: date | datetime, *, subdivision: str | None | Any = _UNSET) -> bool:
    """
    Return True if *d* is a Malaysian public holiday.

    Parameters
    ----------
    d : date | datetime
        The date to query.  ``datetime`` values are coerced to their date part.
    subdivision : str | None
        ISO 3166-2:MY subdivision code (e.g. ``"KUL"``, ``"SGR"``).
        ``None`` checks federal holidays only.
        When omitted, falls back to ``settings.holiday_subdivision`` (re-read
        on every call — not frozen at import time).

    Returns
    -------
    bool
    """
    if subdivision is _UNSET:
        subdivision = settings.holiday_subdivision
    return _to_date(d) in _calendar(subdivision)


def holiday_name(d: date | datetime, *, subdivision: str | None | Any = _UNSET) -> str | None:
    """
    Return the canonical name for a Malaysian public holiday, or None.

    Parameters
    ----------
    d : date | datetime
        The date to query.  ``datetime`` values are coerced to their date part.
    subdivision : str | None
        ISO 3166-2:MY subdivision code (e.g. ``"KUL"``, ``"SGR"``).
        ``None`` checks federal holidays only.
        When omitted, falls back to ``settings.holiday_subdivision`` (re-read
        on every call — not frozen at import time).

    Returns
    -------
    str | None
        The canonical holiday name, or ``None`` if *d* is not a holiday.
    """
    if subdivision is _UNSET:
        subdivision = settings.holiday_subdivision
    return _calendar(subdivision).get(_to_date(d))

from __future__ import annotations

"""
tests/core/external/test_holidays_my.py
────────────────────────────────────────
Unit tests for the Malaysian public holiday calendar (core/external/holidays_my.py).

Dates used
----------
* 2026-05-01 — Labour/Labor Day (federal)
* 2026-05-14 — Ordinary Thursday, no federal holiday
* 2026-02-01 — Thaipusam 2026 (state holiday in KUL / Federal Territory Day in KUL;
               confirmed via `holidays.country_holidays("MY", subdiv="KUL", years=2026)`
               — NOT in the federal calendar)
"""

from datetime import date, datetime

import pytest

from core.external.holidays_my import holiday_name, is_holiday


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_lru_cache():
    """
    Clear the lru_cache on the holiday-calendar factory before and after
    each test to avoid cross-test pollution (e.g. when tests call with
    different subdivision values).
    """
    from core.external.holidays_my import _calendar

    _calendar.cache_clear()
    yield
    _calendar.cache_clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_labour_day_2026_is_holiday():
    """2026-05-01 (Labour/Labor Day) is a Malaysian federal holiday."""
    assert is_holiday(date(2026, 5, 1), subdivision=None) is True


def test_non_holiday_weekday_is_false():
    """2026-05-14 (ordinary Thursday) is NOT a Malaysian federal holiday."""
    assert is_holiday(date(2026, 5, 14), subdivision=None) is False


def test_holiday_name_returns_canonical_string():
    """
    holiday_name for Labour/Labor Day should contain "labor" (case-insensitive).

    The ``holidays`` package may return "Labor Day" or "Labour Day" depending
    on version; we do a case-insensitive substring match to stay version-stable.
    """
    name = holiday_name(date(2026, 5, 1), subdivision=None)
    assert name is not None, "Expected a holiday name but got None"
    assert "labor" in name.lower(), (
        f"Expected the holiday name to contain 'labor' (case-insensitive); got: {name!r}"
    )


def test_datetime_input_is_normalized():
    """
    Passing a datetime with a time component should work identically to
    passing the equivalent date.
    """
    dt = datetime(2026, 5, 1, 14, 30, 0)
    d = date(2026, 5, 1)

    assert is_holiday(dt, subdivision=None) == is_holiday(d, subdivision=None)
    assert holiday_name(dt, subdivision=None) == holiday_name(d, subdivision=None)


def test_subdivision_unlocks_state_holiday():
    """
    Thaipusam 2026 (2026-02-01) is a state holiday in KUL but NOT a federal
    holiday. Confirmed date via:
        holidays.country_holidays("MY", subdiv="KUL", years=2026)[date(2026, 2, 1)]
        → "Federal Territory Day; Thaipusam"

    - is_holiday(d, subdivision=None)    → False  (not federal)
    - is_holiday(d, subdivision="KUL")  → True   (state holiday in KUL)
    """
    thaipusam_2026 = date(2026, 2, 1)

    assert is_holiday(thaipusam_2026, subdivision=None) is False, (
        "Thaipusam 2026-02-01 should NOT appear in the federal-only calendar"
    )
    assert is_holiday(thaipusam_2026, subdivision="KUL") is True, (
        "Thaipusam 2026-02-01 should appear in the KUL state calendar"
    )

"""Tests for technician handler helper functions."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_format_my_work_empty():
    from bot.handlers.technicians import _format_my_work

    text = _format_my_work([])
    assert "no" in text.lower() or "assigned" in text.lower()


def test_format_my_work_with_items():
    from bot.handlers.technicians import _format_my_work

    orders = [
        {"id": 3, "ahu_id": "e0301", "level": 3, "title": "Vibration fault", "status": "approved"},
        {"id": 7, "ahu_id": "e0402", "level": 4, "title": "Overtemp", "status": "in_progress"},
    ]
    text = _format_my_work(orders)
    assert "#3" in text
    assert "e0301" in text
    assert "#7" in text


def test_format_ahu_status_contains_ahu_id():
    from bot.handlers.technicians import _format_ahu_status

    data = {"ahu_id": "e0402", "temperature": 22.5, "airflow": 1200}
    text = _format_ahu_status("e0402", data)
    assert "e0402" in text

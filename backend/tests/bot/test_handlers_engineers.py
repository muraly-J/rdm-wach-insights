"""Tests for engineer handler helper functions."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_format_review_detail_contains_ahu():
    from bot.handlers.engineers import _format_review_detail
    wo = {
        "id": 7, "ahu_id": "e0507", "level": 5, "title": "Low airflow",
        "description": "Airflow sensor below threshold",
        "fair_snapshot": '{"F": 55, "A": 30, "I": 70, "R": 80, "composite": 58}',
    }
    text = _format_review_detail(wo)
    assert "e0507" in text
    assert "#7" in text
    assert "Low airflow" in text


def test_format_review_detail_contains_fair():
    from bot.handlers.engineers import _format_review_detail
    wo = {
        "id": 7, "ahu_id": "e0507", "level": 5, "title": "Low airflow",
        "description": None,
        "fair_snapshot": '{"F": 55, "A": 30, "I": 70, "R": 80, "composite": 58}',
    }
    text = _format_review_detail(wo)
    assert "55" in text or "F:" in text


def test_format_edit_diff_shows_changes():
    from bot.handlers.engineers import _format_edit_diff
    old_wo = {"title": "Old title", "description": "Old description"}
    text = _format_edit_diff(old_wo, new_title="New title", new_description="New description")
    assert "Old title" in text
    assert "New title" in text

"""Tests for the triage agent router."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_classify_query_message_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("What is the health score for Level 4?") == "analysis"


def test_classify_action_message_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Create a ticket for AHU e0402") == "resolution"


def test_classify_notify_message_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Send an alert to the technician") == "resolution"


def test_classify_show_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Show me the worst AHUs on Level 3") == "analysis"


def test_classify_fix_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Fix the phase imbalance issue on e0507") == "resolution"


def test_classify_why_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Why is e0301 in warning state?") == "analysis"


def test_classify_explain_returns_analysis():
    from agents.router import classify_intent
    assert classify_intent("Explain what FAIR scoring means") == "analysis"


def test_classify_approve_returns_resolution():
    from agents.router import classify_intent
    assert classify_intent("Approve the pending work order") == "resolution"


def test_classify_empty_defaults_to_analysis():
    from agents.router import classify_intent
    assert classify_intent("") == "analysis"

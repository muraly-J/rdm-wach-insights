import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from llm.persona_detector import detect_persona


def test_financial_keywords():
    assert detect_persona("What is the ROI of fixing this? How much does the TNB penalty cost?") == "financial"


def test_technician_keywords():
    assert detect_persona("I need to replace the capacitor and inspect the belt tension") == "technician"


def test_technical_keywords():
    assert detect_persona("What does the THD reading mean and how does phase imbalance affect the FAIR score?") == "technical"


def test_general_default():
    assert detect_persona("Why is the machine not working?") == "general"


def test_stated_persona_overrides_all():
    assert detect_persona(
        "What is the ROI of fixing this? TNB penalty?",
        stated_persona="technician",
    ) == "technician"


def test_role_command():
    assert detect_persona("/role financial — what does the score mean?") == "financial"


def test_explicit_engineer():
    assert detect_persona("I'm an engineer, give me the technical breakdown") == "technical"


def test_explicit_technician():
    assert detect_persona("I'm a technician, how do I fix this?") == "technician"


def test_history_reinforces_financial():
    history = [
        {"role": "user", "content": "What is the ROI of this maintenance?"},
        {"role": "user", "content": "How does the TNB penalty affect our budget?"},
    ]
    assert detect_persona("Tell me more about the cost", history=history) == "financial"


def test_empty_message_defaults_general():
    assert detect_persona("") == "general"


def test_mixed_signals_financial_wins():
    # financial has more keywords
    assert detect_persona(
        "What is the cost, ROI, budget impact, TNB tariff, and RM penalty?"
    ) == "financial"

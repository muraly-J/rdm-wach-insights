import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.query_classifier import classify_query_complexity


def test_short_status_query_is_fast():
    assert classify_query_complexity("What is the health of e0101?", []) == "fast"


def test_list_query_is_fast():
    assert classify_query_complexity("Show me level 3 devices", []) == "fast"


def test_is_device_query_is_fast():
    assert classify_query_complexity("Is e0301 healthy?", []) == "fast"


def test_how_many_query_is_fast():
    assert classify_query_complexity("How many devices are critical?", []) == "fast"


def test_why_question_is_think():
    assert classify_query_complexity("Why is e0101 showing high THD?", []) == "think"


def test_compare_question_is_think():
    assert classify_query_complexity("Compare level 3 and level 5 health scores", []) == "think"


def test_analyse_question_is_think():
    assert classify_query_complexity("Analyse the power factor trend for e0201 over time", []) == "think"


def test_recommend_question_is_think():
    assert classify_query_complexity("What should I do about the overload on level 2?", []) == "think"


def test_root_cause_question_is_think():
    assert classify_query_complexity("What is the root cause of the phase imbalance?", []) == "think"


def test_three_devices_is_think():
    assert classify_query_complexity("Compare e0101 e0102 and e0103 health scores", []) == "think"


def test_two_levels_is_think():
    assert classify_query_complexity("How does level 3 compare to level 5?", []) == "think"


def test_long_history_with_long_message_is_think():
    history = [{"role": "user"}, {"role": "assistant"}] * 3  # 6 turns
    msg = "Tell me more about what is happening with the energy anomaly scores across the building"
    assert classify_query_complexity(msg, history) == "think"


def test_long_history_with_short_message_is_fast():
    history = [{"role": "user"}, {"role": "assistant"}] * 3  # 6 turns
    msg = "What is the score?"
    assert classify_query_complexity(msg, history) == "fast"

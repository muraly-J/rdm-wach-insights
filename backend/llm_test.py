"""
Test script for Stage 3 — LLM Query Translation Engine
Run from the project root: python backend/llm_test.py

Requires LM Studio to be running with a model loaded.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm.translator import translate_query

print("\n" + "="*60)
print(" WACH INSIGHT - LLM TRANSLATION TEST ".center(60, "="))
print("="*60)

test_cases = [
    # (description, user_query, expect_success)
    ("Time-series by device ID",        "Show e0101 power consumption for the last 7 days",       True),
    ("Ranking query",                   "Rank the top 10 devices by average power this month",     True),
    ("Informal phrasing - energy",      "Which AHU uses the most energy this week?",               True),
    ("Specific device + voltage",       "Show me voltage for e0206 today",                         True),
    ("All-time ranking, smaller N",     "Top 5 devices by reactive power all time",                True),
    ("Unsupported metric - anomaly",    "Show me temperature anomalies for e0101",                 False),
    ("Completely off-topic",            "What's the weather like today?",                          False),
]

passed = 0
failed = 0

for description, query_text, expect_success in test_cases:
    print(f"\n[{'✅ expect pass' if expect_success else '🚫 expect fail'}] {description}")
    print(f"   Input: \"{query_text}\"")

    result, error = translate_query(query_text)

    if expect_success:
        if result:
            print(f"   ✅ Translated → type={result.query_type.value}, metric={result.metric}, "
                  f"range={result.time_range}, devices={result.device_ids}, top_n={result.top_n}")
            passed += 1
        else:
            print(f"   ❌ Expected success but got error: {error}")
            failed += 1
    else:
        if error:
            print(f"   ✅ Correctly rejected → {error[:80]}")
            passed += 1
        else:
            print(f"   ❌ Expected rejection but got: {result}")
            failed += 1

print("\n" + "="*60)
print(f" RESULTS: {passed}/{len(test_cases)} passed, {failed} failed ".center(60, "="))
print("="*60 + "\n")
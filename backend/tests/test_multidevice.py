"""
Test script for Task A — Multi-device comparison
Run from the project root: python3 backend/tests/test_multidevice.py
"""

import sys, os

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import asyncio
from backend.llm.translator import translate_query

async def run_tests():
    print("\n" + "="*60)
    print(" TASK A — MULTI-DEVICE COMPARISON TEST ".center(60, "="))
    print("="*60)

    cases = [
        # (description, query, expect_success, expected_device_count)
        ("vs syntax",            "Compare e0101 vs e0206 power last 7 days",          True, 2),
        ("and syntax",           "Show e0101 and e0206 energy today",                  True, 2),
        ("three devices",        "e0405 and e0410 and e0411 power last 7 days",        True, 3),
        ("comma list",           "Plot e0101, e0206, e0405 voltage this week",         True, 3),
        ("against syntax",       "Plot e0101 against e0206 power demand last 30 days", True, 2),
        ("single still works",   "Show e0101 power today",                             True, 1),
        ("ranking still works",  "Top 10 devices by energy this month",                True, 0),  # 0 = empty list
    ]

    passed = failed = 0

    for desc, query, expect_ok, expected_devices in cases:
        print(f"\n[{'✅ expect pass' if expect_ok else '🚫 expect fail'}] {desc}")
        print(f"   Input: \"{query}\"")

        result, error = await translate_query(query)

        if expect_ok:
            if result:
                device_count = len(result.device_ids)
                count_ok = device_count == expected_devices
                print(f"   type={result.query_type.value}, metric={result.metric}, "
                      f"range={result.time_range}, devices={result.device_ids}")
                if count_ok:
                    print(f"   ✅ Correct — {device_count} device(s) extracted")
                    passed += 1
                else:
                    print(f"   ❌ Expected {expected_devices} device(s), got {device_count}")
                    failed += 1
            else:
                print(f"   ❌ Expected success but got error: {error}")
                failed += 1
        else:
            if error:
                print(f"   ✅ Correctly rejected: {error[:60]}")
                passed += 1
            else:
                print(f"   ❌ Expected rejection but passed")
                failed += 1

    print("\n" + "="*60)
    print(f" RESULTS: {passed}/{len(cases)} passed, {failed} failed ".center(60, "="))
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_tests())

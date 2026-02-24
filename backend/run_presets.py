#!/usr/bin/env python3
"""Test preset prompts - limited set."""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8081/api/query"

# Test the critical presets that were failing
TEST_CASES = [
    ("Power: top 20", "Compare top 20 devices by power demand this week across all levels"),
    ("Power: levels 7,8,9", "Which 15 AHUs have the highest total power in levels 7, 8, and 9?"),
    ("Energy: top 10 all time", "Which 10 AHUs have the highest energy consumption all time?"),
    ("Efficiency: top 10 all levels", "Which 10 AHUs have the worst power factor across all levels?"),
    ("Current: top 10 all time", "Which 10 AHUs have the highest average current all time?"),
    ("Diagnostics: THD all levels", "Current THD comparison across all building levels — identify issues"),
    ("Reactive: top 10 all time", "Which 10 devices have the highest reactive energy import all time?"),
]

def test_query(name, query):
    """Test a single query and return detailed results."""
    try:
        response = requests.post(BASE_URL, json={
            "user_query": query,
            "session_id": f"preset-test-{name}"
        }, timeout=45)
        
        if response.status_code == 200:
            data = response.json()
            chart_data = data.get("chart", {}).get("data", [])
            
            # Get unique devices in chart
            chart_devices = [item.get("device_id") for item in chart_data if item.get("device_id")]
            unique_devices = list(dict.fromkeys(chart_devices))
            
            return {
                "ok": True,
                "device_ids_count": len(unique_devices),
                "chart_devices": unique_devices,
            }
        else:
            return {"ok": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def main():
    print("Testing critical preset prompts...")
    passed = 0
    failed = 0
    
    for name, query in TEST_CASES:
        print(f"[{name}]")
        
        result = test_query(name, query)
        
        if result["ok"]:
            devices_count = result["device_ids_count"]
            
            # Check for problematic patterns
            issues = []
            chart_devices = result["chart_devices"]
            
            if devices_count == 1 and "e0101" in chart_devices:
                issues.append("Only e0101 returned!")
            
            if "levels" in query.lower() and devices_count > 0:
                has_only_e01 = all(d and d.startswith("e01") for d in chart_devices)
                if has_only_e01 and devices_count < 5:
                    issues.append(f"Only e01xx devices ({devices_count}) for multi-level query!")
            
            if issues:
                print(f"  ✗ {devices_count} devices: {chart_devices}")
                for issue in issues:
                    print(f"      {issue}")
                failed += 1
            else:
                devices_preview = chart_devices[:5]
                suffix = '...' if len(chart_devices) > 5 else ''
                print(f"  ✓ {devices_count} devices: {devices_preview}{suffix}")
                passed += 1
        else:
            print(f"  ✗ Error: {result['error']}")
            failed += 1
    
    print()
    print(f"Summary: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

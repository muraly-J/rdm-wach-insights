#!/usr/bin/env python3
"""Test all preset prompts through the browser API."""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8081/api/query"

# All preset queries from ChatView.jsx
ALL_PRESETS = [
    # Power Comparisons - Level-specific
    ("Power: levels 1,2,3", "Compare power total of AHUs in levels 1, 2, and 3 for the past month"),
    ("Power: top 20", "Compare top 20 devices by power demand this week across all levels"),
    ("Power: levels 7,8,9", "Which 15 AHUs have the highest total power in levels 7, 8, and 9?"),
    ("Power: all AHUs", "Show me a comparison of power usage across all AHUs today"),
    ("Power: rank top 10", "Rank top 10 devices by max power demand this month"),
    ("Power: compare e0206 vs e0301", "Compare e0206 vs e0301 power today"),
    
    # Energy Analysis
    ("Energy: levels 4,5,6", "Compare energy import of AHUs in levels 4, 5, and 6 last month"),
    ("Energy: top 10 all time", "Which 10 AHUs have the highest energy consumption all time?"),
    ("Energy: levels 1-3", "Show me total energy usage for levels 1-3 compared this week"),
    ("Energy: compare e0206 vs e0401", "Compare e0206 vs e0401 energy import last 30 days"),
    ("Energy: top 5 all levels", "Top 5 energy hogs across all building levels this month"),
    ("Energy: level 11 vs 1", "Energy consumption comparison: AHUs in level 11 vs level 1"),
    
    # Efficiency Insights
    ("Efficiency: levels 2,3", "Compare power factor of AHUs in levels 2 and 3 this month — find inefficiencies"),
    ("Efficiency: top 10 all levels", "Which 10 AHUs have the worst power factor across all levels?"),
    ("Efficiency: compare e0105 vs e0308", "Show me power factor comparison between e0105 and e0308 last 30 days"),
    ("Efficiency: top 15 ranking", "Efficiency ranking: compare top 15 devices by average power factor today"),
    ("Efficiency: levels 7-10", "Power factor comparison across levels 7, 8, 9, and 10 this week"),
    ("Efficiency: levels 1-3 worst", "Which AHUs in levels 1-3 have the lowest power factor today?"),
    
    # Current & Voltage
    ("Current: levels 4,5,6", "Compare current usage across AHUs in levels 4, 5, and 6 this week"),
    ("Current: L1,L2,L3 e0206", "Voltage comparison: show phases L1, L2, L3 for e0206 today"),
    ("Current: top 10 all time", "Which 10 AHUs have the highest average current all time?"),
    ("Current: compare e0307 vs e0112", "Compare e0307 vs e0112 voltage levels last 7 days"),
    ("Current: all AHUs unbalance", "Current unbalance comparison across all AHUs this month"),
    ("Current: THD levels 1-3", "Voltage THD comparison: levels 1, 2, and 3 today"),
    
    # Diagnostics
    ("Diagnostics: THD all levels", "Current THD comparison across all building levels — identify issues"),
    ("Diagnostics: harmonics level 11 vs 1", "Show me voltage harmonics for AHUs in level 11 vs level 1"),
    ("Diagnostics: THD levels 2-5", "THD analysis for AHUs in levels 2-5 this month"),
    
    # Reactive Power
    ("Reactive: levels 1,2,3", "Compare reactive power of AHUs in levels 1, 2, and 3 this month"),
    ("Reactive: top 10 all time", "Which 10 devices have the highest reactive energy import all time?"),
    ("Reactive: levels 7-11", "Reactive power comparison: levels 7, 8, and 9 vs levels 10, 11"),
    ("Reactive: compare e0214 vs e0317", "Compare e0214 vs e0317 reactive power last 30 days"),
    ("Reactive: top consumers", "Top reactive power consumers across all AHUs this week"),
    ("Reactive: levels 4-6", "Reactive energy import comparison for levels 4-6 today"),
]

def test_query(name, query):
    """Test a single query and return detailed results."""
    try:
        response = requests.post(BASE_URL, json={
            "user_query": query,
            "session_id": f"preset-test-{name}"
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            chart_data = data.get("chart", {}).get("data", [])
            
            query_type = data.get("query_type")
            metric = data.get("metric", "")
            top_n = data.get("top_n")
            
            # Get unique devices in chart
            chart_devices = [item.get("device_id") for item in chart_data if item.get("device_id")]
            unique_devices = list(dict.fromkeys(chart_devices))
            
            # Check for problematic patterns
            issues = []
            
            # Issue: Only e0101 in chart when it should have multiple devices
            if len(unique_devices) == 1 and "e0101" in unique_devices:
                issues.append("WARNING: Only e0101 in chart!")
            
            # Issue: Chart devices don't match query expectations for multi-level queries
            if "levels" in query.lower():
                has_only_e01 = all(d and d.startswith("e01") for d in unique_devices)
                if len(unique_devices) > 0 and has_only_e01 and len(unique_devices) < 5:
                    issues.append(f"WARNING: Only e01xx devices ({len(unique_devices)}) for multi-level query!")
            
            return {
                "ok": True,
                "query_type": query_type,
                "metric": metric,
                "top_n": top_n,
                "device_ids_count": len(unique_devices),
                "chart_devices": unique_devices,
                "chart_data_points": len(chart_data),
                "summary_preview": data.get("summary", "")[:100] if data.get("summary") else "No summary",
                "issues": issues
            }
        else:
            return {"ok": False, "error": f"HTTP {response.status_code}: {response.text[:100]}"}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "TIMEOUT"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

def main():
    print("=" * 90)
    print("Preset Prompts Test - Browser UI Validation")
    print("=" * 90)
    print()
    
    results = []
    passed = 0
    failed = 0
    
    for name, query in ALL_PRESETS:
        print(f"[{name:35}] {query[:60]}...")
        
        result = test_query(name, query)
        
        if result["ok"]:
            chart_devices = result["chart_devices"]
            
            # Check for problematic patterns
            issues = []
            
            # Issue: Only e0101 in chart when it should have multiple devices
            if len(chart_devices) == 1 and "e0101" in chart_devices:
                issues.append("WARNING: Only e0101 in chart!")
            
            # Issue: Chart devices don't match query expectations for multi-level queries
            if "levels" in query.lower():
                has_only_e01 = all(d and d.startswith("e01") for d in chart_devices)
                if len(chart_devices) > 0 and has_only_e01 and len(chart_devices) < 5:
                    issues.append(f"WARNING: Only e01xx devices ({len(chart_devices)}) for multi-level query!")
            
            if issues:
                print(f"  ✗ {len(chart_devices)} devices in chart: {chart_devices}")
                for issue in issues:
                    print(f"      {issue}")
                failed += 1
            else:
                devices_preview = chart_devices[:5]
                suffix = '...' if len(chart_devices) > 5 else ''
                print(f"  ✓ {len(chart_devices)} devices: {devices_preview}{suffix}")
                passed += 1
        else:
            print(f"  ✗ Error: {result['error']}")
            failed += 1
        
        results.append({"name": name, "query": query, **result})
        
        # Small delay
        import time
        time.sleep(0.1)
    
    print()
    print("=" * 90)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 90)
    
    # List issues
    if failed > 0:
        print()
        print("Issues found:")
        for r in results:
            if not r.get("ok", False):
                print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")
            elif r.get("issues"):
                for issue in r["issues"]:
                    print(f"  - {r['name']}: {issue}")
    
    return failed

if __name__ == "__main__":
    sys.exit(main())

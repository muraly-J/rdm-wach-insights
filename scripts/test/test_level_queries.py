#!/usr/bin/env python3
import requests

BASE_URL = "http://127.0.0.1:8081/api/query"

# Device counts from AHU_LEVEL_CONFIG in schemas.py (parsed from TSV)
LEVELS = {
    "Level 1": {"expected_count": 21, "description": "e0101,e0102,... (including e0212)"},
    "Level 2": {"expected_count": 15, "description": "e0201,e0202,... (including e0213-e0218)"},
    "Level 3": {"expected_count": 16, "description": "e0210,e0211,... (including e0401,e0402,e0423)"},
    "Level 4": {"expected_count": 13, "description": "e0403,e0404,... (including e0406x2, e0419)"},
    "Level 5": {"expected_count": 12, "description": "e0501,e0502,... (including e0622)"},
    "Level 6": {"expected_count": 11, "description": "e0602,e0603,... (including e0611, e0625-e0628)"},
    "Level 7": {"expected_count": 4, "description": "e0701-e0704"},
    "Level 8": {"expected_count": 5, "description": "e0801-e0805"},
    "Level 9": {"expected_count": 8, "description": "e0901-e0908"},
    "Level 10": {"expected_count": 8, "description": "e1001-e1008"},
    "Level 11": {"expected_count": 8, "description": "e1101-e1108"},
}

def test_level(level_name, expected_count, description):
    query = f"compare power total of the ahus in {level_name} for the past 30 days"
    print(f"\n{'='*60}")
    print(f"Testing: {level_name}")
    print(f"Expected: {expected_count} devices ({description})")
    print(f"Query: {query}")
    
    try:
        response = requests.post(BASE_URL, json={
            "user_query": query,
            "session_id": f"test-{level_name.lower().replace(' ', '-')}"
        })
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            chart = result.get('chart', {})
            data_count = len(chart.get('data', []))
            
            print(f"Data count: {data_count}")
            
            if data_count == expected_count:
                print(f"✓ PASS - Got exactly {expected_count} devices")
                return True
            elif data_count == 21 and expected_count != 21:
                print(f"✗ FAIL - Got Level 1 data ({data_count}) instead of {expected_count}")
                return False
            else:
                print(f"✗ FAIL - Expected {expected_count}, got {data_count}")
                return False
        else:
            print(f"✗ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ FAIL - Exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing all AHU levels with power total query")
    
    results = {}
    for level_name, info in LEVELS.items():
        success = test_level(level_name, info["expected_count"], info["description"])
        results[level_name] = success
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    
    for level_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {level_name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

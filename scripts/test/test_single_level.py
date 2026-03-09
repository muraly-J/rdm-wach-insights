import requests
import json

# Test the query endpoint
url = "http://localhost:8081/api/query"
payload = {
    "user_query": "compare power total of the ahus in level 1 for the past 30 days",
    "session_id": "test-session-level1"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nQuery Type: {result.get('query_type')}")
        print(f"Device IDs count: {len(result.get('device_ids', []))}")
        
        chart = result.get('chart', {})
        print(f"Chart type: {chart.get('chart_type')}")
        print(f"Data count: {len(chart.get('data', []))}")
        
        if chart.get('data'):
            print("\nFirst 5 devices:")
            for item in chart['data'][:5]:
                print(f"  {item}")
            
            if len(chart['data']) > 5:
                print(f"\n... and {len(chart['data']) - 5} more devices")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")

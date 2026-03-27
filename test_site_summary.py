#!/usr/bin/env python3

import requests
import os

# Test the site summary endpoint to verify it works
def test_site_summary_endpoint():
    # Use the same base URL as the frontend
    base_url = "http://localhost:8081"
    
    try:
        # Test with 7d range (default)
        response = requests.get(f"{base_url}/api/site/summary?range=7d", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("Site Summary Data:")
            print(f"  Total AHUs: {data.get('totalAHUs', 'N/A')}")
            print(f"  Average Site Health: {data.get('avgSiteHealth', 'N/A')}")
            print(f"  AHUs in Alert: {data.get('ahusInAlert', 'N/A')}")
            print(f"  Estimated Monthly Cost: {data.get('estMonthlyCostMYR', 'N/A')}")
            print(f"  Star AHU: {data.get('starAHU', 'N/A')}")
            print(f"  Critical AHU: {data.get('criticalAHU', 'N/A')}")
            print(f"  Level Tiles Count: {len(data.get('levelTiles', []))}")
            print(f"  Trend Deltas Count: {len(data.get('trendDeltas', []))}")
        else:
            print("Error response:")
            try:
                error_data = response.json()
                print(f"  Error Details: {error_data}")
            except:
                print(f"  Response text: {response.text}")
                
    except Exception as e:
        print(f"Error connecting to endpoint: {e}")

if __name__ == "__main__":
    test_site_summary_endpoint()
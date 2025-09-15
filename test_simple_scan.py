#!/usr/bin/env python3
"""Test script to verify basic scan endpoint"""

import requests
import json

# Test the basic scan endpoint first
url = "http://localhost:5001/scan"
params = {
    "max_price": "5.00",
    "min_delta": "0.20",
    "max_delta": "0.40"
}

print("Testing basic scan endpoint...")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    print("\n✅ Response received:")
    print(f"Status: {data.get('status', 'unknown')}")
    
    # Show available keys
    print(f"Available keys: {list(data.keys())}")
    
    # Check different possible field names
    for field in ['final_opportunities', 'opportunities', 'top_picks', 'results']:
        if field in data:
            items = data[field]
            if isinstance(items, list):
                print(f"\nFound '{field}' field with {len(items)} items")
                if items:
                    print(f"First item keys: {list(items[0].keys())}")
            elif isinstance(items, dict):
                print(f"\nFound '{field}' field with {len(items)} keys")
                if items:
                    first_key = list(items.keys())[0]
                    print(f"First entry ({first_key}) keys: {list(items[first_key].keys())}")
                    
    # Save response to file for detailed analysis
    with open('scan_response.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\n📁 Full response saved to scan_response.json")
        
except requests.Timeout:
    print(f"❌ Request timed out after 30 seconds")
except Exception as e:
    print(f"❌ Error: {e}")
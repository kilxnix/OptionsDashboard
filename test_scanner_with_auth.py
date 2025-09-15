#!/usr/bin/env python3
"""Test scanner with authentication to verify response structure"""

import requests
import json

# Load test credentials
with open('test_credentials.json', 'r') as f:
    creds = json.load(f)

# Test the explosive-earnings-combo endpoint with auth
url = "http://localhost:5001/explosive-earnings-combo"
params = {
    "max_price": "5.00",
    "min_delta": "0.20",
    "max_delta": "0.40"
}

headers = {
    "Authorization": f"Bearer {creds['access_token']}"
}

print("Testing explosive-earnings-combo endpoint with authentication...")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    # Make a shorter timeout request to not wait for full scan
    response = requests.get(url, params=params, headers=headers, timeout=5)
    data = response.json()
    
    print("\n✅ Response received (may be partial due to timeout):")
    print(f"Status: {data.get('status', 'unknown')}")
    
except requests.Timeout:
    print("\n⏱️  Request timed out (scan still running)")
    
    # Test basic scan endpoint instead for quick response
    print("\nTesting basic scan endpoint...")
    scan_url = "http://localhost:5001/scan"
    response = requests.get(scan_url, params=params, headers=headers, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Basic scan response received")
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Available keys: {list(data.keys())}")
        
        # Check for opportunity fields
        for field in ['final_opportunities', 'opportunities', 'top_picks', 'results']:
            if field in data:
                items = data[field]
                if isinstance(items, list):
                    print(f"\nFound '{field}' with {len(items)} items")
                    if items:
                        first = items[0]
                        print(f"First item structure:")
                        print(f"  - Symbol: {first.get('symbol', 'N/A')}")
                        print(f"  - Keys: {list(first.keys())[:10]}")
                elif isinstance(items, dict):
                    print(f"\nFound '{field}' with {len(items)} entries")
                    
        # Save for analysis
        with open('scan_auth_response.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\n📁 Response saved to scan_auth_response.json")
    else:
        print(f"❌ Basic scan failed: {response.status_code}")
        print(response.json())
        
except Exception as e:
    print(f"❌ Error: {e}")
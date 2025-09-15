#!/usr/bin/env python3
"""Test script to verify scanner response structure"""

import requests
import json

# Test the explosive-earnings-combo endpoint directly
url = "http://localhost:5001/explosive-earnings-combo"
params = {
    "max_price": "5.00",
    "min_delta": "0.20",
    "max_delta": "0.40"
}

print("Testing explosive-earnings-combo endpoint...")
print(f"URL: {url}")
print(f"Params: {params}")

try:
    response = requests.get(url, params=params)
    data = response.json()
    
    print("\n✅ Response received:")
    print(f"Status: {data.get('status', 'unknown')}")
    
    # Check different possible field names
    if 'final_opportunities' in data:
        print(f"Found 'final_opportunities' field with {len(data['final_opportunities'])} items")
        if data['final_opportunities']:
            print("\nFirst opportunity structure:")
            first = data['final_opportunities'][0]
            print(json.dumps({
                'symbol': first.get('symbol'),
                'combined_score': first.get('combined_score'),
                'trade_plan_keys': list(first.get('trade_plan', {}).keys()) if 'trade_plan' in first else None,
                'all_keys': list(first.keys())
            }, indent=2))
            
            # Show the full trade_plan structure
            if 'trade_plan' in first:
                print("\nTrade plan structure:")
                print(json.dumps(first['trade_plan'], indent=2))
    
    elif 'opportunities' in data:
        print(f"Found 'opportunities' field with {len(data['opportunities'])} items")
    
    elif 'top_picks' in data:
        print(f"Found 'top_picks' field with {len(data['top_picks'])} items")
    
    else:
        print("No expected opportunity fields found in response")
        print("Available keys:", list(data.keys()))
        
except Exception as e:
    print(f"❌ Error: {e}")
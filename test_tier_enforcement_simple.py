#!/usr/bin/env python3
"""
Simple tier enforcement verification test
"""

import requests
import json
import sys
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:5001"

# Test user credentials
TEST_USERS = {
    'free': {'email': 'free@test.com', 'password': 'FreeUser123!'},
    'basic': {'email': 'basic@test.com', 'password': 'BasicUser123!'},
    'premium': {'email': 'premium@test.com', 'password': 'PremiumUser123!'},
    'admin': {'email': 'admin@test.com', 'password': 'AdminUser123!'}
}

def test_tier_enforcement():
    """Quick test of tier enforcement"""
    print("🚀 Testing Tier Enforcement")
    print("="*60)
    
    results = []
    
    for user_type, creds in TEST_USERS.items():
        print(f"\n📋 Testing {user_type} user...")
        
        # Login
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json=creds
        )
        
        if response.status_code != 200:
            print(f"  ❌ Failed to login: {response.status_code}")
            continue
        
        token = response.json().get('tokens', {}).get('access_token')
        print(f"  ✓ Logged in successfully")
        
        # Get user info
        response = requests.get(
            f"{API_BASE_URL}/api/auth/me",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            data = response.json()
            subscription = data.get('subscription', {})
            tier = subscription.get('tier', 'unknown')
            print(f"  ✓ User tier: {tier}")
            
            # Test premium endpoint access
            response = requests.get(
                f"{API_BASE_URL}/api/jpm-explosion-hunter",
                headers={'Authorization': f'Bearer {token}'},
                params={'limit': 1}  # Minimal params to avoid timeout
            )
            
            if user_type in ['premium', 'admin']:
                if response.status_code in [200, 204]:
                    print(f"  ✅ Can access premium endpoints")
                    results.append(f"{user_type}: PASS - Premium access works")
                else:
                    print(f"  ❌ Cannot access premium endpoints (got {response.status_code})")
                    results.append(f"{user_type}: FAIL - Should have premium access")
            else:
                if response.status_code == 403:
                    print(f"  ✅ Correctly blocked from premium endpoints")
                    results.append(f"{user_type}: PASS - Correctly restricted")
                else:
                    print(f"  ❌ Should be blocked from premium endpoints (got {response.status_code})")
                    results.append(f"{user_type}: FAIL - Should be blocked")
        else:
            print(f"  ❌ Failed to get user info: {response.status_code}")
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    for result in results:
        print(result)
    
    # Check if all tests passed
    failed = any("FAIL" in r for r in results)
    if not failed:
        print("\n✅ All tier enforcement tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_tier_enforcement())
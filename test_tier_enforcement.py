#!/usr/bin/env python3
"""
Test script to verify tier enforcement in scanner endpoints
"""
import requests
import json
import sys

# Base URL
BASE_URL = "http://localhost:5001"

# Test users with different tiers
TEST_USERS = {
    'free': {
        'email': 'free_test@example.com',
        'password': 'FreeTest123!',
        'first_name': 'Free',
        'last_name': 'User'
    },
    'basic': {
        'email': 'basic_test@example.com', 
        'password': 'BasicTest123!',
        'first_name': 'Basic',
        'last_name': 'User'
    },
    'premium': {
        'email': 'premium_test@example.com',
        'password': 'PremiumTest123!',
        'first_name': 'Premium',
        'last_name': 'User'
    }
}

def register_user(user_data):
    """Register a new test user"""
    print(f"Registering {user_data['first_name']} user...")
    response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
    if response.status_code == 409:
        print(f"  User already exists, attempting login...")
        return login_user(user_data['email'], user_data['password'])
    elif response.status_code == 201:
        data = response.json()
        print(f"  ✓ Registered successfully")
        return data['tokens']['access_token']
    else:
        print(f"  ✗ Registration failed: {response.text}")
        return None

def login_user(email, password):
    """Login a user and get access token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        'email': email,
        'password': password
    })
    if response.status_code == 200:
        data = response.json()
        return data['tokens']['access_token']
    else:
        print(f"  ✗ Login failed: {response.text}")
        return None

def get_user_info(token):
    """Get user information including tier"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  ✗ Failed to get user info: {response.text}")
        return None

def test_scanner_endpoint(endpoint, token, params=None):
    """Test a scanner endpoint with given token"""
    headers = {'Authorization': f'Bearer {token}'}
    url = f"{BASE_URL}/{endpoint}"
    
    if params:
        response = requests.get(url, headers=headers, params=params)
    else:
        response = requests.get(url, headers=headers)
    
    return response

def test_tier_enforcement():
    """Main test function"""
    print("=" * 60)
    print("TESTING TIER ENFORCEMENT")
    print("=" * 60)
    
    # Register test users and get tokens
    tokens = {}
    for tier, user_data in TEST_USERS.items():
        token = register_user(user_data)
        if token:
            tokens[tier] = token
    
    if not tokens:
        print("✗ Failed to create any test users")
        return
    
    print("\n" + "=" * 60)
    print("VERIFYING USER TIERS")
    print("=" * 60)
    
    # Verify user tiers
    for tier, token in tokens.items():
        print(f"\n{tier.upper()} User:")
        user_info = get_user_info(token)
        if user_info:
            subscription = user_info.get('subscription', {})
            print(f"  Plan: {subscription.get('plan', 'Unknown')}")
            print(f"  Tier: {subscription.get('tier', 'Unknown')}")
            print(f"  Status: {subscription.get('status', 'Unknown')}")
    
    print("\n" + "=" * 60)
    print("TESTING SCANNER ACCESS")
    print("=" * 60)
    
    # Test scanner endpoints with different tiers
    scanners = [
        ('scan', {'max_price': '10.00', 'min_delta': '0.10'}),
        ('explosive-scan', {'scan_type': 'comprehensive'}),
        ('api/jpm-explosion-hunter', {})
    ]
    
    for scanner, params in scanners:
        print(f"\n📊 Testing {scanner}:")
        for tier, token in tokens.items():
            print(f"  {tier.upper()} tier: ", end="")
            response = test_scanner_endpoint(scanner, token, params)
            
            if response.status_code == 200:
                data = response.json()
                # Check for applied limits
                if 'applied_limits' in data:
                    print(f"✓ Access granted (limits applied: {data['applied_limits']})")
                else:
                    print("✓ Full access granted")
            elif response.status_code == 403:
                data = response.json()
                print(f"🔒 Access denied - {data.get('message', 'Tier restriction')}")
            elif response.status_code == 429:
                print("⏱️ Rate limited")
            else:
                print(f"✗ Error {response.status_code}: {response.text[:100]}")
    
    print("\n" + "=" * 60)
    print("TESTING PARAMETER ENFORCEMENT")
    print("=" * 60)
    
    # Test parameter limits
    test_params = {
        'max_price': '20.00',  # Should be limited for free/basic
        'min_delta': '0.05',   # Should be limited for free/basic
        'max_delta': '0.95',   # Should be limited for free/basic
        'days_to_expiry': '60' # Should be limited for free/basic
    }
    
    print(f"\nTesting /scan with premium parameters:")
    print(f"  Parameters: {test_params}")
    
    for tier, token in tokens.items():
        print(f"\n  {tier.upper()} tier:")
        response = test_scanner_endpoint('scan', token, test_params)
        
        if response.status_code == 200:
            data = response.json()
            if 'applied_limits' in data:
                print(f"    ⚠️ Parameters adjusted: {data['applied_limits']}")
            else:
                print(f"    ✓ All parameters accepted")
            
            # Show actual parameters used
            if 'scan_parameters' in data:
                params = data['scan_parameters']
                print(f"    Actual max_price: {params.get('max_price', 'N/A')}")
                print(f"    Actual delta range: {params.get('min_delta', 'N/A')}-{params.get('max_delta', 'N/A')}")
                print(f"    Actual days: {params.get('days_to_expiry', 'N/A')}")
        else:
            print(f"    ✗ Error {response.status_code}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_tier_enforcement()
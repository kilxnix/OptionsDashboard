#!/usr/bin/env python3
"""
Final comprehensive test to verify tier enforcement is working properly
"""
import requests
import json
import sys
import time

# Base URL
BASE_URL = "http://localhost:5001"

# Test users with their expected tiers
TEST_USERS = {
    'free': {
        'email': 'free_test@example.com',
        'password': 'FreeTest123!',
        'expected_tier': 'free'
    },
    'basic': {
        'email': 'basic_test@example.com', 
        'password': 'BasicTest123!',
        'expected_tier': 'basic'
    },
    'premium': {
        'email': 'premium_test@example.com',
        'password': 'PremiumTest123!',
        'expected_tier': 'premium'
    }
}

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
        return None

def get_user_info(token):
    """Get user information including tier"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def test_scanner_access(endpoint, token, params=None):
    """Test a scanner endpoint with given token"""
    headers = {'Authorization': f'Bearer {token}'}
    url = f"{BASE_URL}/{endpoint}"
    
    # Use minimal params for scan test (just to test access, not full scan)
    test_params = params or {'limit': 1, 'dry_run': 'true'}
    
    response = requests.get(url, headers=headers, params=test_params, timeout=10)
    return response

def test_tier_enforcement():
    """Main test function"""
    print("=" * 70)
    print("FINAL TIER ENFORCEMENT VERIFICATION TEST")
    print("=" * 70)
    
    # Login test users and get tokens
    print("\n📝 STEP 1: LOGIN AND VERIFY TIERS")
    print("-" * 70)
    
    tokens = {}
    tier_verified = {}
    
    for user_type, user_data in TEST_USERS.items():
        print(f"\n{user_type.upper()} User:")
        token = login_user(user_data['email'], user_data['password'])
        if not token:
            print(f"  ✗ Failed to login")
            continue
            
        tokens[user_type] = token
        user_info = get_user_info(token)
        
        if user_info:
            actual_tier = user_info.get('subscription', {}).get('tier', 'unknown')
            expected_tier = user_data['expected_tier']
            
            if actual_tier == expected_tier:
                print(f"  ✓ Tier verified: {actual_tier}")
                tier_verified[user_type] = True
            else:
                print(f"  ✗ Tier mismatch! Expected: {expected_tier}, Got: {actual_tier}")
                tier_verified[user_type] = False
    
    print("\n" + "=" * 70)
    print("📊 STEP 2: TEST SCANNER ACCESS BY TIER")
    print("-" * 70)
    
    # Test matrix: endpoint -> expected access by tier
    test_matrix = {
        'scan': {
            'free': 'allowed',
            'basic': 'allowed',
            'premium': 'allowed'
        },
        'explosive-scan': {
            'free': 'denied',
            'basic': 'allowed',
            'premium': 'allowed'
        },
        'api/jpm-explosion-hunter': {
            'free': 'denied',
            'basic': 'denied',
            'premium': 'allowed'
        }
    }
    
    results = {}
    
    for endpoint, expectations in test_matrix.items():
        print(f"\n📍 Testing /{endpoint}:")
        endpoint_results = {}
        
        for tier, token in tokens.items():
            expected = expectations[tier]
            print(f"  {tier.upper():8} - Expected: {expected:7} - ", end="")
            
            try:
                response = test_scanner_access(endpoint, token)
                
                if response.status_code == 200:
                    actual = 'allowed'
                    print(f"✓ Access granted")
                elif response.status_code == 403:
                    actual = 'denied'
                    data = response.json()
                    print(f"🔒 Access denied")
                else:
                    actual = f'error-{response.status_code}'
                    print(f"✗ Error {response.status_code}")
                
                endpoint_results[tier] = (expected == actual)
                
            except Exception as e:
                print(f"✗ Exception: {str(e)[:50]}")
                endpoint_results[tier] = False
        
        results[endpoint] = endpoint_results
    
    print("\n" + "=" * 70)
    print("🎯 STEP 3: TEST PARAMETER ENFORCEMENT")
    print("-" * 70)
    
    # Test with premium parameters that should be limited for lower tiers
    premium_params = {
        'max_price': '20.00',  # Should be limited to 0.50 for free, 1.00 for basic
        'min_delta': '0.05',   # Should be limited to 0.30 for free, 0.25 for basic
        'max_delta': '0.95',   # Should be limited to 0.70 for free, 0.75 for basic
        'days_to_expiry': '60', # Should be limited to 7 for free, 14 for basic
        'limit': '1'  # Keep small to avoid long scan
    }
    
    param_tests = {}
    
    print(f"\nTesting /scan with premium parameters:")
    print(f"  Input: max_price={premium_params['max_price']}, delta={premium_params['min_delta']}-{premium_params['max_delta']}, days={premium_params['days_to_expiry']}")
    print()
    
    for tier, token in tokens.items():
        print(f"  {tier.upper()} tier:")
        
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(f"{BASE_URL}/scan", headers=headers, params=premium_params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if limits were applied
                if 'applied_limits' in data:
                    print(f"    ⚠️  Parameters adjusted: {data['applied_limits'][:100]}")
                    param_tests[tier] = 'limited'
                else:
                    print(f"    ✓ All parameters accepted (no limits)")
                    param_tests[tier] = 'unlimited'
                    
                # Show tier info if present
                if 'tier' in data:
                    print(f"    ℹ️  Response tier: {data['tier']}")
                    
            else:
                print(f"    ✗ Error {response.status_code}")
                param_tests[tier] = 'error'
                
        except Exception as e:
            print(f"    ✗ Exception: {str(e)[:50]}")
            param_tests[tier] = 'error'
    
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("-" * 70)
    
    # Calculate overall pass/fail
    all_passed = True
    
    # Check tier verification
    print("\n1. Tier Verification:")
    for tier, verified in tier_verified.items():
        status = "✓ PASS" if verified else "✗ FAIL"
        print(f"   {tier:8} - {status}")
        if not verified:
            all_passed = False
    
    # Check scanner access
    print("\n2. Scanner Access Control:")
    for endpoint, endpoint_results in results.items():
        endpoint_passed = all([v for v in endpoint_results.values()])
        status = "✓ PASS" if endpoint_passed else "✗ FAIL"
        print(f"   /{endpoint:25} - {status}")
        if not endpoint_passed:
            all_passed = False
            for tier, passed in endpoint_results.items():
                if not passed:
                    print(f"      └─ {tier} tier failed")
    
    # Check parameter enforcement
    print("\n3. Parameter Enforcement:")
    expected_param_results = {
        'free': 'limited',
        'basic': 'limited',
        'premium': 'unlimited'
    }
    
    for tier, result in param_tests.items():
        expected = expected_param_results.get(tier, 'unknown')
        passed = (result == expected)
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"   {tier:8} - {status} (expected: {expected}, got: {result})")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Tier enforcement is working correctly.")
    else:
        print("⚠️  SOME TESTS FAILED. Review the results above.")
    print("=" * 70)

if __name__ == "__main__":
    test_tier_enforcement()
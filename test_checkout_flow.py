#!/usr/bin/env python3
"""
Test Stripe checkout flow for all subscription types
"""
import requests
import json
import sys

# Test configurations
BASE_URL = "http://localhost:5001/api"
TEST_USER = {
    "email": "test_checkout@example.com",
    "password": "Test123!@#",
    "first_name": "Test",
    "last_name": "User"
}

def test_checkout_flow():
    """Test the complete checkout flow for all subscription types"""
    print("=" * 60)
    print("TESTING STRIPE CHECKOUT FLOW")
    print("=" * 60)
    
    # Step 1: Register a new test user
    print("\n1. Registering test user...")
    response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    if response.status_code == 409:
        print("   User already exists, logging in...")
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
    
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to register/login: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    data = response.json()
    access_token = data["tokens"]["access_token"]
    print(f"✅ Authenticated as {TEST_USER['email']}")
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test configurations for each subscription type
    test_cases = [
        {
            "name": "Basic Monthly",
            "plan_tier": "basic",
            "billing_interval": "monthly",
            "currency": "usd"
        },
        {
            "name": "Basic Weekly",
            "plan_tier": "basic",
            "billing_interval": "weekly",
            "currency": "usd"
        },
        {
            "name": "Premium Monthly",
            "plan_tier": "premium",
            "billing_interval": "monthly",
            "currency": "usd"
        },
        {
            "name": "Premium Weekly",
            "plan_tier": "premium",
            "billing_interval": "weekly",
            "currency": "usd"
        },
        {
            "name": "Basic Weekly EUR",
            "plan_tier": "basic",
            "billing_interval": "weekly",
            "currency": "eur"
        },
        {
            "name": "Premium Weekly GBP",
            "plan_tier": "premium",
            "billing_interval": "weekly",
            "currency": "gbp"
        }
    ]
    
    print("\n2. Testing checkout session creation for all subscription types:")
    print("-" * 60)
    
    all_passed = True
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        print(f"   Plan: {test_case['plan_tier'].upper()}")
        print(f"   Billing: {test_case['billing_interval'].capitalize()}")
        print(f"   Currency: {test_case['currency'].upper()}")
        
        # Create checkout session
        response = requests.post(
            f"{BASE_URL}/stripe/create-checkout",
            headers=headers,
            json=test_case
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                print(f"   ✅ Checkout session created successfully!")
                print(f"      Session ID: {data.get('session_id', 'N/A')[:20]}...")
                print(f"      Checkout URL: {data.get('checkout_url', 'N/A')[:50]}...")
                print(f"      Billing Interval: {data.get('billing_interval', 'Not returned')}")
                if data.get('trial_days'):
                    print(f"      Trial Days: {data['trial_days']}")
            else:
                print(f"   ❌ Failed: {data.get('message', 'Unknown error')}")
                all_passed = False
        else:
            print(f"   ❌ HTTP {response.status_code} Error")
            try:
                error_data = response.json()
                print(f"      Error: {error_data.get('message', 'Unknown error')}")
            except:
                print(f"      Response: {response.text[:200]}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED! Checkout flow is working correctly.")
    else:
        print("❌ SOME TESTS FAILED! Please check the errors above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_checkout_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
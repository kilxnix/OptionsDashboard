#!/usr/bin/env python
"""
Test script for Stripe integration
This script tests all Stripe-related endpoints and functionality
"""
import requests
import json
import time
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:5000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(test_name, success, message=""):
    """Print test result with color"""
    if success:
        print(f"{GREEN}✓{RESET} {test_name}")
        if message:
            print(f"  {message}")
    else:
        print(f"{RED}✗{RESET} {test_name}")
        if message:
            print(f"  {RED}{message}{RESET}")

def print_section(title):
    """Print section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def test_stripe_prices():
    """Test getting Stripe prices"""
    print_section("Testing Stripe Prices Endpoint")
    
    response = requests.get(f"{BASE_URL}/api/stripe/prices")
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success' and 'prices' in data:
            print_test("Get Stripe prices", True, f"Found {len(data['prices'])} pricing tiers")
            
            # Verify each tier
            expected_tiers = ['free', 'basic', 'premium', 'enterprise']
            found_tiers = [p['tier'] for p in data['prices']]
            
            for tier in expected_tiers:
                if tier in found_tiers:
                    price_info = next(p for p in data['prices'] if p['tier'] == tier)
                    print_test(f"  {tier.capitalize()} tier", True, 
                              f"${price_info['price_monthly']}/month")
                else:
                    print_test(f"  {tier.capitalize()} tier", False, "Tier not found")
            
            return True
        else:
            print_test("Get Stripe prices", False, "Invalid response format")
            return False
    else:
        print_test("Get Stripe prices", False, f"HTTP {response.status_code}")
        return False

def test_user_registration():
    """Test user registration with free tier"""
    print_section("Testing User Registration")
    
    # Generate unique email
    timestamp = int(time.time())
    email = f"test_{timestamp}@example.com"
    
    payload = {
        "email": email,
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "company": "Test Company"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
    
    if response.status_code == 201:
        data = response.json()
        if data['status'] == 'success':
            print_test("User registration", True, f"Registered {email}")
            print_test("  Free tier assigned", data['user']['plan'] == 'Free Tier')
            print_test("  Access token received", 'access_token' in data['tokens'])
            print_test("  Refresh token received", 'refresh_token' in data['tokens'])
            
            return data['tokens']['access_token'], data['user']['id']
        else:
            print_test("User registration", False, data.get('message', 'Unknown error'))
            return None, None
    else:
        print_test("User registration", False, f"HTTP {response.status_code}")
        return None, None

def test_subscription_info(access_token):
    """Test getting subscription information"""
    print_section("Testing Subscription Info")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{BASE_URL}/api/stripe/subscription", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success' and 'subscription' in data:
            sub = data['subscription']
            print_test("Get subscription info", True, 
                      f"Current plan: {sub['plan']} ({sub['tier']})")
            print_test("  Subscription status", sub['status'] == 'active')
            print_test("  Price", True, f"${sub['price']}/month")
            
            # Check features
            features = sub.get('features', {})
            print(f"\n  {YELLOW}Features:{RESET}")
            for feature, enabled in features.items():
                status = f"{GREEN}✓{RESET}" if enabled else f"{RED}✗{RESET}"
                print(f"    {status} {feature.replace('_', ' ').title()}")
            
            return True
        else:
            print_test("Get subscription info", False, "Invalid response format")
            return False
    else:
        print_test("Get subscription info", False, f"HTTP {response.status_code}")
        return False

def test_checkout_session(access_token, plan_tier='premium'):
    """Test creating Stripe checkout session"""
    print_section(f"Testing Checkout Session Creation ({plan_tier})")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"plan_tier": plan_tier}
    
    response = requests.post(f"{BASE_URL}/api/stripe/create-checkout", 
                            json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            print_test("Create checkout session", True)
            print_test("  Session ID", bool(data.get('session_id')))
            print_test("  Checkout URL", bool(data.get('checkout_url')))
            
            if 'trial_days' in data:
                print_test("  Trial period", True, f"{data['trial_days']} days")
            
            print(f"\n  {YELLOW}Checkout URL:{RESET}")
            print(f"  {data['checkout_url'][:80]}...")
            
            return data['session_id']
        else:
            print_test("Create checkout session", False, data.get('message', 'Unknown error'))
            return None
    else:
        print_test("Create checkout session", False, f"HTTP {response.status_code}")
        return None

def test_portal_session(access_token):
    """Test creating customer portal session"""
    print_section("Testing Customer Portal Session")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.post(f"{BASE_URL}/api/stripe/create-portal", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'success':
            print_test("Create portal session", True)
            print(f"\n  {YELLOW}Portal URL:{RESET}")
            print(f"  {data['portal_url'][:80]}...")
            return True
        else:
            print_test("Create portal session", False, data.get('message', 'Unknown error'))
            return False
    elif response.status_code == 404:
        print_test("Create portal session", True, 
                  "Expected: No subscription yet (user needs to complete checkout first)")
        return True
    else:
        print_test("Create portal session", False, f"HTTP {response.status_code}")
        return False

def test_api_key_creation(access_token):
    """Test API key creation"""
    print_section("Testing API Key Management")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"name": "Test API Key"}
    
    response = requests.post(f"{BASE_URL}/api/auth/api-keys", 
                            json=payload, headers=headers)
    
    if response.status_code == 201:
        data = response.json()
        if data['status'] == 'success':
            print_test("Create API key", True)
            api_key = data['api_key']['key']
            print(f"  {YELLOW}API Key:{RESET} {api_key[:20]}...")
            
            # Test using API key
            headers = {"X-API-Key": api_key}
            response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
            print_test("  Authenticate with API key", response.status_code == 200)
            
            return api_key
        else:
            print_test("Create API key", False, data.get('message', 'Unknown error'))
            return None
    else:
        print_test("Create API key", False, f"HTTP {response.status_code}")
        return None

def run_all_tests():
    """Run all Stripe integration tests"""
    print(f"\n{BLUE}╔{'═'*58}╗{RESET}")
    print(f"{BLUE}║{'Options Scanner - Stripe Integration Test Suite':^58}║{RESET}")
    print(f"{BLUE}╚{'═'*58}╝{RESET}")
    
    # Track test results
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Get Stripe prices
    if test_stripe_prices():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 2: Register new user
    access_token, user_id = test_user_registration()
    if access_token:
        tests_passed += 1
        
        # Test 3: Get subscription info
        if test_subscription_info(access_token):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 4: Create checkout session
        session_id = test_checkout_session(access_token, 'premium')
        if session_id:
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 5: Create portal session
        if test_portal_session(access_token):
            tests_passed += 1
        else:
            tests_failed += 1
        
        # Test 6: Create API key
        if test_api_key_creation(access_token):
            tests_passed += 1
        else:
            tests_failed += 1
    else:
        tests_failed += 1
        print(f"\n{RED}Cannot continue tests without authentication{RESET}")
    
    # Print summary
    print_section("Test Summary")
    total_tests = tests_passed + tests_failed
    success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"{GREEN}Passed: {tests_passed}{RESET}")
    print(f"{RED}Failed: {tests_failed}{RESET}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if tests_failed == 0:
        print(f"\n{GREEN}✅ All tests passed successfully!{RESET}")
    else:
        print(f"\n{RED}⚠️  Some tests failed. Please review the output above.{RESET}")
    
    print(f"\n{YELLOW}Note: This test uses Stripe test mode.{RESET}")
    print(f"{YELLOW}To complete the integration:{RESET}")
    print(f"1. Configure webhook endpoint in Stripe Dashboard")
    print(f"2. Set STRIPE_WEBHOOK_SECRET environment variable")
    print(f"3. Test webhook processing with Stripe CLI")

if __name__ == "__main__":
    run_all_tests()
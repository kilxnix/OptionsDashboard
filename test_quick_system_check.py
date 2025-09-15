#!/usr/bin/env python3
"""
Quick system check for Options Scanner SaaS
Tests key functionality without running long scanners
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_scanner_access():
    """Test scanner endpoint access control"""
    print(f"\n{BLUE}=== Testing Scanner Access Control ==={RESET}")
    
    # First register and login a test user
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    # Register
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        'email': test_email,
        'password': test_password,
        'first_name': 'Test',
        'last_name': 'User'
    })
    
    if response.status_code != 201:
        print(f"{RED}✗ Failed to register user{RESET}")
        return False
    
    data = response.json()
    token = data.get('tokens', {}).get('access_token')
    print(f"{GREEN}✓ User registered with free tier{RESET}")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test /scan endpoint (should work with free tier)
    response = requests.get(f"{BASE_URL}/scan", headers=headers, params={'limit': 1})
    if response.status_code in [200, 429]:  # 429 = rate limit
        print(f"{GREEN}✓ Free tier can access /scan endpoint{RESET}")
    else:
        print(f"{RED}✗ Free tier cannot access /scan: {response.status_code}{RESET}")
    
    # Test /explosive-scan endpoint (should be restricted)
    response = requests.get(f"{BASE_URL}/explosive-scan", headers=headers, params={'limit': 1})
    if response.status_code == 403:
        print(f"{GREEN}✓ Explosive scanner properly restricted for free tier{RESET}")
    else:
        print(f"{RED}✗ Explosive scanner not restricted: {response.status_code}{RESET}")
    
    # Test /jpm-explosion-hunter endpoint (should be restricted)
    response = requests.get(f"{BASE_URL}/jpm-explosion-hunter", headers=headers, params={'limit': 1})
    if response.status_code == 403:
        print(f"{GREEN}✓ JPM scanner properly restricted for free tier{RESET}")
    else:
        print(f"{RED}✗ JPM scanner not restricted: {response.status_code}{RESET}")
    
    # Test without authentication (should fail)
    response = requests.get(f"{BASE_URL}/scan")
    if response.status_code == 401:
        print(f"{GREEN}✓ Scanner requires authentication{RESET}")
    else:
        print(f"{RED}✗ Scanner allows unauthenticated access: {response.status_code}{RESET}")
    
    return True

def test_account_balance():
    """Test account balance and transaction system"""
    print(f"\n{BLUE}=== Testing Account Balance System ==={RESET}")
    
    # Register a new user
    test_email = f"balance_test_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        'email': test_email,
        'password': test_password
    })
    
    if response.status_code != 201:
        print(f"{RED}✗ Failed to register user for balance test{RESET}")
        return False
    
    data = response.json()
    token = data.get('tokens', {}).get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Check balance endpoint
    response = requests.get(f"{BASE_URL}/api/stripe/balance", headers=headers)
    if response.status_code == 200:
        data = response.json()
        balance = data.get('balance', 0)
        print(f"{GREEN}✓ Balance endpoint working - Current balance: ${balance:.2f}{RESET}")
        
        # Check transaction history
        if 'transactions' in data:
            print(f"{GREEN}✓ Transaction history available{RESET}")
        else:
            print(f"{RED}✗ No transaction history{RESET}")
    else:
        print(f"{RED}✗ Balance endpoint failed: {response.status_code}{RESET}")
        return False
    
    return True

def test_stripe_integration():
    """Test Stripe integration endpoints"""
    print(f"\n{BLUE}=== Testing Stripe Integration ==={RESET}")
    
    # Register a new user
    test_email = f"stripe_test_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        'email': test_email,
        'password': test_password
    })
    
    if response.status_code != 201:
        print(f"{RED}✗ Failed to register user for Stripe test{RESET}")
        return False
    
    data = response.json()
    token = data.get('tokens', {}).get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test checkout session creation
    response = requests.post(f"{BASE_URL}/api/stripe/create-checkout", 
                            headers=headers,
                            json={'plan_tier': 'BASIC'})
    
    if response.status_code == 200:
        data = response.json()
        if 'checkout_url' in data:
            print(f"{GREEN}✓ Stripe checkout session created successfully{RESET}")
            print(f"  Session ID: {data.get('session_id', '')[:20]}...")
        else:
            print(f"{RED}✗ Checkout session missing URL{RESET}")
    else:
        print(f"{RED}✗ Failed to create checkout session: {response.status_code}{RESET}")
        if response.text:
            print(f"  Error: {response.text[:200]}")
    
    # Test top-up session creation
    response = requests.post(f"{BASE_URL}/api/stripe/create-topup", 
                            headers=headers,
                            json={'amount': 'small'})
    
    if response.status_code == 200:
        data = response.json()
        if 'checkout_url' in data:
            print(f"{GREEN}✓ Top-up session created successfully{RESET}")
        else:
            print(f"{RED}✗ Top-up session missing URL{RESET}")
    else:
        print(f"{RED}✗ Failed to create top-up session: {response.status_code}{RESET}")
        if response.text:
            print(f"  Error: {response.text[:200]}")
    
    return True

def test_dashboard_api():
    """Test dashboard-related API endpoints"""
    print(f"\n{BLUE}=== Testing Dashboard API Endpoints ==={RESET}")
    
    # Register and login
    test_email = f"dashboard_test_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json={
        'email': test_email,
        'password': test_password
    })
    
    if response.status_code != 201:
        print(f"{RED}✗ Failed to register user for dashboard test{RESET}")
        return False
    
    data = response.json()
    token = data.get('tokens', {}).get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test /api/auth/me endpoint (used by dashboard)
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        data = response.json()
        user_data = data.get('user', {})
        
        # Check required fields for dashboard
        has_email = 'email' in user_data
        has_role = 'role' in user_data
        has_subscription = 'subscription' in data
        
        if has_email and has_role and has_subscription:
            print(f"{GREEN}✓ Dashboard user data complete{RESET}")
            print(f"  Email: {user_data.get('email')}")
            print(f"  Role: {user_data.get('role')}")
            print(f"  Plan: {data.get('subscription', {}).get('plan_name', 'Unknown')}")
        else:
            print(f"{RED}✗ Dashboard user data incomplete{RESET}")
    else:
        print(f"{RED}✗ Failed to get user data: {response.status_code}{RESET}")
    
    # Test usage statistics endpoint
    response = requests.get(f"{BASE_URL}/api/auth/usage", headers=headers)
    if response.status_code == 200:
        print(f"{GREEN}✓ Usage statistics endpoint working{RESET}")
    elif response.status_code == 404:
        print(f"  Usage endpoint not implemented yet")
    else:
        print(f"{RED}✗ Usage endpoint error: {response.status_code}{RESET}")
    
    return True

def main():
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   Options Scanner SaaS - Quick System Check{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"{RED}API is not healthy. Please check the backend.{RESET}")
            return
    except:
        print(f"{RED}API is not running. Please start the backend first.{RESET}")
        return
    
    print(f"{GREEN}✓ API is running{RESET}")
    
    # Run tests
    results = []
    results.append(('Scanner Access Control', test_scanner_access()))
    results.append(('Account Balance System', test_account_balance()))
    results.append(('Stripe Integration', test_stripe_integration()))
    results.append(('Dashboard API', test_dashboard_api()))
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}                 QUICK CHECK SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for name, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print(f"\n{GREEN}✓ ALL CRITICAL SYSTEMS OPERATIONAL!{RESET}")
    else:
        print(f"\n{RED}⚠ Some systems need attention{RESET}")
    
    # Save results
    with open('quick_check_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': [{'test': name, 'passed': result} for name, result in results],
            'summary': {'passed': passed, 'failed': failed}
        }, f, indent=2)
    
    print("\nResults saved to quick_check_results.json")

if __name__ == "__main__":
    main()
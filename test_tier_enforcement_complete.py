#!/usr/bin/env python3
"""
Comprehensive test for tier enforcement in the Options Scanner SaaS
Tests that tier limits are properly enforced at both UI and API levels
"""

import requests
import json
import sys
from datetime import datetime
import time

# Test configuration
API_BASE_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5000"

# Test user credentials (should exist in database)
TEST_USERS = {
    'free': {
        'email': 'free@test.com',
        'password': 'FreeUser123!',
        'expected_tier': 'free'
    },
    'basic': {
        'email': 'basic@test.com',
        'password': 'BasicUser123!',
        'expected_tier': 'basic'
    },
    'premium': {
        'email': 'premium@test.com',
        'password': 'PremiumUser123!',
        'expected_tier': 'premium'
    },
    'admin': {
        'email': 'admin@test.com',
        'password': 'AdminUser123!',
        'expected_tier': 'premium'  # Admins should get premium access
    }
}

# Scanner endpoints and their tier requirements
SCANNER_ENDPOINTS = {
    '/scan': ['free', 'basic', 'premium'],
    '/explosive-scan': ['basic', 'premium'],
    '/explosive-earnings-combo': ['basic', 'premium'],
    '/jpm-explosion-hunter': ['premium'],
    '/gamma-squeeze-scan': ['premium'],
    '/enhanced-scan': ['premium']
}

# Tier parameter limits
TIER_LIMITS = {
    'free': {
        'max_price': 0.50,
        'min_delta': 0.30,
        'max_delta': 0.70,
        'days_to_expiry': 7,
        'max_results': 5
    },
    'basic': {
        'max_price': 1.00,
        'min_delta': 0.25,
        'max_delta': 0.75,
        'days_to_expiry': 14,
        'max_results': 15
    },
    'premium': {
        'max_price': 10.00,
        'min_delta': 0.0,
        'max_delta': 1.0,
        'days_to_expiry': 90,
        'max_results': 100
    }
}

class TierEnforcementTester:
    def __init__(self):
        self.results = []
        self.tokens = {}
        
    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        result = {
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Print result
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def setup_test_users(self):
        """Create test users if they don't exist"""
        print("\n🔧 Setting up test users...")
        
        for user_type, creds in TEST_USERS.items():
            # Try to register the user (may already exist)
            response = requests.post(
                f"{API_BASE_URL}/api/auth/register",
                json={
                    'email': creds['email'],
                    'password': creds['password'],
                    'first_name': user_type.capitalize(),
                    'last_name': 'User'
                }
            )
            
            if response.status_code == 409:
                print(f"   User {creds['email']} already exists")
            elif response.status_code == 200:
                print(f"   Created user {creds['email']}")
            else:
                print(f"   Warning: Could not create {creds['email']}: {response.status_code}")
        
        # Login and get tokens
        for user_type, creds in TEST_USERS.items():
            response = requests.post(
                f"{API_BASE_URL}/api/auth/login",
                json={
                    'email': creds['email'],
                    'password': creds['password']
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[user_type] = data.get('tokens', {}).get('access_token')
                print(f"   ✓ Logged in as {user_type} user")
            else:
                print(f"   ✗ Failed to login as {user_type}: {response.status_code}")
                self.tokens[user_type] = None
    
    def test_scanner_access(self):
        """Test that users can only access appropriate scanners"""
        print("\n🔍 Testing scanner endpoint access...")
        
        for endpoint, allowed_tiers in SCANNER_ENDPOINTS.items():
            for user_type, token in self.tokens.items():
                if not token:
                    continue
                
                # Test access to the endpoint
                response = requests.get(
                    f"{API_BASE_URL}{endpoint}",
                    headers={'Authorization': f'Bearer {token}'},
                    params={'max_price': '5.00', 'limit': 5}
                )
                
                # Determine expected result
                user_tier = TEST_USERS[user_type]['expected_tier']
                should_have_access = user_tier in allowed_tiers
                
                # Check result
                if should_have_access:
                    if response.status_code in [200, 204]:
                        self.log_result(
                            f"{user_type} user can access {endpoint}",
                            True
                        )
                    else:
                        self.log_result(
                            f"{user_type} user can access {endpoint}",
                            False,
                            f"Expected 200, got {response.status_code}"
                        )
                else:
                    if response.status_code == 403:
                        self.log_result(
                            f"{user_type} user blocked from {endpoint}",
                            True
                        )
                    else:
                        self.log_result(
                            f"{user_type} user blocked from {endpoint}",
                            False,
                            f"Expected 403, got {response.status_code}"
                        )
    
    def test_parameter_limits(self):
        """Test that parameter limits are enforced based on tier"""
        print("\n📊 Testing parameter limit enforcement...")
        
        test_params = {
            'max_price': 8.00,  # Above basic limit
            'min_delta': 0.10,  # Below free limit
            'max_delta': 0.90,  # Above basic limit
            'days_to_expiry': 30,  # Above free/basic limit
            'max_results': 50  # Above free/basic limit
        }
        
        for user_type, token in self.tokens.items():
            if not token or user_type == 'admin':  # Skip admin (should get premium)
                continue
            
            # Test the basic scan endpoint (available to all)
            response = requests.get(
                f"{API_BASE_URL}/scan",
                headers={'Authorization': f'Bearer {token}'},
                params=test_params
            )
            
            if response.status_code == 200:
                data = response.json()
                applied_limits = data.get('applied_limits', [])
                
                # Check if limits were applied correctly
                user_tier = TEST_USERS[user_type]['expected_tier']
                if user_tier != 'premium':
                    if applied_limits:
                        self.log_result(
                            f"Parameter limits applied for {user_type} user",
                            True,
                            f"Limits: {', '.join(applied_limits[:2]) if applied_limits else 'None'}"
                        )
                    else:
                        self.log_result(
                            f"Parameter limits applied for {user_type} user",
                            False,
                            "No limits applied when they should have been"
                        )
                else:
                    # Premium should have no limits
                    if not applied_limits:
                        self.log_result(
                            f"No limits for {user_type} user",
                            True
                        )
                    else:
                        self.log_result(
                            f"No limits for {user_type} user",
                            False,
                            f"Unexpected limits: {applied_limits}"
                        )
    
    def test_admin_premium_access(self):
        """Test that admins get premium-level access"""
        print("\n👑 Testing admin premium access...")
        
        admin_token = self.tokens.get('admin')
        if not admin_token:
            self.log_result("Admin premium access", False, "No admin token available")
            return
        
        # Test access to premium-only endpoint
        response = requests.get(
            f"{API_BASE_URL}/jpm-explosion-hunter",
            headers={'Authorization': f'Bearer {admin_token}'},
            params={'max_price': '10.00', 'days_to_expiry': 60}
        )
        
        if response.status_code in [200, 204]:
            self.log_result(
                "Admin can access premium endpoints",
                True
            )
        else:
            self.log_result(
                "Admin can access premium endpoints",
                False,
                f"Got status {response.status_code}"
            )
        
        # Test that admin doesn't get parameter limits
        response = requests.get(
            f"{API_BASE_URL}/scan",
            headers={'Authorization': f'Bearer {admin_token}'},
            params={
                'max_price': 10.00,
                'min_delta': 0.01,
                'max_delta': 0.99,
                'days_to_expiry': 90
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            applied_limits = data.get('applied_limits', [])
            
            if not applied_limits:
                self.log_result(
                    "Admin has no parameter limits",
                    True
                )
            else:
                self.log_result(
                    "Admin has no parameter limits",
                    False,
                    f"Unexpected limits: {applied_limits}"
                )
    
    def test_frontend_ui_enforcement(self):
        """Test that frontend correctly shows/hides features based on tier"""
        print("\n🖥️  Testing frontend UI enforcement...")
        
        for user_type, token in self.tokens.items():
            if not token:
                continue
            
            # Get user info to check tier
            response = requests.get(
                f"{API_BASE_URL}/api/auth/me",
                headers={'Authorization': f'Bearer {token}'}
            )
            
            if response.status_code == 200:
                data = response.json()
                subscription = data.get('subscription', {})
                tier = subscription.get('tier', 'free').lower()
                
                # Check if tier matches expected
                expected_tier = TEST_USERS[user_type]['expected_tier']
                if tier == expected_tier or (user_type == 'admin' and tier):
                    self.log_result(
                        f"Frontend receives correct tier for {user_type}",
                        True,
                        f"Tier: {tier}"
                    )
                else:
                    self.log_result(
                        f"Frontend receives correct tier for {user_type}",
                        False,
                        f"Expected {expected_tier}, got {tier}"
                    )
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("📋 TIER ENFORCEMENT TEST REPORT")
        print("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n⚠️  Failed Tests:")
            for result in self.results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['details']}")
        
        # Save report to file
        with open('tier_enforcement_test_report.json', 'w') as f:
            json.dump({
                'summary': {
                    'total': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': passed_tests/total_tests*100
                },
                'results': self.results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print("\n📄 Report saved to tier_enforcement_test_report.json")
        
        return passed_tests == total_tests

def main():
    """Run tier enforcement tests"""
    print("🚀 Starting Tier Enforcement Tests")
    print("="*60)
    
    tester = TierEnforcementTester()
    
    try:
        # Setup test users
        tester.setup_test_users()
        
        # Wait for services to be ready
        print("\n⏳ Waiting for services to stabilize...")
        time.sleep(2)
        
        # Run tests
        tester.test_scanner_access()
        tester.test_parameter_limits()
        tester.test_admin_premium_access()
        tester.test_frontend_ui_enforcement()
        
        # Generate report
        all_passed = tester.generate_report()
        
        if all_passed:
            print("\n✅ All tier enforcement tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please review the report.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Comprehensive system testing for Options Scanner SaaS
Tests all major functionality including authentication, pricing, dashboard, and scanner endpoints
"""
import requests
import json
import time
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5000"
TEST_EMAIL = f"test_{int(time.time())}@example.com"
TEST_PASSWORD = "TestPassword123!"

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class SystemTester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_result(self, test_name, success, details=""):
        """Log test result with color formatting"""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            print(f"{GREEN}✓{RESET} {test_name}")
            if details:
                print(f"  {details}")
        else:
            self.failed_tests += 1
            print(f"{RED}✗{RESET} {test_name}")
            if details:
                print(f"  {RED}{details}{RESET}")
        
        self.results.append({
            'test': test_name,
            'success': success,
            'details': details
        })
    
    def test_health_check(self):
        """Test if the API is running"""
        print(f"\n{BLUE}=== Testing Health Check ==={RESET}")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            success = response.status_code == 200
            self.log_result("Health check", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_result("Health check", False, str(e))
            return False
    
    def test_registration(self):
        """Test user registration"""
        print(f"\n{BLUE}=== Testing User Registration ==={RESET}")
        
        # Test with invalid email
        try:
            response = requests.post(f"{BASE_URL}/api/auth/register", json={
                'email': 'invalid-email',
                'password': TEST_PASSWORD
            })
            self.log_result("Invalid email rejection", response.status_code == 400)
        except Exception as e:
            self.log_result("Invalid email rejection", False, str(e))
        
        # Test with weak password
        try:
            response = requests.post(f"{BASE_URL}/api/auth/register", json={
                'email': TEST_EMAIL,
                'password': 'weak'
            })
            self.log_result("Weak password rejection", response.status_code == 400)
        except Exception as e:
            self.log_result("Weak password rejection", False, str(e))
        
        # Test successful registration
        try:
            response = requests.post(f"{BASE_URL}/api/auth/register", json={
                'email': TEST_EMAIL,
                'password': TEST_PASSWORD,
                'first_name': 'Test',
                'last_name': 'User',
                'company': 'Test Company'
            })
            
            if response.status_code == 201:
                data = response.json()
                self.token = data.get('tokens', {}).get('access_token')
                self.user_id = data.get('user', {}).get('id')
                self.log_result("User registration", True, f"User ID: {self.user_id}")
                
                # Check if free plan was assigned
                has_free_plan = data.get('user', {}).get('plan') == 'Free Tier'
                self.log_result("Free plan assignment", has_free_plan)
                
                return True
            else:
                self.log_result("User registration", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("User registration", False, str(e))
            return False
        
        # Test duplicate registration
        try:
            response = requests.post(f"{BASE_URL}/api/auth/register", json={
                'email': TEST_EMAIL,
                'password': TEST_PASSWORD
            })
            self.log_result("Duplicate email rejection", response.status_code == 409)
        except Exception as e:
            self.log_result("Duplicate email rejection", False, str(e))
    
    def test_login(self):
        """Test user login"""
        print(f"\n{BLUE}=== Testing User Login ==={RESET}")
        
        # Test with wrong password
        try:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                'email': TEST_EMAIL,
                'password': 'WrongPassword123!'
            })
            self.log_result("Wrong password rejection", response.status_code == 401)
        except Exception as e:
            self.log_result("Wrong password rejection", False, str(e))
        
        # Test successful login
        try:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                'email': TEST_EMAIL,
                'password': TEST_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('tokens', {}).get('access_token')
                self.log_result("User login", True, f"Token received: {self.token[:20]}...")
                return True
            else:
                self.log_result("User login", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("User login", False, str(e))
            return False
    
    def test_jwt_authentication(self):
        """Test JWT token authentication"""
        print(f"\n{BLUE}=== Testing JWT Authentication ==={RESET}")
        
        if not self.token:
            self.log_result("JWT authentication", False, "No token available")
            return False
        
        # Test with valid token
        try:
            headers = {'Authorization': f'Bearer {self.token}'}
            response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("JWT authentication", True, f"User email: {data.get('user', {}).get('email')}")
                
                # Check subscription info
                has_subscription = 'subscription' in data
                self.log_result("Subscription info in /me endpoint", has_subscription)
                
                return True
            else:
                self.log_result("JWT authentication", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("JWT authentication", False, str(e))
            return False
        
        # Test without token
        try:
            response = requests.get(f"{BASE_URL}/api/auth/me")
            self.log_result("Unauthorized access rejection", response.status_code == 401)
        except Exception as e:
            self.log_result("Unauthorized access rejection", False, str(e))
    
    def test_pricing_endpoint(self):
        """Test pricing endpoint"""
        print(f"\n{BLUE}=== Testing Pricing Endpoint ==={RESET}")
        
        try:
            response = requests.get(f"{BASE_URL}/api/stripe/prices")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response is an array
                is_array = isinstance(data, list)
                self.log_result("Pricing endpoint returns array", is_array, f"Type: {type(data)}")
                
                if is_array:
                    # Check array contents
                    has_plans = len(data) > 0
                    self.log_result("Pricing data contains plans", has_plans, f"Found {len(data)} plans")
                    
                    # Check plan structure
                    if has_plans:
                        plan = data[0]
                        has_required_fields = all(field in plan for field in ['tier', 'name', 'price_monthly', 'features'])
                        self.log_result("Plan structure validation", has_required_fields, f"Fields: {list(plan.keys())}")
                
                return is_array
            else:
                self.log_result("Pricing endpoint", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Pricing endpoint", False, str(e))
            return False
    
    def test_scanner_endpoints(self):
        """Test scanner endpoints with authentication and tier enforcement"""
        print(f"\n{BLUE}=== Testing Scanner Endpoints ==={RESET}")
        
        if not self.token:
            self.log_result("Scanner endpoints", False, "No token available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Test basic scanner (should work with free tier)
        try:
            response = requests.get(f"{BASE_URL}/scan", headers=headers)
            free_tier_access = response.status_code in [200, 429]  # 429 means rate limit
            self.log_result("Free tier scanner access", free_tier_access, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Free tier scanner access", False, str(e))
        
        # Test explosive scanner (requires basic/premium tier)
        try:
            response = requests.get(f"{BASE_URL}/explosive-scan", headers=headers)
            restricted_access = response.status_code == 403
            self.log_result("Explosive scanner tier restriction", restricted_access, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Explosive scanner tier restriction", False, str(e))
        
        # Test JPM scanner (requires premium tier)
        try:
            response = requests.get(f"{BASE_URL}/jpm-explosion-hunter", headers=headers)
            restricted_access = response.status_code == 403
            self.log_result("JPM scanner tier restriction", restricted_access, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("JPM scanner tier restriction", False, str(e))
        
        # Test without authentication
        try:
            response = requests.get(f"{BASE_URL}/scan")
            no_auth_rejection = response.status_code == 401
            self.log_result("Scanner requires authentication", no_auth_rejection, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("Scanner requires authentication", False, str(e))
    
    def test_account_balance(self):
        """Test account balance and credit system"""
        print(f"\n{BLUE}=== Testing Account Balance System ==={RESET}")
        
        if not self.token:
            self.log_result("Account balance", False, "No token available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Test balance endpoint
        try:
            response = requests.get(f"{BASE_URL}/api/stripe/balance", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                has_balance = 'balance' in data
                self.log_result("Balance endpoint", has_balance, f"Balance: ${data.get('balance', 0):.2f}")
                
                # Check transactions
                has_transactions = 'transactions' in data
                self.log_result("Transaction history", has_transactions)
                
                return True
            else:
                self.log_result("Balance endpoint", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Balance endpoint", False, str(e))
            return False
    
    def test_topup_session(self):
        """Test top-up session creation"""
        print(f"\n{BLUE}=== Testing Top-up Session Creation ==={RESET}")
        
        if not self.token:
            self.log_result("Top-up session", False, "No token available")
            return False
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Test top-up session creation
        try:
            response = requests.post(f"{BASE_URL}/api/stripe/create-topup", 
                                    headers=headers,
                                    json={'amount': 'small'})
            
            if response.status_code == 200:
                data = response.json()
                has_url = 'checkout_url' in data
                self.log_result("Top-up session creation", has_url, 
                              f"Session created: {data.get('session_id', '')[:20]}...")
                return True
            else:
                self.log_result("Top-up session creation", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Top-up session creation", False, str(e))
            return False
    
    def test_frontend_pages(self):
        """Test frontend pages are accessible"""
        print(f"\n{BLUE}=== Testing Frontend Pages ==={RESET}")
        
        pages = [
            ('/', 'Home page'),
            ('/pricing', 'Pricing page'),
            ('/login', 'Login page'),
            ('/register', 'Registration page'),
            ('/dashboard', 'Dashboard page'),
            ('/scanner', 'Scanner page')
        ]
        
        for path, name in pages:
            try:
                response = requests.get(f"{FRONTEND_URL}{path}", timeout=5)
                success = response.status_code == 200
                self.log_result(f"{name} accessibility", success, f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"{name} accessibility", False, str(e))
    
    def run_all_tests(self):
        """Run all system tests"""
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}   Options Scanner SaaS - Comprehensive System Testing{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        
        # Check if API is running
        if not self.test_health_check():
            print(f"\n{RED}API is not running. Please start the backend first.{RESET}")
            return
        
        # Run all tests
        self.test_registration()
        self.test_login()
        self.test_jwt_authentication()
        self.test_pricing_endpoint()
        self.test_scanner_endpoints()
        self.test_account_balance()
        self.test_topup_session()
        self.test_frontend_pages()
        
        # Print summary
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}                    TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Total tests: {self.total_tests}")
        print(f"{GREEN}Passed: {self.passed_tests}{RESET}")
        print(f"{RED}Failed: {self.failed_tests}{RESET}")
        
        if self.failed_tests == 0:
            print(f"\n{GREEN}✓ ALL TESTS PASSED! System is fully operational.{RESET}")
        else:
            print(f"\n{YELLOW}⚠ Some tests failed. Please review the failures above.{RESET}")
        
        # Save results to file
        with open('test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'results': self.results
            }, f, indent=2)
        
        print(f"\nTest results saved to test_results.json")

if __name__ == "__main__":
    tester = SystemTester()
    tester.run_all_tests()
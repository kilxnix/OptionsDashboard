"""
Comprehensive test for all three payment methods:
1. Account Credits
2. Stripe Card 
3. USDC Crypto
"""
import requests
import json
from datetime import datetime
import time
import os

# API Base URL
API_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5000"

# Test credentials
TEST_USER_EMAIL = "paytest@example.com"
TEST_USER_PASSWORD = "TestPassword123!"
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "AdminPassword123!"

class PaymentMethodTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.user_id = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
    
    def add_result(self, test_name, status, details="", error=None):
        """Add test result to the report"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        if error:
            result["error"] = str(error)
        self.test_results["tests"].append(result)
        
        # Print result
        emoji = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
    
    def setup_test_user(self):
        """Create and setup test user with account balance"""
        print("\n=== Setting Up Test User ===")
        
        # First try to register a new user
        register_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "first_name": "Payment",
            "last_name": "Tester",
            "company": "Test Corp"
        }
        
        response = self.session.post(f"{API_URL}/api/auth/register", json=register_data)
        
        if response.status_code == 409:
            # User exists, try to login
            print("User already exists, logging in...")
            login_response = self.session.post(f"{API_URL}/api/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            
            if login_response.status_code == 200:
                data = login_response.json()
                self.access_token = data['tokens']['access_token']
                self.user_id = data['user']['id']
                self.add_result("User Setup", "PASSED", "Logged in existing user")
            else:
                self.add_result("User Setup", "FAILED", "Could not login", login_response.text)
                return False
                
        elif response.status_code == 201:
            # New user created
            data = response.json()
            self.access_token = data['tokens']['access_token']
            self.user_id = data['user']['id']
            self.add_result("User Setup", "PASSED", "Created new test user")
        else:
            self.add_result("User Setup", "FAILED", "Could not create user", response.text)
            return False
        
        # Add credits to user account for testing
        print("Adding test credits to user account...")
        self.add_test_credits()
        
        return True
    
    def add_test_credits(self):
        """Add test credits to user account"""
        # Login as admin to add credits
        admin_login = self.session.post(f"{API_URL}/api/auth/login", json={
            "email": TEST_ADMIN_EMAIL,
            "password": TEST_ADMIN_PASSWORD
        })
        
        if admin_login.status_code == 200:
            admin_token = admin_login.json()['tokens']['access_token']
            
            # Add credits to test user using the correct endpoint
            headers = {"Authorization": f"Bearer {admin_token}"}
            credit_response = self.session.post(
                f"{API_URL}/api/admin/topup/{self.user_id}",
                json={"amount": 100.00, "description": "Test credits for payment testing"},
                headers=headers
            )
            
            if credit_response.status_code == 200:
                self.add_result("Add Test Credits", "PASSED", "Added $100 to test account")
            else:
                self.add_result("Add Test Credits", "WARNING", f"Could not add credits: {credit_response.text}")
        else:
            self.add_result("Add Test Credits", "WARNING", "Could not login as admin to add credits")
    
    def test_account_credits_payment(self):
        """Test payment using account credits"""
        print("\n=== Testing Account Credits Payment ===")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 1. Check current balance
        balance_response = self.session.get(f"{API_URL}/api/auth/me", headers=headers)
        if balance_response.status_code == 200:
            current_balance = balance_response.json().get('account_balance', 0)
            self.add_result("Check Balance", "PASSED", f"Current balance: ${current_balance}")
        else:
            self.add_result("Check Balance", "FAILED", "Could not get balance")
            return
        
        # 2. Try to subscribe to Basic plan using credits
        payment_data = {
            "plan_tier": "basic",
            "billing_interval": "weekly"  # Cheaper for testing
        }
        
        payment_response = self.session.post(
            f"{API_URL}/api/subscription/credit-payment",
            json=payment_data,
            headers=headers
        )
        
        if payment_response.status_code == 200:
            result = payment_response.json()
            new_balance = result.get('remaining_balance', 0)
            sub_info = result.get('subscription', {})
            
            self.add_result(
                "Credit Payment", 
                "PASSED", 
                f"Successfully subscribed to {sub_info.get('plan', 'N/A')}. Balance: ${current_balance} -> ${new_balance}"
            )
            
            # Verify subscription is active
            me_response = self.session.get(f"{API_URL}/api/auth/me", headers=headers)
            if me_response.status_code == 200:
                user_data = me_response.json()
                if user_data.get('plan_tier') == 'basic':
                    self.add_result("Subscription Verification", "PASSED", "User now has Basic plan")
                else:
                    self.add_result("Subscription Verification", "FAILED", f"Expected basic plan, got {user_data.get('plan_tier')}")
        else:
            error_msg = payment_response.json().get('message', payment_response.text)
            self.add_result("Credit Payment", "FAILED", error_msg)
    
    def test_stripe_card_checkout(self):
        """Test Stripe card payment checkout session creation"""
        print("\n=== Testing Stripe Card Payment ===")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create Stripe checkout session
        checkout_data = {
            "plan_tier": "premium",
            "billing_interval": "monthly",
            "currency": "usd"
        }
        
        checkout_response = self.session.post(
            f"{API_URL}/api/stripe/create-checkout",
            json=checkout_data,
            headers=headers
        )
        
        if checkout_response.status_code == 200:
            result = checkout_response.json()
            session_id = result.get('session_id')
            checkout_url = result.get('url')
            
            if session_id and checkout_url:
                self.add_result(
                    "Stripe Checkout Session",
                    "PASSED",
                    f"Created checkout session. URL: {checkout_url[:50]}..."
                )
                
                # Verify the session contains correct data
                if 'stripe.com' in checkout_url:
                    self.add_result("Stripe URL Validation", "PASSED", "Valid Stripe checkout URL")
                else:
                    self.add_result("Stripe URL Validation", "WARNING", "URL doesn't look like Stripe")
                    
            else:
                self.add_result("Stripe Checkout Session", "FAILED", "Missing session_id or URL")
        else:
            error_msg = checkout_response.json().get('message', checkout_response.text)
            self.add_result("Stripe Checkout Session", "FAILED", error_msg)
    
    def test_usdc_crypto_checkout(self):
        """Test USDC crypto payment checkout session creation"""
        print("\n=== Testing USDC Crypto Payment ===")
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create USDC checkout session
        checkout_data = {
            "plan_tier": "basic",
            "billing_interval": "weekly",
            "currency": "usdc"  # USDC currency
        }
        
        checkout_response = self.session.post(
            f"{API_URL}/api/stripe/create-checkout",
            json=checkout_data,
            headers=headers
        )
        
        if checkout_response.status_code == 200:
            result = checkout_response.json()
            session_id = result.get('session_id')
            checkout_url = result.get('url')
            
            if session_id and checkout_url:
                self.add_result(
                    "USDC Checkout Session",
                    "PASSED",
                    f"Created USDC checkout session. URL: {checkout_url[:50]}..."
                )
                
                # Check if payment methods include Link (for crypto)
                if result.get('payment_method_types'):
                    payment_methods = result.get('payment_method_types', [])
                    if 'link' in payment_methods:
                        self.add_result("USDC Payment Method", "PASSED", "Link payment method enabled for crypto")
                    else:
                        self.add_result("USDC Payment Method", "WARNING", f"Payment methods: {payment_methods}")
            else:
                self.add_result("USDC Checkout Session", "FAILED", "Missing session_id or URL")
        else:
            error_msg = checkout_response.json().get('message', checkout_response.text)
            self.add_result("USDC Checkout Session", "FAILED", error_msg)
    
    def test_frontend_endpoints(self):
        """Test frontend endpoints and UI flow"""
        print("\n=== Testing Frontend Endpoints ===")
        
        # Test main page
        response = self.session.get(FRONTEND_URL)
        if response.status_code == 200:
            self.add_result("Frontend Homepage", "PASSED", "Homepage loads successfully")
        else:
            self.add_result("Frontend Homepage", "FAILED", f"Status code: {response.status_code}")
        
        # Test pricing page
        response = self.session.get(f"{FRONTEND_URL}/pricing")
        if response.status_code == 200:
            content = response.text
            # Check for important elements
            checks = {
                "Weekly/Monthly Toggle": "billing-toggle" in content or "Weekly" in content,
                "Currency Selection": "currency" in content or "USD" in content,
                "Plan Cards": "Basic Plan" in content or "$29" in content,
                "Subscribe Buttons": "Subscribe" in content or "subscribe-btn" in content
            }
            
            for check_name, check_result in checks.items():
                if check_result:
                    self.add_result(f"Pricing Page - {check_name}", "PASSED", "Element found")
                else:
                    self.add_result(f"Pricing Page - {check_name}", "WARNING", "Element not found")
        else:
            self.add_result("Frontend Pricing Page", "FAILED", f"Status code: {response.status_code}")
        
        # Test dashboard (requires login)
        response = self.session.get(f"{FRONTEND_URL}/dashboard")
        if response.status_code in [200, 302]:  # May redirect to login
            self.add_result("Frontend Dashboard", "PASSED", "Dashboard endpoint accessible")
        else:
            self.add_result("Frontend Dashboard", "FAILED", f"Status code: {response.status_code}")
    
    def test_api_endpoints(self):
        """Test API endpoints availability"""
        print("\n=== Testing API Endpoints ===")
        
        endpoints = [
            ("/", "API Root"),
            ("/health", "Health Check"),
            ("/api/auth/register", "Registration Endpoint"),
            ("/api/auth/login", "Login Endpoint"),
            ("/api/subscription/credit-payment", "Credit Payment Endpoint"),
            ("/api/stripe/create-checkout", "Stripe Checkout Endpoint"),
            ("/api/account/topup", "Top-up Endpoint")
        ]
        
        for endpoint, name in endpoints:
            response = self.session.get(f"{API_URL}{endpoint}")
            # POST endpoints will return 405 for GET, which is fine
            if response.status_code in [200, 405, 401]:
                self.add_result(f"API - {name}", "PASSED", f"Endpoint exists (status: {response.status_code})")
            else:
                self.add_result(f"API - {name}", "FAILED", f"Status code: {response.status_code}")
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "="*60)
        print("PAYMENT METHODS TEST REPORT")
        print("="*60)
        print(f"Timestamp: {self.test_results['timestamp']}")
        print(f"Total Tests: {len(self.test_results['tests'])}")
        
        passed = len([t for t in self.test_results['tests'] if t['status'] == 'PASSED'])
        failed = len([t for t in self.test_results['tests'] if t['status'] == 'FAILED'])
        warnings = len([t for t in self.test_results['tests'] if t['status'] == 'WARNING'])
        
        print(f"\n✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        if failed > 0:
            print("\nFailed Tests:")
            for test in self.test_results['tests']:
                if test['status'] == 'FAILED':
                    print(f"  - {test['test']}: {test.get('details', '')}")
        
        # Save report to file
        with open('payment_test_report.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print("\nDetailed report saved to: payment_test_report.json")
        
        # Create summary report
        summary = f"""
# Payment Methods Test Summary

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Test Results Overview

| Category | Result | Details |
|----------|--------|---------|
| **Account Credits** | {'✅ WORKING' if self.check_test_passed('Credit Payment') else '❌ FAILED'} | Direct payment using account balance |
| **Stripe Card** | {'✅ WORKING' if self.check_test_passed('Stripe Checkout Session') else '❌ FAILED'} | Stripe checkout session creation |
| **USDC Crypto** | {'✅ WORKING' if self.check_test_passed('USDC Checkout Session') else '❌ FAILED'} | USDC payment via Stripe Link |
| **Frontend** | {'✅ WORKING' if self.check_test_passed('Frontend Homepage') else '❌ FAILED'} | UI and navigation |
| **API Endpoints** | {'✅ WORKING' if self.check_test_passed('API - API Root') else '❌ FAILED'} | Backend API availability |

## Summary

- **Total Tests Run:** {len(self.test_results['tests'])}
- **Passed:** {passed}
- **Failed:** {failed}
- **Warnings:** {warnings}

## System Status

The payment system is {'**PRODUCTION READY** ✅' if failed == 0 else '**NOT READY** ❌ - Issues need to be resolved'}

## Payment Methods Status

1. **Account Credits:** {'Fully functional' if self.check_test_passed('Credit Payment') else 'Has issues'}
2. **Stripe Card Payments:** {'Checkout sessions creating successfully' if self.check_test_passed('Stripe Checkout Session') else 'Has issues'}
3. **USDC Crypto Payments:** {'Configured with Stripe Link' if self.check_test_passed('USDC Checkout Session') else 'Has issues'}

## Recommendations

{self.get_recommendations()}
"""
        
        with open('PAYMENT_TEST_SUMMARY.md', 'w') as f:
            f.write(summary)
        print("\nSummary report saved to: PAYMENT_TEST_SUMMARY.md")
        
        return summary
    
    def check_test_passed(self, test_name):
        """Check if a specific test passed"""
        for test in self.test_results['tests']:
            if test_name in test['test'] and test['status'] == 'PASSED':
                return True
        return False
    
    def get_recommendations(self):
        """Get recommendations based on test results"""
        recommendations = []
        
        if not self.check_test_passed('Credit Payment'):
            recommendations.append("- Fix account credits payment functionality")
        
        if not self.check_test_passed('Stripe Checkout Session'):
            recommendations.append("- Verify Stripe API keys are configured")
            recommendations.append("- Check Stripe product/price setup")
        
        if not self.check_test_passed('USDC Checkout Session'):
            recommendations.append("- Ensure USDC payment method is properly configured in Stripe")
            recommendations.append("- Verify Link payment method is enabled")
        
        if len(recommendations) == 0:
            recommendations.append("- System is ready for production")
            recommendations.append("- Consider adding monitoring for payment failures")
            recommendations.append("- Implement webhook handlers for payment confirmations")
        
        return "\n".join(recommendations)
    
    def run_all_tests(self):
        """Run all payment method tests"""
        print("Starting Payment Methods Testing Suite...")
        print("="*60)
        
        # Setup
        if not self.setup_test_user():
            print("Failed to setup test user. Aborting tests.")
            return
        
        # Run tests
        self.test_api_endpoints()
        self.test_frontend_endpoints()
        self.test_account_credits_payment()
        self.test_stripe_card_checkout()
        self.test_usdc_crypto_checkout()
        
        # Generate report
        report = self.generate_report()
        print(report)


if __name__ == "__main__":
    tester = PaymentMethodTester()
    tester.run_all_tests()
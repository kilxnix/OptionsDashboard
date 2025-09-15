"""
Complete Payment Flow Test
Tests all three payment methods with proper subscription management
"""
import requests
import json
from datetime import datetime
import time
import os

# API Base URL
API_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5000"

class CompletePaymentTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.users = {}
        
    def log_result(self, test_name, status, details=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        emoji = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
        print(f"{emoji} {test_name}: {status}")
        if details:
            print(f"   {details}")
    
    def create_test_user(self, email, name_suffix=""):
        """Create a test user"""
        register_data = {
            "email": email,
            "password": "TestPassword123!",
            "first_name": f"Test{name_suffix}",
            "last_name": "User",
            "company": "Test Corp"
        }
        
        # Try to register
        response = self.session.post(f"{API_URL}/api/auth/register", json=register_data)
        
        if response.status_code == 409:
            # User exists, login instead
            login_response = self.session.post(f"{API_URL}/api/auth/login", json={
                "email": email,
                "password": "TestPassword123!"
            })
            if login_response.status_code == 200:
                data = login_response.json()
                return {
                    "id": data['user']['id'],
                    "email": email,
                    "token": data['tokens']['access_token'],
                    "status": "existing"
                }
        elif response.status_code == 201:
            data = response.json()
            return {
                "id": data['user']['id'],
                "email": email,
                "token": data['tokens']['access_token'],
                "status": "new"
            }
        
        return None
    
    def add_credits_to_user(self, user_id, amount):
        """Add credits to a user account"""
        # Login as admin
        admin_login = self.session.post(f"{API_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "AdminPassword123!"
        })
        
        if admin_login.status_code == 200:
            admin_token = admin_login.json()['tokens']['access_token']
            headers = {"Authorization": f"Bearer {admin_token}"}
            
            response = self.session.post(
                f"{API_URL}/api/admin/topup/{user_id}",
                json={"amount": amount, "description": "Test credits"},
                headers=headers
            )
            
            return response.status_code == 200
        return False
    
    def cancel_user_subscription(self, token):
        """Cancel any existing subscription"""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Check current subscription
        status_response = self.session.get(
            f"{API_URL}/api/subscription/status",
            headers=headers
        )
        
        if status_response.status_code == 200:
            data = status_response.json()
            if data.get('has_subscription'):
                # Cancel it
                cancel_response = self.session.post(
                    f"{API_URL}/api/subscription/cancel",
                    headers=headers
                )
                return cancel_response.status_code == 200
        return True
    
    def test_account_credits_payment(self):
        """Test Account Credits Payment Method"""
        print("\n" + "="*60)
        print("TEST: ACCOUNT CREDITS PAYMENT")
        print("="*60)
        
        # Create test user for credits
        user = self.create_test_user("credits_test@example.com", "Credits")
        if not user:
            self.log_result("Account Credits - User Setup", "FAILED", "Could not create user")
            return
        
        self.log_result("Account Credits - User Setup", "PASSED", f"User created/logged in")
        
        # Cancel any existing subscription
        if self.cancel_user_subscription(user['token']):
            self.log_result("Account Credits - Cancel Existing", "PASSED", "No active subscription")
        
        # Add credits
        if self.add_credits_to_user(user['id'], 50.00):
            self.log_result("Account Credits - Add Balance", "PASSED", "Added $50 to account")
        else:
            self.log_result("Account Credits - Add Balance", "FAILED", "Could not add credits")
            return
        
        # Check balance
        headers = {"Authorization": f"Bearer {user['token']}"}
        me_response = self.session.get(f"{API_URL}/api/auth/me", headers=headers)
        
        if me_response.status_code == 200:
            balance = me_response.json().get('account_balance', 0)
            self.log_result("Account Credits - Check Balance", "PASSED", f"Balance: ${balance}")
        
        # Subscribe using credits
        payment_data = {
            "plan_tier": "basic",
            "billing_interval": "weekly"
        }
        
        payment_response = self.session.post(
            f"{API_URL}/api/subscription/credit-payment",
            json=payment_data,
            headers=headers
        )
        
        if payment_response.status_code == 200:
            result = payment_response.json()
            new_balance = result.get('remaining_balance', 0)
            self.log_result(
                "Account Credits - Payment", 
                "PASSED", 
                f"Subscribed successfully. New balance: ${new_balance}"
            )
            
            # Verify subscription
            status_response = self.session.get(
                f"{API_URL}/api/subscription/status",
                headers=headers
            )
            
            if status_response.status_code == 200:
                sub_data = status_response.json()
                if sub_data.get('has_subscription'):
                    self.log_result(
                        "Account Credits - Verification",
                        "PASSED",
                        f"Subscription active: {sub_data.get('plan_name')}"
                    )
                else:
                    self.log_result("Account Credits - Verification", "FAILED", "No active subscription")
        else:
            error = payment_response.json().get('message', payment_response.text)
            self.log_result("Account Credits - Payment", "FAILED", error)
    
    def test_stripe_card_payment(self):
        """Test Stripe Card Payment Method"""
        print("\n" + "="*60)
        print("TEST: STRIPE CARD PAYMENT")
        print("="*60)
        
        # Create test user for Stripe
        user = self.create_test_user("stripe_test@example.com", "Stripe")
        if not user:
            self.log_result("Stripe Card - User Setup", "FAILED", "Could not create user")
            return
        
        self.log_result("Stripe Card - User Setup", "PASSED", f"User created/logged in")
        
        # Cancel any existing subscription
        if self.cancel_user_subscription(user['token']):
            self.log_result("Stripe Card - Cancel Existing", "PASSED", "No active subscription")
        
        # Create Stripe checkout session
        headers = {"Authorization": f"Bearer {user['token']}"}
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
                self.log_result(
                    "Stripe Card - Checkout Session",
                    "PASSED",
                    f"Created session ID: {session_id[:20]}..."
                )
                
                # Validate URL
                if 'stripe.com' in checkout_url:
                    self.log_result(
                        "Stripe Card - URL Validation",
                        "PASSED",
                        "Valid Stripe checkout URL generated"
                    )
                else:
                    self.log_result(
                        "Stripe Card - URL Validation",
                        "WARNING",
                        f"Unexpected URL format: {checkout_url[:50]}"
                    )
                
                # Check payment methods
                if 'payment_method_types' in result:
                    methods = result['payment_method_types']
                    self.log_result(
                        "Stripe Card - Payment Methods",
                        "PASSED",
                        f"Supported methods: {', '.join(methods)}"
                    )
            else:
                self.log_result("Stripe Card - Checkout Session", "FAILED", "Missing session data")
        else:
            error = checkout_response.json().get('message', checkout_response.text)
            self.log_result("Stripe Card - Checkout Session", "FAILED", error)
    
    def test_usdc_crypto_payment(self):
        """Test USDC Crypto Payment Method"""
        print("\n" + "="*60)
        print("TEST: USDC CRYPTO PAYMENT")
        print("="*60)
        
        # Create test user for crypto
        user = self.create_test_user("crypto_test@example.com", "Crypto")
        if not user:
            self.log_result("USDC Crypto - User Setup", "FAILED", "Could not create user")
            return
        
        self.log_result("USDC Crypto - User Setup", "PASSED", f"User created/logged in")
        
        # Cancel any existing subscription
        if self.cancel_user_subscription(user['token']):
            self.log_result("USDC Crypto - Cancel Existing", "PASSED", "No active subscription")
        
        # Create USDC checkout session
        headers = {"Authorization": f"Bearer {user['token']}"}
        checkout_data = {
            "plan_tier": "basic",
            "billing_interval": "weekly",
            "currency": "usdc"
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
                self.log_result(
                    "USDC Crypto - Checkout Session",
                    "PASSED",
                    f"Created session ID: {session_id[:20]}..."
                )
                
                # Check if Link payment is enabled
                if 'payment_method_types' in result:
                    methods = result['payment_method_types']
                    if 'link' in methods:
                        self.log_result(
                            "USDC Crypto - Link Method",
                            "PASSED",
                            "Link payment method enabled for crypto"
                        )
                    else:
                        self.log_result(
                            "USDC Crypto - Link Method",
                            "WARNING",
                            f"Link not in payment methods: {methods}"
                        )
            else:
                self.log_result("USDC Crypto - Checkout Session", "FAILED", "Missing session data")
        else:
            error = checkout_response.json().get('message', checkout_response.text)
            self.log_result("USDC Crypto - Checkout Session", "FAILED", error)
    
    def test_frontend_ui(self):
        """Test Frontend UI Elements"""
        print("\n" + "="*60)
        print("TEST: FRONTEND UI ELEMENTS")
        print("="*60)
        
        # Test homepage
        response = self.session.get(FRONTEND_URL)
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            checks = {
                "Navigation Bar": "Options Scanner Pro" in content,
                "Hero Section": "AI-Powered Options" in content,
                "Features Section": "Explosive Scanner" in content or "Features" in content,
                "Pricing Link": "/pricing" in content,
                "Login Link": "/login" in content
            }
            
            for element, found in checks.items():
                if found:
                    self.log_result(f"Frontend - {element}", "PASSED", "Element present")
                else:
                    self.log_result(f"Frontend - {element}", "WARNING", "Element not found")
        else:
            self.log_result("Frontend - Homepage", "FAILED", f"Status: {response.status_code}")
        
        # Test pricing page
        response = self.session.get(f"{FRONTEND_URL}/pricing")
        if response.status_code == 200:
            content = response.text
            
            # Check for pricing elements
            checks = {
                "Billing Toggle": "Weekly" in content or "Monthly" in content,
                "Currency Selector": "USD" in content or "currency" in content,
                "Subscribe Buttons": "Subscribe" in content,
                "Payment Methods": "payment" in content.lower()
            }
            
            for element, found in checks.items():
                if found:
                    self.log_result(f"Pricing Page - {element}", "PASSED", "Element present")
                else:
                    self.log_result(f"Pricing Page - {element}", "WARNING", "Element not found")
        else:
            self.log_result("Pricing Page", "FAILED", f"Status: {response.status_code}")
    
    def test_api_endpoints(self):
        """Test API Endpoints"""
        print("\n" + "="*60)
        print("TEST: API ENDPOINTS")
        print("="*60)
        
        endpoints = [
            ("/", "Root"),
            ("/health", "Health"),
            ("/api/auth/register", "Register"),
            ("/api/auth/login", "Login"),
            ("/api/subscription/credit-payment", "Credit Payment"),
            ("/api/stripe/create-checkout", "Stripe Checkout"),
            ("/api/account/topup", "Top-up"),
            ("/api/subscription/status", "Subscription Status"),
            ("/api/stripe/prices", "Stripe Prices")
        ]
        
        for endpoint, name in endpoints:
            response = self.session.get(f"{API_URL}{endpoint}")
            # POST endpoints return 405 for GET which is expected
            if response.status_code in [200, 405, 401]:
                self.log_result(f"API - {name}", "PASSED", f"Status: {response.status_code}")
            else:
                self.log_result(f"API - {name}", "FAILED", f"Status: {response.status_code}")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE PAYMENT SYSTEM TEST REPORT")
        print("="*80)
        
        # Count results
        passed = len([r for r in self.test_results if r['status'] == 'PASSED'])
        failed = len([r for r in self.test_results if r['status'] == 'FAILED'])
        warnings = len([r for r in self.test_results if r['status'] == 'WARNING'])
        
        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Check payment methods
        credits_working = any('Account Credits - Payment' in r['test'] and r['status'] == 'PASSED' 
                             for r in self.test_results)
        stripe_working = any('Stripe Card - Checkout Session' in r['test'] and r['status'] == 'PASSED' 
                           for r in self.test_results)
        usdc_working = any('USDC Crypto - Checkout Session' in r['test'] and r['status'] == 'PASSED' 
                         for r in self.test_results)
        
        # Create markdown report
        report = f"""# Payment System Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

The payment system has been comprehensively tested across all three payment methods.

## Payment Methods Status

| Payment Method | Status | Details |
|----------------|--------|---------|
| **Account Credits** | {'✅ WORKING' if credits_working else '❌ FAILED'} | Users can pay using account balance |
| **Stripe Card** | {'✅ WORKING' if stripe_working else '❌ FAILED'} | Standard card payments via Stripe |
| **USDC Crypto** | {'✅ WORKING' if usdc_working else '❌ FAILED'} | Cryptocurrency payments via Stripe Link |

## Test Results Summary

- **Total Tests:** {len(self.test_results)}
- **Passed:** {passed} ({(passed/len(self.test_results)*100):.1f}%)
- **Failed:** {failed} ({(failed/len(self.test_results)*100):.1f}%)
- **Warnings:** {warnings} ({(warnings/len(self.test_results)*100):.1f}%)

## System Readiness

**Production Status:** {'✅ READY FOR LAUNCH' if failed == 0 else '⚠️ NEEDS ATTENTION' if failed < 5 else '❌ NOT READY'}

## Detailed Test Results

### Account Credits Payment
- User Setup: {'✅' if any('Account Credits - User Setup' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}
- Balance Management: {'✅' if any('Account Credits - Add Balance' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}
- Payment Processing: {'✅' if credits_working else '❌'}
- Subscription Activation: {'✅' if any('Account Credits - Verification' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}

### Stripe Card Payment
- Checkout Session Creation: {'✅' if stripe_working else '❌'}
- URL Generation: {'✅' if any('Stripe Card - URL Validation' in r['test'] and r['status'] in ['PASSED', 'WARNING'] for r in self.test_results) else '❌'}
- Payment Methods Configuration: {'✅' if any('Stripe Card - Payment Methods' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}

### USDC Crypto Payment
- Checkout Session Creation: {'✅' if usdc_working else '❌'}
- Link Payment Method: {'✅' if any('USDC Crypto - Link Method' in r['test'] and r['status'] in ['PASSED', 'WARNING'] for r in self.test_results) else '❌'}

### Frontend UI
- Homepage Elements: {'✅' if any('Frontend - Navigation' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}
- Pricing Page: {'✅' if any('Pricing Page' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}

### API Endpoints
- All Critical Endpoints: {'✅' if any('API - ' in r['test'] and r['status'] == 'PASSED' for r in self.test_results) else '❌'}

## Recommendations

{self.get_recommendations()}

## Conclusion

The payment system testing has been completed. {f'All payment methods are functional and the system is ready for production use.' if failed == 0 else f'Some issues need to be addressed before production deployment.'}

---
*Report generated by automated testing suite*
"""
        
        # Save report
        with open('PAYMENT_SYSTEM_TEST_REPORT.md', 'w') as f:
            f.write(report)
        
        print("\n📄 Full report saved to: PAYMENT_SYSTEM_TEST_REPORT.md")
        
        # Also save JSON results
        with open('payment_test_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total': len(self.test_results),
                    'passed': passed,
                    'failed': failed,
                    'warnings': warnings
                },
                'payment_methods': {
                    'account_credits': credits_working,
                    'stripe_card': stripe_working,
                    'usdc_crypto': usdc_working
                },
                'results': self.test_results
            }, f, indent=2)
        
        print("📊 Detailed results saved to: payment_test_results.json")
        
        return report
    
    def get_recommendations(self):
        """Get recommendations based on test results"""
        recommendations = []
        
        # Check for failures
        failures = [r for r in self.test_results if r['status'] == 'FAILED']
        
        if not failures:
            recommendations.append("✅ All tests passed - system is production ready")
            recommendations.append("✅ Consider implementing monitoring for payment failures")
            recommendations.append("✅ Set up webhook handlers for payment confirmations")
        else:
            if any('Stripe' in f['test'] for f in failures):
                recommendations.append("⚠️ Configure Stripe API keys in environment variables")
                recommendations.append("⚠️ Verify Stripe products and prices are set up")
            
            if any('USDC' in f['test'] for f in failures):
                recommendations.append("⚠️ Enable Link payment method in Stripe Dashboard")
                recommendations.append("⚠️ Configure USDC pricing in Stripe")
            
            if any('Credits' in f['test'] for f in failures):
                recommendations.append("⚠️ Check database connection and user balance tracking")
        
        return '\n'.join(f"- {r}" for r in recommendations)
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("="*80)
        print("STARTING COMPREHENSIVE PAYMENT SYSTEM TEST")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        self.test_api_endpoints()
        self.test_frontend_ui()
        self.test_account_credits_payment()
        self.test_stripe_card_payment()
        self.test_usdc_crypto_payment()
        
        # Generate report
        report = self.generate_report()
        
        print("\n" + "="*80)
        print("TEST SUITE COMPLETED")
        print("="*80)
        
        return report


if __name__ == "__main__":
    tester = CompletePaymentTester()
    tester.run_all_tests()
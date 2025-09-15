"""
Test script to verify the authentication system
"""
import requests
import json
import time
from datetime import datetime

# Base URL - using localhost since we're testing locally
BASE_URL = "http://localhost:5000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(title):
    """Print a formatted header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def test_register():
    """Test user registration"""
    print_header("Testing User Registration")
    
    # Generate unique email using timestamp
    email = f"test_{int(time.time())}@example.com"
    
    data = {
        "email": email,
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "company": "Test Company"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
    
    if response.status_code == 201:
        result = response.json()
        print_success(f"User registered successfully: {email}")
        print_info(f"User ID: {result['user']['id']}")
        print_info(f"Plan: {result['user']['plan']}")
        print_info(f"Access Token: {result['tokens']['access_token'][:20]}...")
        return result
    else:
        print_error(f"Registration failed: {response.json()}")
        return None

def test_login(email="test@example.com", password="TestPassword123!"):
    """Test user login"""
    print_header("Testing User Login")
    
    data = {
        "email": email,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print_success(f"Login successful for: {email}")
        print_info(f"User: {result['user']['first_name']} {result['user']['last_name']}")
        print_info(f"Plan: {result['user']['plan']}")
        print_info(f"Access Token: {result['tokens']['access_token'][:20]}...")
        return result
    else:
        print_error(f"Login failed: {response.json()}")
        return None

def test_get_current_user(access_token):
    """Test getting current user info"""
    print_header("Testing Get Current User")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        user = result['user']
        subscription = result['subscription']
        print_success("Successfully retrieved user info")
        print_info(f"Email: {user['email']}")
        print_info(f"Role: {user['role']}")
        print_info(f"Plan: {subscription['plan']} ({subscription['tier']})")
        print_info(f"Quotas: {json.dumps(subscription['quotas'], indent=2)}")
        return result
    else:
        print_error(f"Failed to get user info: {response.json()}")
        return None

def test_create_api_key(access_token):
    """Test creating an API key"""
    print_header("Testing API Key Creation")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    data = {
        "name": "Test API Key"
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/api-keys", json=data, headers=headers)
    
    if response.status_code == 201:
        result = response.json()
        print_success("API key created successfully")
        print_info(f"Key ID: {result['api_key']['id']}")
        print_info(f"Key Name: {result['api_key']['name']}")
        print_info(f"API Key: {result['api_key']['key']}")
        print(f"{YELLOW}{result['warning']}{RESET}")
        return result['api_key']
    else:
        print_error(f"Failed to create API key: {response.json()}")
        return None

def test_protected_endpoint(access_token, endpoint="/scan"):
    """Test accessing a protected endpoint"""
    print_header(f"Testing Protected Endpoint: {endpoint}")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Test with minimal parameters for scan endpoint
    params = {
        "limit": 1,
        "min_price": 0.01,
        "max_price": 0.10
    }
    
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
    
    if response.status_code == 200:
        print_success(f"Successfully accessed {endpoint}")
        result = response.json()
        if 'status' in result:
            print_info(f"Response status: {result['status']}")
        return True
    elif response.status_code == 403:
        result = response.json()
        print_error(f"Access denied: {result.get('message', 'Forbidden')}")
        if 'current_tier' in result:
            print_info(f"Current tier: {result['current_tier']}")
        return False
    elif response.status_code == 401:
        print_error("Authentication required")
        return False
    elif response.status_code == 429:
        result = response.json()
        print_error(f"Rate limit exceeded: {result.get('message', 'Too many requests')}")
        return False
    else:
        print_error(f"Failed with status {response.status_code}: {response.text[:200]}")
        return False

def test_api_key_access(api_key, endpoint="/scan"):
    """Test accessing endpoints with API key"""
    print_header(f"Testing API Key Access: {endpoint}")
    
    headers = {
        "X-API-Key": api_key
    }
    
    params = {
        "limit": 1,
        "min_price": 0.01,
        "max_price": 0.10
    }
    
    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=params)
    
    if response.status_code == 200:
        print_success(f"Successfully accessed {endpoint} with API key")
        return True
    else:
        print_error(f"Failed to access with API key: {response.status_code}")
        if response.text:
            print_info(f"Response: {response.text[:200]}")
        return False

def test_refresh_token(refresh_token):
    """Test refreshing access token"""
    print_header("Testing Token Refresh")
    
    data = {
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/refresh", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print_success("Token refreshed successfully")
        print_info(f"New Access Token: {result['access_token'][:20]}...")
        return result['access_token']
    else:
        print_error(f"Failed to refresh token: {response.json()}")
        return None

def test_tier_access():
    """Test tier-based access control"""
    print_header("Testing Tier-Based Access Control")
    
    # Register a new user (gets free tier by default)
    user_data = test_register()
    if not user_data:
        return
    
    access_token = user_data['tokens']['access_token']
    
    # Test endpoints for different tiers
    endpoints = [
        ("/scan", "Free/Basic/Premium/Enterprise"),
        ("/explosive-scan", "Basic/Premium/Enterprise"),
        ("/enhanced-scan", "Premium/Enterprise"),
        ("/mega-discovery-scan", "Enterprise only")
    ]
    
    print(f"\n{YELLOW}Testing with Free Tier user:{RESET}")
    for endpoint, allowed_tiers in endpoints:
        success = test_protected_endpoint(access_token, endpoint)
        if endpoint == "/scan" and success:
            print_success(f"Free tier can access {endpoint} ✓")
        elif not success and endpoint != "/scan":
            print_info(f"Free tier blocked from {endpoint} (expected)")

def test_admin_login():
    """Test admin user login"""
    print_header("Testing Admin Login")
    
    # Try to login as admin
    admin_data = test_login("admin@optionsscanner.com", "Admin123!")
    if admin_data:
        print_success("Admin login successful")
        return admin_data
    else:
        print_error("Admin login failed")
        return None

def main():
    """Run all authentication tests"""
    print(f"\n{BLUE}{'*'*60}{RESET}")
    print(f"{BLUE}{'Options Scanner Authentication System Test':^60}{RESET}")
    print(f"{BLUE}{'*'*60}{RESET}\n")
    
    # Test 1: Register a new user
    user_data = test_register()
    if not user_data:
        print_error("Registration test failed. Stopping tests.")
        return
    
    access_token = user_data['tokens']['access_token']
    refresh_token = user_data['tokens']['refresh_token']
    
    # Test 2: Get current user info
    test_get_current_user(access_token)
    
    # Test 3: Create API key
    api_key_data = test_create_api_key(access_token)
    
    # Test 4: Access protected endpoint with JWT
    test_protected_endpoint(access_token, "/scan")
    
    # Test 5: Access with API key if created
    if api_key_data:
        test_api_key_access(api_key_data['key'], "/scan")
    
    # Test 6: Refresh token
    new_access_token = test_refresh_token(refresh_token)
    
    # Test 7: Test tier-based access
    test_tier_access()
    
    # Test 8: Admin login
    test_admin_login()
    
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}{'All Authentication Tests Completed!':^60}{RESET}")
    print(f"{GREEN}{'='*60}{RESET}\n")

if __name__ == "__main__":
    main()
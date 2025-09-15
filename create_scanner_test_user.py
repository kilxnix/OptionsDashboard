#!/usr/bin/env python3
"""Create a test user for testing the scanner interface"""

import requests
import json

# Register a test user
register_url = "http://localhost:5001/api/auth/register"
test_user = {
    "email": "scanner_test@example.com",
    "password": "Test123!@#",
    "first_name": "Scanner",
    "last_name": "Test"
}

print("Creating test user for scanner testing...")
print(f"Email: {test_user['email']}")

try:
    # Try to register the user
    response = requests.post(register_url, json=test_user)
    data = response.json()
    
    if response.status_code == 201:
        print("✅ User created successfully!")
        print(f"Access token: {data['tokens']['access_token'][:20]}...")
        
        # Save credentials for easy testing
        with open('test_credentials.json', 'w') as f:
            json.dump({
                'email': test_user['email'],
                'password': test_user['password'],
                'access_token': data['tokens']['access_token']
            }, f, indent=2)
        print("📁 Credentials saved to test_credentials.json")
        
    elif response.status_code == 409:
        print("User already exists, trying to login...")
        
        # Try to login
        login_url = "http://localhost:5001/api/auth/login"
        login_response = requests.post(login_url, json={
            "email": test_user['email'],
            "password": test_user['password']
        })
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            print("✅ Login successful!")
            print(f"Access token: {login_data['tokens']['access_token'][:20]}...")
            
            # Save credentials
            with open('test_credentials.json', 'w') as f:
                json.dump({
                    'email': test_user['email'],
                    'password': test_user['password'],
                    'access_token': login_data['tokens']['access_token']
                }, f, indent=2)
            print("📁 Credentials saved to test_credentials.json")
        else:
            print(f"❌ Login failed: {login_response.json()}")
    else:
        print(f"❌ Registration failed: {data}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n🌐 You can now test the scanner interface at http://localhost:5000")
print(f"   Login with: {test_user['email']} / {test_user['password']}")
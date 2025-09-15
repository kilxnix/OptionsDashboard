#!/usr/bin/env python3
"""Test the complete login flow to verify everything is working"""

import requests
import json

def test_login_flow():
    """Test the complete login flow"""
    
    # Test backend health
    print("1. Testing backend health...")
    response = requests.get("http://localhost:5001/health")
    assert response.status_code == 200, f"Backend health check failed: {response.status_code}"
    print("   ✅ Backend is healthy on port 5001")
    
    # Test frontend
    print("\n2. Testing frontend...")
    response = requests.get("http://localhost:5000/")
    assert response.status_code == 200, f"Frontend check failed: {response.status_code}"
    print("   ✅ Frontend is running on port 5000")
    
    # Test login with valid credentials
    print("\n3. Testing login...")
    login_data = {
        "email": "test@example.com",
        "password": "Test123!@#"
    }
    response = requests.post(
        "http://localhost:5001/api/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Login failed: {response.status_code}"
    
    data = response.json()
    assert data["status"] == "success", f"Login status not success: {data}"
    assert "access_token" in data["tokens"], "No access token returned"
    assert "refresh_token" in data["tokens"], "No refresh token returned"
    
    print("   ✅ Login successful!")
    print(f"   - User: {data['user']['email']}")
    print(f"   - Plan: {data['user']['plan']}")
    print(f"   - Role: {data['user']['role']}")
    print(f"   - Access token received: {data['tokens']['access_token'][:50]}...")
    
    # Test authenticated endpoint
    print("\n4. Testing authenticated API call...")
    headers = {
        "Authorization": f"Bearer {data['tokens']['access_token']}"
    }
    response = requests.get("http://localhost:5001/api/auth/me", headers=headers)
    assert response.status_code == 200, f"Auth check failed: {response.status_code}"
    
    user_data = response.json()
    print("   ✅ Authenticated API call successful!")
    print(f"   - User ID: {user_data['user']['id']}")
    print(f"   - Subscription status: {user_data['subscription']['status']}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED! Login system is fully functional!")
    print("="*60)
    print("\nSummary:")
    print("- Backend server is running on port 5001 ✅")
    print("- Frontend server is running on port 5000 ✅")
    print("- Flask secret key issue fixed (no crash) ✅")
    print("- Login authentication working ✅")
    print("- JWT tokens generated successfully ✅")
    print("- Authenticated API calls working ✅")

if __name__ == "__main__":
    try:
        test_login_flow()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
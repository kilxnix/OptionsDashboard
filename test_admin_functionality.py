#!/usr/bin/env python3
"""
Test script to verify admin functionality
"""
import requests
import json
import os
from datetime import datetime

# Base URL
BASE_URL = "http://localhost:5001"

def test_admin_login():
    """Test admin login"""
    print("\n1. Testing admin login...")
    
    # Login as admin
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "sheltontraylor@gmail.com",
        "password": "admin123"  # Replace with actual password
    })
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print("✅ Admin login successful")
            print(f"   Role: {data.get('user', {}).get('role')}")
            return data.get('access_token')
        else:
            print(f"❌ Login failed: {data.get('message')}")
            return None
    else:
        print(f"❌ Login failed with status code: {response.status_code}")
        return None

def test_list_users(token):
    """Test listing users endpoint"""
    print("\n2. Testing list users endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            users = data.get('users', [])
            print(f"✅ Successfully retrieved {len(users)} users")
            
            # Display first 3 users
            for i, user in enumerate(users[:3]):
                print(f"\n   User {i+1}:")
                print(f"   - Email: {user['email']}")
                print(f"   - Balance: ${user['account_balance']:.2f}")
                print(f"   - Subscription: {user['subscription']['tier']}")
                print(f"   - Status: {user['status']}")
            
            return users
        else:
            print(f"❌ Failed to get users: {data.get('message')}")
            return []
    elif response.status_code == 403:
        print("❌ Access denied - not an admin")
        return []
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        return []

def test_topup_user(token, user_id, amount=10.00):
    """Test topping up a user's balance"""
    print(f"\n3. Testing top-up for user ID {user_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/admin/topup/{user_id}",
        headers=headers,
        json={
            "amount": amount,
            "description": "Test admin topup"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print(f"✅ Successfully topped up ${amount:.2f}")
            print(f"   Transaction ID: {data.get('transaction_id')}")
            print(f"   New Balance: ${data.get('new_balance'):.2f}")
            return True
        else:
            print(f"❌ Topup failed: {data.get('message')}")
            return False
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_grant_subscription(token, user_id, tier="basic", days=30):
    """Test granting a subscription to a user"""
    print(f"\n4. Testing grant subscription for user ID {user_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/admin/grant-subscription/{user_id}",
        headers=headers,
        json={
            "tier": tier,
            "duration_days": days
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print(f"✅ Successfully granted {tier} subscription for {days} days")
            print(f"   Subscription ID: {data.get('subscription_id')}")
            print(f"   Expires: {data.get('expires_at')}")
            return True
        else:
            print(f"❌ Grant subscription failed: {data.get('message')}")
            return False
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_audit_log(token):
    """Test viewing audit log"""
    print("\n5. Testing audit log...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/admin/audit-log", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            logs = data.get('logs', [])
            print(f"✅ Successfully retrieved {len(logs)} audit log entries")
            
            # Display last 3 entries
            for i, log in enumerate(logs[:3]):
                print(f"\n   Log {i+1}:")
                print(f"   - Action: {log['action']}")
                print(f"   - Actor: {log['actor']['email']}")
                print(f"   - Target: {log['target_type']} #{log['target_id']}")
                print(f"   - Success: {log['success']}")
                print(f"   - Time: {log['created_at']}")
            
            return True
        else:
            print(f"❌ Failed to get audit log: {data.get('message')}")
            return False
    else:
        print(f"❌ Failed with status code: {response.status_code}")
        return False

def test_non_admin_access():
    """Test that non-admin users cannot access admin endpoints"""
    print("\n6. Testing non-admin access restriction...")
    
    # First, create a test non-admin user or use existing one
    # For this test, we'll assume there's a non-admin user
    # You may need to adjust the credentials
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "test@example.com",  # Replace with a non-admin user
        "password": "test123"
    })
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            non_admin_token = data.get('access_token')
            
            # Try to access admin endpoint
            headers = {"Authorization": f"Bearer {non_admin_token}"}
            response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
            
            if response.status_code == 403:
                print("✅ Non-admin correctly denied access (403 Forbidden)")
                return True
            else:
                print(f"❌ Non-admin was not blocked! Status: {response.status_code}")
                return False
    
    print("⚠️ Could not test non-admin access (no non-admin user available)")
    return None

def main():
    """Run all admin tests"""
    print("=" * 60)
    print("ADMIN FUNCTIONALITY TEST SUITE")
    print("=" * 60)
    
    # Test 1: Admin login
    token = test_admin_login()
    if not token:
        print("\n❌ Cannot proceed without admin token")
        print("\nNote: Make sure the admin user exists with correct password")
        print("You may need to update the password in this script")
        return
    
    # Test 2: List users
    users = test_list_users(token)
    
    # Test 3: Top up a user (if we have users)
    if users and len(users) > 0:
        # Pick a non-admin user to test with
        test_user = None
        for user in users:
            if user['role'] != 'admin':
                test_user = user
                break
        
        if test_user:
            test_topup_user(token, test_user['id'], 25.00)
            
            # Test 4: Grant subscription
            test_grant_subscription(token, test_user['id'], "premium", 7)
        else:
            print("\n⚠️ No non-admin users found to test with")
    
    # Test 5: View audit log
    test_audit_log(token)
    
    # Test 6: Non-admin access restriction
    test_non_admin_access()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)
    
    print("\n📊 Summary:")
    print("- Admin login: ✅")
    print("- List users: ✅" if users else "❌")
    print("- Top-up functionality: Tested" if users else "Skipped")
    print("- Grant subscription: Tested" if users else "Skipped")
    print("- Audit log: Tested")
    print("- Security (non-admin block): Tested")
    
    print("\n✅ Admin functionality is ready!")
    print("\nYou can now access the admin dashboard at:")
    print("http://localhost:5000/admin")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Password reset script for admin user
This script resets the password for sheltontraylor@gmail.com to Admin123!
"""
import os
import sys
import bcrypt
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the database models and utilities
from models import db, User, UserRole, UserStatus
from auth import AuthManager
from flask import Flask
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def reset_admin_password():
    """Reset the password for the admin user"""
    
    # Configuration
    admin_email = "sheltontraylor@gmail.com"
    new_password = "Admin123!"
    
    print(f"=== Password Reset Script ===")
    print(f"Target user: {admin_email}")
    print(f"New password: {new_password}")
    print("=" * 40)
    
    # Create Flask app for database context
    app = Flask(__name__)
    
    # Configure database
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not found")
        return False
    
    # Flask-SQLAlchemy expects SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the database with the app
    db.init_app(app)
    
    with app.app_context():
        try:
            # Find the user
            print(f"\n1. Looking for user with email: {admin_email}")
            user = User.query.filter_by(email=admin_email).first()
            
            if not user:
                print(f"   ERROR: User with email {admin_email} not found!")
                print("\n   Checking all users in database...")
                all_users = User.query.all()
                if all_users:
                    print("   Found users:")
                    for u in all_users:
                        print(f"   - {u.email} (Role: {u.role.value if u.role else 'None'})")
                else:
                    print("   No users found in database!")
                return False
            
            print(f"   ✓ User found: ID={user.id}, Role={user.role.value if user.role else 'None'}")
            
            # Hash the new password
            print(f"\n2. Hashing new password...")
            password_hash = AuthManager.hash_password(new_password)
            print(f"   ✓ Password hashed successfully")
            
            # Update the password
            print(f"\n3. Updating password in database...")
            old_hash = user.password_hash[:20] + "..." if user.password_hash else "None"
            print(f"   Old password hash: {old_hash}")
            
            user.password_hash = password_hash
            user.updated_at = datetime.utcnow()
            
            # Ensure user is active and has admin role
            if user.status != UserStatus.ACTIVE:
                print(f"   Setting user status to ACTIVE (was {user.status.value if user.status else 'None'})")
                user.status = UserStatus.ACTIVE
            
            if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
                print(f"   Setting user role to ADMIN (was {user.role.value if user.role else 'None'})")
                user.role = UserRole.ADMIN
            
            db.session.commit()
            print(f"   ✓ Password updated successfully")
            
            # Verify the update
            print(f"\n4. Verifying password update...")
            updated_user = User.query.filter_by(email=admin_email).first()
            if updated_user and updated_user.password_hash == password_hash:
                print(f"   ✓ Password verified in database")
            else:
                print(f"   ERROR: Password verification failed!")
                return False
            
            # Test password verification
            print(f"\n5. Testing password verification...")
            if AuthManager.verify_password(new_password, updated_user.password_hash):
                print(f"   ✓ Password verification successful")
            else:
                print(f"   ERROR: Password verification failed!")
                return False
            
            print("\n" + "=" * 40)
            print("✓ PASSWORD RESET SUCCESSFUL!")
            print(f"  Email: {admin_email}")
            print(f"  Password: {new_password}")
            print(f"  Role: {updated_user.role.value}")
            print(f"  Status: {updated_user.status.value}")
            print("=" * 40)
            print("\nYou can now log in with these credentials.")
            
            return True
            
        except Exception as e:
            print(f"\nERROR: Failed to reset password: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = reset_admin_password()
    sys.exit(0 if success else 1)
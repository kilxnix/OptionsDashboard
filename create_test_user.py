#!/usr/bin/env python3
"""Create a test user for verifying login functionality"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from models import db, User, Plan, Subscription, PlanTier, UserRole, UserStatus, SubscriptionStatus
from auth import AuthManager
from flask import Flask

# Initialize Flask app with minimal config
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

with app.app_context():
    # Check if test user already exists
    test_email = "test@example.com"
    existing_user = User.query.filter_by(email=test_email).first()
    
    if existing_user:
        print(f"Test user {test_email} already exists")
        # Update password to ensure we know it
        existing_user.password_hash = AuthManager.hash_password("Test123!@#")
        db.session.commit()
        print("Password updated to: Test123!@#")
    else:
        # Create new test user
        test_user = User(
            email=test_email,
            password_hash=AuthManager.hash_password("Test123!@#"),
            first_name="Test",
            last_name="User",
            company="Test Company",
            status=UserStatus.ACTIVE,
            role=UserRole.USER
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        # Create free tier subscription
        free_plan = Plan.query.filter_by(tier=PlanTier.FREE).first()
        if not free_plan:
            # Create default free plan if it doesn't exist
            free_plan = Plan(
                code='free',
                name='Free Tier',
                tier=PlanTier.FREE,
                price_monthly=0,
                quotas_json={'scans_per_day': 5, 'api_calls_per_minute': 10},
                allowed_endpoints_json=['/scan'],
                features_json={'basic_scanning': True}
            )
            db.session.add(free_plan)
            db.session.commit()
        
        subscription = Subscription(
            user_id=test_user.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)
        db.session.commit()
        
        print(f"✅ Test user created successfully!")
        print(f"   Email: {test_email}")
        print(f"   Password: Test123!@#")
        print(f"   Plan: {free_plan.name}")
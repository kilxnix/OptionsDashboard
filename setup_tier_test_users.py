#!/usr/bin/env python3
"""
Setup test users for tier enforcement testing
"""

import os
import sys
from datetime import datetime, timedelta

# Set up database connection
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/options_scanner')

from models import db, User, Plan, Subscription, PlanTier, UserRole, UserStatus, SubscriptionStatus
from auth import AuthManager
from flask import Flask

# Create Flask app context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def setup_test_users():
    """Create test users with different subscription tiers"""
    
    with app.app_context():
        print("Setting up test users...")
        
        # Ensure plans exist
        plans = {
            'free': Plan.query.filter_by(tier=PlanTier.FREE).first(),
            'basic': Plan.query.filter_by(tier=PlanTier.BASIC).first(),
            'premium': Plan.query.filter_by(tier=PlanTier.PREMIUM).first()
        }
        
        # Create plans if they don't exist
        if not plans['free']:
            plans['free'] = Plan(
                code='free',
                name='Free Tier',
                tier=PlanTier.FREE,
                price_monthly=0,
                quotas_json={'scans_per_day': 5, 'api_calls_per_minute': 10},
                allowed_endpoints_json=['/scan'],
                features_json={'basic_scanning': True}
            )
            db.session.add(plans['free'])
        
        if not plans['basic']:
            plans['basic'] = Plan(
                code='basic',
                name='Basic Tier',
                tier=PlanTier.BASIC,
                price_monthly=29,
                quotas_json={'scans_per_day': 50, 'api_calls_per_minute': 30},
                allowed_endpoints_json=['/scan', '/explosive-scan', '/explosive-earnings-combo'],
                features_json={'explosive_scanning': True, 'technical_analysis': True}
            )
            db.session.add(plans['basic'])
        
        if not plans['premium']:
            plans['premium'] = Plan(
                code='premium',
                name='Premium Tier',
                tier=PlanTier.PREMIUM,
                price_monthly=99,
                quotas_json={'scans_per_day': 500, 'api_calls_per_minute': 100},
                allowed_endpoints_json=['*'],
                features_json={'all_features': True}
            )
            db.session.add(plans['premium'])
        
        db.session.commit()
        
        # Test user configurations
        test_users = [
            {
                'email': 'free@test.com',
                'password': 'FreeUser123!',
                'first_name': 'Free',
                'last_name': 'User',
                'role': UserRole.USER,
                'plan': plans['free']
            },
            {
                'email': 'basic@test.com',
                'password': 'BasicUser123!',
                'first_name': 'Basic',
                'last_name': 'User',
                'role': UserRole.USER,
                'plan': plans['basic']
            },
            {
                'email': 'premium@test.com',
                'password': 'PremiumUser123!',
                'first_name': 'Premium',
                'last_name': 'User',
                'role': UserRole.USER,
                'plan': plans['premium']
            },
            {
                'email': 'admin@test.com',
                'password': 'AdminUser123!',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': UserRole.ADMIN,
                'plan': plans['free']  # Admin gets free plan but should have premium access
            }
        ]
        
        for user_config in test_users:
            # Check if user exists
            user = User.query.filter_by(email=user_config['email']).first()
            
            if user:
                # Update existing user
                print(f"Updating user: {user_config['email']}")
                user.password_hash = AuthManager.hash_password(user_config['password'])
                user.role = user_config['role']
                user.status = UserStatus.ACTIVE
                
                # Delete old subscriptions
                Subscription.query.filter_by(user_id=user.id).delete()
            else:
                # Create new user
                print(f"Creating user: {user_config['email']}")
                user = User(
                    email=user_config['email'],
                    password_hash=AuthManager.hash_password(user_config['password']),
                    first_name=user_config['first_name'],
                    last_name=user_config['last_name'],
                    role=user_config['role'],
                    status=UserStatus.ACTIVE
                )
                db.session.add(user)
                db.session.flush()
            
            # Create subscription
            subscription = Subscription(
                user_id=user.id,
                plan_id=user_config['plan'].id,
                status=SubscriptionStatus.ACTIVE,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(subscription)
            
            print(f"  ✓ {user_config['email']} - {user_config['role'].value} with {user_config['plan'].tier.value} plan")
        
        db.session.commit()
        print("\n✅ All test users created successfully!")
        
        # Print login instructions
        print("\nTest User Credentials:")
        print("-" * 40)
        for user_config in test_users:
            print(f"Email: {user_config['email']}")
            print(f"Password: {user_config['password']}")
            print(f"Role: {user_config['role'].value}")
            print(f"Plan: {user_config['plan'].tier.value}")
            print("-" * 40)

if __name__ == "__main__":
    setup_test_users()
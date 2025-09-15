#!/usr/bin/env python3
"""
Create test users with different subscription tiers
"""
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL')

from models import db, User, Plan, Subscription, PlanTier, UserRole, UserStatus, SubscriptionStatus
from auth import AuthManager
from datetime import datetime, timedelta
from flask import Flask

# Initialize Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def create_test_users():
    """Create test users with different tier subscriptions"""
    
    with app.app_context():
        # Create plans if they don't exist
        plans = {
            PlanTier.FREE: {
                'code': 'free',
                'name': 'Free Tier',
                'price_monthly': 0,
                'price_weekly': 0,
                'quotas': {'scans_per_day': 5, 'api_calls_per_minute': 10},
                'allowed_endpoints': ['/scan'],
                'features': {'basic_scanning': True}
            },
            PlanTier.BASIC: {
                'code': 'basic',
                'name': 'Basic',
                'price_monthly': 29,
                'price_weekly': 9,
                'quotas': {'scans_per_day': 50, 'api_calls_per_minute': 30},
                'allowed_endpoints': ['/scan', '/explosive-scan', '/plans'],
                'features': {'explosive_scanning': True, 'technical_analysis': True}
            },
            PlanTier.PREMIUM: {
                'code': 'premium',
                'name': 'Premium',
                'price_monthly': 99,
                'price_weekly': 29,
                'quotas': {'scans_per_day': 500, 'api_calls_per_minute': 100},
                'allowed_endpoints': ['*'],
                'features': {'all_scanners': True, 'priority_support': True, 'advanced_features': True}
            }
        }
        
        created_plans = {}
        for tier, plan_data in plans.items():
            plan = Plan.query.filter_by(tier=tier).first()
            if not plan:
                plan = Plan(
                    code=plan_data['code'],
                    name=plan_data['name'],
                    tier=tier,
                    price_monthly=plan_data['price_monthly'],
                    price_weekly=plan_data['price_weekly'],
                    quotas_json=plan_data['quotas'],
                    allowed_endpoints_json=plan_data['allowed_endpoints'],
                    features_json=plan_data['features']
                )
                db.session.add(plan)
                print(f"✅ Created {plan_data['name']} plan")
            created_plans[tier] = plan
        
        db.session.commit()
        
        # Create test users
        test_users = [
            {
                'email': 'premium@test.com',
                'password': 'Premium123!',
                'first_name': 'Premium',
                'last_name': 'User',
                'tier': PlanTier.PREMIUM,
                'role': UserRole.USER
            },
            {
                'email': 'basic@test.com',
                'password': 'Basic123!',
                'first_name': 'Basic',
                'last_name': 'User',
                'tier': PlanTier.BASIC,
                'role': UserRole.USER
            },
            {
                'email': 'free@test.com',
                'password': 'Free123!',
                'first_name': 'Free',
                'last_name': 'User',
                'tier': PlanTier.FREE,
                'role': UserRole.USER
            },
            {
                'email': 'admin@test.com',
                'password': 'Admin123!',
                'first_name': 'Admin',
                'last_name': 'User',
                'tier': PlanTier.PREMIUM,
                'role': UserRole.ADMIN
            }
        ]
        
        for user_data in test_users:
            # Check if user already exists
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if existing_user:
                print(f"⚠️  User {user_data['email']} already exists")
                # Update their subscription if needed
                sub = Subscription.query.filter_by(user_id=existing_user.id, status=SubscriptionStatus.ACTIVE).first()
                if sub and sub.plan.tier != user_data['tier']:
                    # Update subscription to correct tier
                    sub.plan = created_plans[user_data['tier']]
                    db.session.commit()
                    print(f"   Updated subscription to {user_data['tier'].value}")
                continue
            
            # Create new user
            user = User(
                email=user_data['email'],
                password_hash=AuthManager.hash_password(user_data['password']),
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                status=UserStatus.ACTIVE,
                account_balance=100.00 if user_data['tier'] != PlanTier.FREE else 0
            )
            db.session.add(user)
            db.session.flush()
            
            # Create subscription
            subscription = Subscription(
                user_id=user.id,
                plan_id=created_plans[user_data['tier']].id,
                status=SubscriptionStatus.ACTIVE,
                billing_period='monthly',
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(subscription)
            
            print(f"✅ Created {user_data['email']} with {user_data['tier'].value} tier")
        
        db.session.commit()
        print("\n✅ All test users created successfully!")
        print("\nTest Credentials:")
        print("-" * 50)
        for user_data in test_users:
            print(f"📧 Email: {user_data['email']}")
            print(f"🔑 Password: {user_data['password']}")
            print(f"💎 Tier: {user_data['tier'].value}")
            print(f"👤 Role: {user_data['role'].value}")
            print("-" * 50)

if __name__ == "__main__":
    create_test_users()
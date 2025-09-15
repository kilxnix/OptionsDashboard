"""
Script to seed the database with initial subscription plan data
"""
from datetime import datetime
from models import db, Plan, PlanTier, User, UserRole, UserStatus, ApiKey
from flask import Flask
import os
import json

def create_app():
    """Create Flask app for database seeding"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

def seed_plans():
    """Seed the database with initial subscription plans"""
    plans_data = [
        {
            "code": "free",
            "name": "Free Tier",
            "tier": PlanTier.FREE,
            "price_monthly": 0.0,
            "price_yearly": 0.0,
            "quotas_json": {
                "scans_per_day": 10,
                "api_calls_per_minute": 5,
                "symbols_per_scan": 5,
                "max_days_to_expiry": 7
            },
            "allowed_endpoints_json": [
                "/scan",
                "/plans",
                "/performance/report"
            ],
            "features_json": {
                "priority_support": False,
                "custom_alerts": False,
                "webhook_notifications": False,
                "advanced_filters": False,
                "api_access": False,
                "bulk_export": False
            }
        },
        {
            "code": "basic",
            "name": "Basic Tier",
            "tier": PlanTier.BASIC,
            "price_monthly": 29.0,
            "price_yearly": 299.0,  # ~14% discount
            "quotas_json": {
                "scans_per_day": 100,
                "api_calls_per_minute": 30,
                "symbols_per_scan": 50,
                "max_days_to_expiry": 30
            },
            "allowed_endpoints_json": [
                "/scan",
                "/explosive-scan",
                "/plans",
                "/plans/all",
                "/performance/report",
                "/performance/analyze",
                "/screener/symbols",
                "/screener/all"
            ],
            "features_json": {
                "priority_support": False,
                "custom_alerts": True,
                "webhook_notifications": False,
                "advanced_filters": True,
                "api_access": True,
                "bulk_export": False
            }
        },
        {
            "code": "premium",
            "name": "Premium Tier",
            "tier": PlanTier.PREMIUM,
            "price_monthly": 99.0,
            "price_yearly": 999.0,  # ~16% discount
            "quotas_json": {
                "scans_per_day": 500,
                "api_calls_per_minute": 60,
                "symbols_per_scan": 200,
                "max_days_to_expiry": 90
            },
            "allowed_endpoints_json": [
                "/scan",
                "/explosive-scan",
                "/explosive-earnings-combo",
                "/jpm-explosion-hunter",
                "/gamma-squeeze-detector",
                "/plans",
                "/plans/all",
                "/performance/report",
                "/performance/analyze",
                "/performance/update",
                "/screener/symbols",
                "/screener/all",
                "/screener/fallback",
                "/screener/update-db",
                "/backtest",
                "/market-conditions"
            ],
            "features_json": {
                "priority_support": True,
                "custom_alerts": True,
                "webhook_notifications": True,
                "advanced_filters": True,
                "api_access": True,
                "bulk_export": True,
                "real_time_data": True,
                "backtesting": True
            }
        },
        {
            "code": "enterprise",
            "name": "Enterprise Tier",
            "tier": PlanTier.ENTERPRISE,
            "price_monthly": 299.0,
            "price_yearly": 2999.0,  # ~16% discount
            "quotas_json": {
                "scans_per_day": -1,  # -1 means unlimited
                "api_calls_per_minute": 120,
                "symbols_per_scan": -1,  # unlimited
                "max_days_to_expiry": 365
            },
            "allowed_endpoints_json": ["*"],  # All endpoints
            "features_json": {
                "priority_support": True,
                "custom_alerts": True,
                "webhook_notifications": True,
                "advanced_filters": True,
                "api_access": True,
                "bulk_export": True,
                "real_time_data": True,
                "backtesting": True,
                "dedicated_support": True,
                "custom_integration": True,
                "white_label": True,
                "sla_guarantee": True
            }
        }
    ]
    
    # Check if plans already exist
    existing_plans = Plan.query.filter(Plan.code.in_([p['code'] for p in plans_data])).all()
    existing_codes = {plan.code for plan in existing_plans}
    
    new_plans = []
    updated_plans = []
    
    for plan_data in plans_data:
        if plan_data['code'] in existing_codes:
            # Update existing plan
            plan = Plan.query.filter_by(code=plan_data['code']).first()
            for key, value in plan_data.items():
                setattr(plan, key, value)
            updated_plans.append(plan.code)
        else:
            # Create new plan
            plan = Plan(**plan_data)
            db.session.add(plan)
            new_plans.append(plan.code)
    
    db.session.commit()
    
    return {
        "new_plans": new_plans,
        "updated_plans": updated_plans,
        "total_plans": len(plans_data)
    }

def create_demo_user():
    """Create a demo user for testing"""
    demo_email = "demo@example.com"
    
    # Check if demo user already exists
    existing_user = User.query.filter_by(email=demo_email).first()
    if existing_user:
        return {"message": "Demo user already exists", "user_id": existing_user.id}
    
    # Create demo user
    demo_user = User(
        email=demo_email,
        password_hash="pbkdf2:sha256:600000$demo$1234567890abcdef",  # Not a real password
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        first_name="Demo",
        last_name="User",
        company="Demo Company"
    )
    db.session.add(demo_user)
    db.session.commit()
    
    # Create an API key for the demo user
    api_key_value = ApiKey.generate_key()
    api_key = ApiKey(
        user_id=demo_user.id,
        key_hash=ApiKey.hash_key(api_key_value),
        name="Demo API Key",
        active=True
    )
    db.session.add(api_key)
    db.session.commit()
    
    return {
        "message": "Demo user created",
        "user_id": demo_user.id,
        "api_key": api_key_value  # Only shown once!
    }

def main():
    """Main function to seed the database"""
    app = create_app()
    
    with app.app_context():
        print("Starting database seeding...")
        
        # Seed plans
        print("\n1. Seeding subscription plans...")
        plan_result = seed_plans()
        print(f"   - New plans created: {plan_result['new_plans']}")
        print(f"   - Plans updated: {plan_result['updated_plans']}")
        print(f"   - Total plans: {plan_result['total_plans']}")
        
        # Create demo user
        print("\n2. Creating demo user...")
        user_result = create_demo_user()
        print(f"   - {user_result['message']}")
        if 'api_key' in user_result:
            print(f"   - Demo API Key (save this!): {user_result['api_key']}")
        
        # Display all plans
        print("\n3. Current subscription plans in database:")
        plans = Plan.query.all()
        for plan in plans:
            print(f"\n   {plan.name} ({plan.code}):")
            print(f"   - Tier: {plan.tier.value}")
            print(f"   - Monthly Price: ${plan.price_monthly}")
            print(f"   - Yearly Price: ${plan.price_yearly}")
            print(f"   - Daily Scan Limit: {plan.quotas_json.get('scans_per_day', 'N/A')}")
            print(f"   - API Calls/Minute: {plan.quotas_json.get('api_calls_per_minute', 'N/A')}")
            print(f"   - Active: {plan.active}")
        
        print("\n✅ Database seeding completed successfully!")

if __name__ == "__main__":
    main()
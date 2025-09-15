"""
Seed script to populate the database with subscription plans
"""
import os
import sys
from datetime import datetime
from models import db, Plan, PlanTier, User, UserRole, UserStatus
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

def seed_plans():
    """Create default subscription plans"""
    with app.app_context():
        # Check if plans already exist
        existing_plans = Plan.query.all()
        if existing_plans:
            print(f"Plans already exist: {len(existing_plans)} plans found")
            return
        
        # Free Tier
        free_plan = Plan(
            code='free',
            name='Free Tier',
            tier=PlanTier.FREE,
            price_monthly=0,
            price_yearly=0,
            quotas_json={
                'scans_per_day': 5,
                'api_calls_per_minute': 10,
                'max_api_keys': 1,
                'symbols_per_scan': 10
            },
            allowed_endpoints_json=[
                '/scan',
                '/scan/parameters',
                '/plans'
            ],
            features_json={
                'basic_scanning': True,
                'api_access': False,
                'custom_alerts': False,
                'priority_support': False,
                'advanced_analytics': False
            },
            active=True
        )
        
        # Basic Tier
        basic_plan = Plan(
            code='basic',
            name='Basic Plan',
            tier=PlanTier.BASIC,
            price_monthly=29.99,
            price_yearly=299.99,
            quotas_json={
                'scans_per_day': 50,
                'api_calls_per_minute': 30,
                'max_api_keys': 3,
                'symbols_per_scan': 50
            },
            allowed_endpoints_json=[
                '/scan',
                '/scan/parameters',
                '/plans',
                '/explosive-scan',
                '/latest-results'
            ],
            features_json={
                'basic_scanning': True,
                'api_access': True,
                'custom_alerts': False,
                'priority_support': False,
                'advanced_analytics': False,
                'explosive_scan': True
            },
            active=True
        )
        
        # Premium Tier
        premium_plan = Plan(
            code='premium',
            name='Premium Plan',
            tier=PlanTier.PREMIUM,
            price_monthly=99.99,
            price_yearly=999.99,
            quotas_json={
                'scans_per_day': 500,
                'api_calls_per_minute': 100,
                'max_api_keys': 10,
                'symbols_per_scan': 200
            },
            allowed_endpoints_json=[
                '/scan',
                '/scan/parameters',
                '/plans',
                '/explosive-scan',
                '/enhanced-scan',
                '/enhanced-scan/progress',
                '/enhanced-scan/resume',
                '/pre-earnings-scan',
                '/api/jpm-explosion-hunter',
                '/explosive-techvol-scan',
                '/quantitative-squeeze-scan',
                '/gamma-squeeze-scan',
                '/latest-results'
            ],
            features_json={
                'basic_scanning': True,
                'api_access': True,
                'custom_alerts': True,
                'priority_support': True,
                'advanced_analytics': True,
                'explosive_scan': True,
                'enhanced_scan': True,
                'pre_earnings_scan': True,
                'technical_analysis': True,
                'volatility_analysis': True,
                'gamma_squeeze_detection': True
            },
            active=True
        )
        
        # Enterprise Tier
        enterprise_plan = Plan(
            code='enterprise',
            name='Enterprise Plan',
            tier=PlanTier.ENTERPRISE,
            price_monthly=499.99,
            price_yearly=4999.99,
            quotas_json={
                'scans_per_day': -1,  # Unlimited
                'api_calls_per_minute': -1,  # Unlimited
                'max_api_keys': -1,  # Unlimited
                'symbols_per_scan': -1  # Unlimited
            },
            allowed_endpoints_json=['*'],  # All endpoints
            features_json={
                'basic_scanning': True,
                'api_access': True,
                'custom_alerts': True,
                'priority_support': True,
                'advanced_analytics': True,
                'explosive_scan': True,
                'enhanced_scan': True,
                'pre_earnings_scan': True,
                'technical_analysis': True,
                'volatility_analysis': True,
                'gamma_squeeze_detection': True,
                'mega_discovery_scan': True,
                'comprehensive_pipeline': True,
                'white_label': True,
                'dedicated_support': True,
                'custom_features': True,
                'data_export': True,
                'webhook_integrations': True
            },
            active=True
        )
        
        # Add all plans to database
        db.session.add(free_plan)
        db.session.add(basic_plan)
        db.session.add(premium_plan)
        db.session.add(enterprise_plan)
        
        try:
            db.session.commit()
            print("✅ Successfully created subscription plans:")
            print(f"  - Free Tier: $0/month")
            print(f"  - Basic Plan: ${basic_plan.price_monthly}/month")
            print(f"  - Premium Plan: ${premium_plan.price_monthly}/month")
            print(f"  - Enterprise Plan: ${enterprise_plan.price_monthly}/month")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating plans: {e}")
            return False
        
        return True

def create_test_admin():
    """Create a test admin user"""
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email='admin@optionsscanner.com').first()
        if admin:
            print("Admin user already exists")
            return
        
        from auth import AuthManager
        
        # Create admin user
        admin = User(
            email='admin@optionsscanner.com',
            password_hash=AuthManager.hash_password('Admin123!'),
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        
        db.session.add(admin)
        
        try:
            db.session.commit()
            print("✅ Created admin user: admin@optionsscanner.com")
            print("   Password: Admin123!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin user: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("🔧 Seeding database with subscription plans...")
    seed_plans()
    print("\n🔧 Creating test admin user...")
    create_test_admin()
    print("\n✅ Database seeding complete!")
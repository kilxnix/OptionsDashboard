"""
Create admin user for testing purposes
"""
from models import db, User, UserRole, UserStatus, Plan, Subscription, PlanTier, SubscriptionStatus
from auth import AuthManager
from datetime import datetime, timedelta
from flask import Flask
import os

# Initialize Flask app to use database
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    # Get admin credentials from environment variables (REQUIRED for security)
    admin_email = os.environ.get("TEST_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("TEST_ADMIN_PASSWORD")
    
    if not admin_password:
        print("\n⚠️  WARNING: TEST_ADMIN_PASSWORD not set!")
        print("Using a temporary password for development only.")
        print("For production, set:")
        print("  export TEST_ADMIN_EMAIL=admin@example.com")
        print("  export TEST_ADMIN_PASSWORD=YourSecurePassword123!")
        print("\n")
        # Use a temporary password for development ONLY
        admin_password = "TempDevPassword123!"
    
    # Check if admin exists
    existing_admin = User.query.filter_by(email=admin_email).first()
    
    if existing_admin:
        print(f"Admin user already exists: {admin_email}")
        # Update to ensure it's an admin
        existing_admin.role = UserRole.ADMIN
        existing_admin.status = UserStatus.ACTIVE
        existing_admin.account_balance = 1000.00  # Give admin some balance for testing
        db.session.commit()
        print("Updated admin user with admin privileges and $1000 balance")
    else:
        # Create new admin
        admin_user = User(
            email=admin_email,
            password_hash=AuthManager.hash_password(admin_password),
            first_name="System",
            last_name="Admin",
            company="Options Scanner Pro",
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            account_balance=1000.00
        )
        db.session.add(admin_user)
        
        # Give admin a premium subscription
        premium_plan = Plan.query.filter_by(tier=PlanTier.PREMIUM).first()
        if not premium_plan:
            # Create premium plan if it doesn't exist
            premium_plan = Plan(
                code='premium',
                name='Premium Plan',
                tier=PlanTier.PREMIUM,
                price_monthly=99.00,
                quotas_json={'scans_per_day': 500, 'api_calls_per_minute': 60},
                allowed_endpoints_json=['/scan', '/explosive-scan', '/jpm-explosion-hunter'],
                features_json={'all_features': True}
            )
            db.session.add(premium_plan)
            db.session.commit()
        
        # Create subscription for admin
        admin_subscription = Subscription(
            user_id=admin_user.id,
            plan_id=premium_plan.id,
            status=SubscriptionStatus.ACTIVE,
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=365)  # 1 year subscription
        )
        db.session.add(admin_subscription)
        db.session.commit()
        
        print(f"Created admin user: {admin_email}")
        if os.environ.get("TEST_ADMIN_PASSWORD"):
            print("Password: Set from environment variable")
        else:
            print(f"Password: {admin_password} (⚠️ DEVELOPMENT ONLY)")
        print("Admin has Premium subscription and $1000 balance")
    
    print("\n✅ Admin user ready for testing!")
    print(f"Email: {admin_email}")
    if os.environ.get("TEST_ADMIN_PASSWORD"):
        print("Password: Securely set from environment")
    else:
        print(f"Password: {admin_password} (⚠️ TEST ONLY - DO NOT USE IN PRODUCTION!)")
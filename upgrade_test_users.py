#!/usr/bin/env python3
"""
Upgrade test users to different subscription tiers for testing
"""
import os
import sys
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Plan, Subscription, PlanTier, SubscriptionStatus
from flask import Flask

# Initialize Flask app and database
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def upgrade_user_to_tier(email, tier):
    """Upgrade a user to a specific tier"""
    with app.app_context():
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"✗ User {email} not found")
            return False
        
        # Find or create plan for the tier
        plan = Plan.query.filter_by(tier=tier).first()
        if not plan:
            # Create the plan
            if tier == PlanTier.BASIC:
                plan = Plan(
                    code='basic',
                    name='Basic Tier',
                    tier=PlanTier.BASIC,
                    price_monthly=29,
                    quotas_json={'scans_per_day': 50, 'api_calls_per_minute': 60},
                    allowed_endpoints_json=['/scan', '/explosive-scan', '/explosive-earnings-combo'],
                    features_json={'explosive_scanning': True, 'technical_analysis': True}
                )
            elif tier == PlanTier.PREMIUM:
                plan = Plan(
                    code='premium',
                    name='Premium Tier',
                    tier=PlanTier.PREMIUM,
                    price_monthly=99,
                    quotas_json={'scans_per_day': 500, 'api_calls_per_minute': 300},
                    allowed_endpoints_json='all',
                    features_json={'all_features': True}
                )
            else:
                print(f"✗ Invalid tier: {tier}")
                return False
            
            db.session.add(plan)
            db.session.commit()
        
        # Cancel existing subscription
        existing_sub = Subscription.query.filter_by(
            user_id=user.id,
            status=SubscriptionStatus.ACTIVE
        ).first()
        
        if existing_sub:
            existing_sub.status = SubscriptionStatus.CANCELED
            existing_sub.canceled_at = datetime.utcnow()
        
        # Create new subscription
        new_sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow() + timedelta(days=30)
        )
        
        db.session.add(new_sub)
        db.session.commit()
        
        print(f"✓ Upgraded {email} to {tier.value} tier")
        return True

def main():
    """Main function to upgrade test users"""
    print("=" * 60)
    print("UPGRADING TEST USERS TO DIFFERENT TIERS")
    print("=" * 60)
    
    # Upgrade test users
    upgrades = [
        ('basic_test@example.com', PlanTier.BASIC),
        ('premium_test@example.com', PlanTier.PREMIUM),
        # Keep free_test@example.com on FREE tier
    ]
    
    for email, tier in upgrades:
        print(f"\nUpgrading {email} to {tier.value}...")
        upgrade_user_to_tier(email, tier)
    
    print("\n" + "=" * 60)
    print("UPGRADE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
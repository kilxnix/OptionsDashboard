#!/usr/bin/env python
"""
Seed script to initialize Stripe products and prices
Run this script once to set up all Stripe products for the Options Scanner SaaS
"""
import os
import sys
from stripe_manager import StripeManager
from models import db, Plan, PlanTier
from flask import Flask
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

def seed_plans_and_stripe():
    """Seed database with plans and create corresponding Stripe products"""
    with app.app_context():
        print("=" * 60)
        print("Options Scanner SaaS - Stripe Setup Script")
        print("=" * 60)
        print()
        
        # Ensure database tables exist
        db.create_all()
        print("✓ Database tables created/verified")
        
        # Create or update plans in database
        plans_config = [
            {
                'tier': PlanTier.FREE,
                'code': 'free',
                'name': 'Free Tier',
                'price_monthly': 0,
                'quotas': {
                    'scans_per_day': 5,
                    'api_calls_per_minute': 10,
                    'max_api_keys': 1
                },
                'endpoints': ['/scan'],
                'features': {
                    'basic_scanning': True,
                    'options_chain': False,
                    'explosive_scanner': False,
                    'jpm_hunter': False,
                    'api_access': True,
                    'priority_support': False,
                    'custom_alerts': False
                }
            },
            {
                'tier': PlanTier.BASIC,
                'code': 'basic',
                'name': 'Basic Plan',
                'price_monthly': 29.00,
                'quotas': {
                    'scans_per_day': 50,
                    'api_calls_per_minute': 30,
                    'max_api_keys': 3
                },
                'endpoints': ['/scan', '/explosive-scan'],
                'features': {
                    'basic_scanning': True,
                    'options_chain': True,
                    'explosive_scanner': True,
                    'jpm_hunter': False,
                    'api_access': True,
                    'priority_support': False,
                    'custom_alerts': True,
                    'email_notifications': True
                }
            },
            {
                'tier': PlanTier.PREMIUM,
                'code': 'premium',
                'name': 'Premium Plan',
                'price_monthly': 99.00,
                'quotas': {
                    'scans_per_day': 500,
                    'api_calls_per_minute': 60,
                    'max_api_keys': 10
                },
                'endpoints': ['/scan', '/explosive-scan', '/jpm-explosion-hunter'],
                'features': {
                    'basic_scanning': True,
                    'options_chain': True,
                    'explosive_scanner': True,
                    'jpm_hunter': True,
                    'api_access': True,
                    'priority_support': True,
                    'custom_alerts': True,
                    'email_notifications': True,
                    'slack_integration': True,
                    'historical_data': True
                }
            },
            {
                'tier': PlanTier.ENTERPRISE,
                'code': 'enterprise',
                'name': 'Enterprise Plan',
                'price_monthly': 299.00,
                'quotas': {
                    'scans_per_day': -1,  # Unlimited
                    'api_calls_per_minute': -1,  # Unlimited
                    'max_api_keys': -1  # Unlimited
                },
                'endpoints': ['*'],  # All endpoints
                'features': {
                    'basic_scanning': True,
                    'options_chain': True,
                    'explosive_scanner': True,
                    'jpm_hunter': True,
                    'api_access': True,
                    'priority_support': True,
                    'custom_alerts': True,
                    'email_notifications': True,
                    'slack_integration': True,
                    'historical_data': True,
                    'dedicated_support': True,
                    'custom_endpoints': True,
                    'white_label': True,
                    'sla_guarantee': True
                }
            }
        ]
        
        print("\n📦 Creating/Updating Plans in Database:")
        print("-" * 40)
        
        for config in plans_config:
            plan = Plan.query.filter_by(tier=config['tier']).first()
            
            if not plan:
                plan = Plan(
                    tier=config['tier'],
                    code=config['code'],
                    name=config['name']
                )
                db.session.add(plan)
                print(f"  ✓ Created new plan: {config['name']}")
            else:
                print(f"  ✓ Updating existing plan: {config['name']}")
            
            # Update plan details
            plan.name = config['name']
            plan.price_monthly = config['price_monthly']
            plan.price_yearly = config['price_monthly'] * 10 if config['price_monthly'] > 0 else 0  # 2 months free
            plan.quotas_json = config['quotas']
            plan.allowed_endpoints_json = config['endpoints']
            plan.features_json = config['features']
            plan.active = True
            
            # Display plan info
            print(f"    - Price: ${config['price_monthly']}/month")
            print(f"    - Scans/day: {config['quotas']['scans_per_day'] if config['quotas']['scans_per_day'] > 0 else 'Unlimited'}")
            print(f"    - API calls/min: {config['quotas']['api_calls_per_minute'] if config['quotas']['api_calls_per_minute'] > 0 else 'Unlimited'}")
        
        db.session.commit()
        print("\n✓ All plans saved to database")
        
        # Create Stripe products and prices (skip free tier)
        print("\n💳 Creating Stripe Products and Prices:")
        print("-" * 40)
        
        results = StripeManager.create_or_update_products()
        
        for tier_name, result in results.items():
            if result['status'] == 'success':
                print(f"  ✓ {tier_name.upper()}: Product={result['product_id']}, Price={result['price_id']}")
            else:
                print(f"  ✗ {tier_name.upper()}: Error - {result.get('error', 'Unknown error')}")
        
        # Verify all plans have Stripe IDs (except free)
        print("\n🔍 Verifying Stripe Integration:")
        print("-" * 40)
        
        all_good = True
        for plan in Plan.query.all():
            if plan.tier == PlanTier.FREE:
                print(f"  ✓ {plan.name}: No Stripe product needed (free tier)")
            elif plan.stripe_product_id and plan.stripe_price_monthly_id:
                print(f"  ✓ {plan.name}: Stripe integration complete")
                print(f"    Product ID: {plan.stripe_product_id}")
                print(f"    Price ID: {plan.stripe_price_monthly_id}")
            else:
                print(f"  ✗ {plan.name}: Missing Stripe integration!")
                all_good = False
        
        print("\n" + "=" * 60)
        if all_good:
            print("✅ SUCCESS: All plans are properly configured!")
            print("\nNext steps:")
            print("1. Configure Stripe webhook endpoint in Stripe Dashboard:")
            print(f"   URL: https://your-domain.com/api/stripe/webhook")
            print("   Events to listen for:")
            print("   - checkout.session.completed")
            print("   - customer.subscription.created")
            print("   - customer.subscription.updated")
            print("   - customer.subscription.deleted")
            print("   - invoice.payment_succeeded")
            print("   - invoice.payment_failed")
            print("\n2. Set STRIPE_WEBHOOK_SECRET environment variable")
            print("\n3. Test with Stripe CLI:")
            print("   stripe listen --forward-to localhost:5000/api/stripe/webhook")
        else:
            print("⚠️  WARNING: Some plans are missing Stripe integration.")
            print("Please check your Stripe API key and try again.")
        
        print("=" * 60)
        
        return all_good

if __name__ == "__main__":
    success = seed_plans_and_stripe()
    sys.exit(0 if success else 1)
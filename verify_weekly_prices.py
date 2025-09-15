#!/usr/bin/env python3
"""
Verify and create weekly price IDs in Stripe
"""
import os
import sys
from stripe_manager import StripeManager
from models import db, Plan, PlanTier
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

def verify_weekly_prices():
    """Verify all weekly price IDs are set up"""
    with app.app_context():
        print("=" * 60)
        print("VERIFYING WEEKLY PRICE IDs IN DATABASE")
        print("=" * 60)
        
        # Check each plan tier
        for tier in [PlanTier.BASIC, PlanTier.PREMIUM]:
            print(f"\n📋 Checking {tier.value} plan...")
            plan = Plan.query.filter_by(tier=tier).first()
            
            if not plan:
                print(f"❌ {tier.value} plan not found in database")
                continue
            
            print(f"  Plan ID: {plan.id}")
            print(f"  Plan Name: {plan.name}")
            
            # Check monthly price IDs
            print("\n  💵 Monthly Price IDs:")
            print(f"    USD: {plan.stripe_price_monthly_id or 'NOT SET'}")
            print(f"    EUR: {plan.stripe_price_eur_id or 'NOT SET'}")
            print(f"    GBP: {plan.stripe_price_gbp_id or 'NOT SET'}")
            print(f"    USDC: {plan.stripe_price_usdc_id or 'NOT SET'}")
            
            # Check weekly price IDs
            print("\n  📅 Weekly Price IDs:")
            print(f"    USD: {plan.stripe_price_weekly_id or 'NOT SET'}")
            print(f"    EUR: {plan.stripe_price_weekly_eur_id or 'NOT SET'}")
            print(f"    GBP: {plan.stripe_price_weekly_gbp_id or 'NOT SET'}")
            print(f"    USDC: {plan.stripe_price_weekly_usdc_id or 'NOT SET'}")
            
            # Check if any weekly prices are missing
            weekly_missing = False
            if not plan.stripe_price_weekly_id:
                print(f"    ⚠️  Weekly USD price not configured!")
                weekly_missing = True
            if not plan.stripe_price_weekly_eur_id:
                print(f"    ⚠️  Weekly EUR price not configured!")
                weekly_missing = True
            if not plan.stripe_price_weekly_gbp_id:
                print(f"    ⚠️  Weekly GBP price not configured!")
                weekly_missing = True
            if not plan.stripe_price_weekly_usdc_id:
                print(f"    ⚠️  Weekly USDC price not configured!")
                weekly_missing = True
            
            if not weekly_missing:
                print(f"    ✅ All weekly prices configured!")
        
        print("\n" + "=" * 60)
        print("CREATING/UPDATING STRIPE PRODUCTS AND PRICES")
        print("=" * 60)
        
        # Create or update Stripe products
        results = StripeManager.create_or_update_products()
        
        for tier_name, result in results.items():
            print(f"\n{tier_name}:")
            if result['status'] == 'success':
                print(f"  ✅ Product ID: {result['product_id']}")
                if 'monthly_price_ids' in result:
                    print(f"  ✅ Created {len(result['monthly_price_ids'])} monthly price(s)")
                if 'weekly_price_ids' in result:
                    print(f"  ✅ Created {len(result['weekly_price_ids'])} weekly price(s)")
            else:
                print(f"  ❌ Error: {result['error']}")
        
        print("\n" + "=" * 60)
        print("VERIFICATION AFTER UPDATE")
        print("=" * 60)
        
        # Verify again after update
        for tier in [PlanTier.BASIC, PlanTier.PREMIUM]:
            print(f"\n📋 Final check for {tier.value} plan...")
            plan = Plan.query.filter_by(tier=tier).first()
            
            if plan:
                weekly_ok = all([
                    plan.stripe_price_weekly_id,
                    plan.stripe_price_weekly_eur_id,
                    plan.stripe_price_weekly_gbp_id,
                    plan.stripe_price_weekly_usdc_id
                ])
                
                monthly_ok = all([
                    plan.stripe_price_monthly_id,
                    plan.stripe_price_eur_id,
                    plan.stripe_price_gbp_id,
                    plan.stripe_price_usdc_id
                ])
                
                if weekly_ok and monthly_ok:
                    print(f"  ✅ All price IDs configured!")
                else:
                    if not weekly_ok:
                        print(f"  ⚠️  Some weekly prices still missing")
                    if not monthly_ok:
                        print(f"  ⚠️  Some monthly prices still missing")
        
        print("\n✅ Verification complete!")
        return True

if __name__ == "__main__":
    try:
        verify_weekly_prices()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
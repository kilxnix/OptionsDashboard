"""
Stripe integration manager for the Options Scanner SaaS platform
"""
import os
import stripe
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from models import db, User, Plan, Subscription, PlanTier, SubscriptionStatus, AccountTransaction, TransactionType
from db_utils import DatabaseManager
from flask import current_app
import logging

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Configure logging
logger = logging.getLogger(__name__)

# Stripe price configurations
PLAN_PRICES = {
    PlanTier.FREE: {
        'name': 'Free Tier',
        'price_monthly': 0,
        'price_weekly': 0,
        'features': {
            'scans_per_day': 5,
            'api_calls_per_minute': 10,
            'endpoints': ['/scan'],
            'description': 'Basic scanning capabilities'
        }
    },
    PlanTier.BASIC: {
        'name': 'Basic Plan',
        'price_monthly': 2900,  # $29.00 in cents
        'price_weekly': 700,    # $7.00 in cents
        'price_eur': 2700,     # €27.00 in cents
        'price_eur_weekly': 650,  # €6.50 in cents
        'price_gbp': 2300,     # £23.00 in pence
        'price_gbp_weekly': 550,  # £5.50 in pence
        'price_usdc': 2900,    # 29.00 USDC in cents equivalent
        'price_usdc_weekly': 700,  # 7.00 USDC in cents equivalent
        'trial_days': 14,
        'features': {
            'scans_per_day': 50,
            'api_calls_per_minute': 30,
            'endpoints': ['/scan', '/explosive-scan'],
            'description': 'Enhanced scanning with explosive move detection'
        }
    },
    PlanTier.PREMIUM: {
        'name': 'Premium Plan',
        'price_monthly': 9900,  # $99.00 in cents
        'price_weekly': 2500,   # $25.00 in cents
        'price_eur': 9200,     # €92.00 in cents
        'price_eur_weekly': 2300,  # €23.00 in cents
        'price_gbp': 7900,     # £79.00 in pence
        'price_gbp_weekly': 2000,  # £20.00 in pence
        'price_usdc': 9900,    # 99.00 USDC in cents equivalent
        'price_usdc_weekly': 2500,  # 25.00 USDC in cents equivalent
        'trial_days': 14,
        'features': {
            'scans_per_day': 500,
            'api_calls_per_minute': 60,
            'endpoints': ['/scan', '/explosive-scan', '/jpm-explosion-hunter'],
            'description': 'Advanced scanning with all premium features'
        }
    }
}

# Top-up configurations
TOPUP_AMOUNTS = {
    'small': {'amount': 1000, 'display': '$10'},
    'medium': {'amount': 2500, 'display': '$25'},
    'large': {'amount': 5000, 'display': '$50'},
    'xlarge': {'amount': 10000, 'display': '$100'}
}

# Currency conversion rates (approximate, should be updated regularly)
CURRENCY_RATES = {
    'USD': 1.0,
    'EUR': 0.93,  # 1 USD = 0.93 EUR
    'GBP': 0.79,  # 1 USD = 0.79 GBP
    'USDC': 1.0   # 1 USD = 1 USDC (stablecoin)
}


def convert_currency(amount_usd: int, target_currency: str) -> int:
    """Convert USD amount (in cents) to target currency
    
    Args:
        amount_usd: Amount in USD cents
        target_currency: Target currency code (EUR, GBP, USDC)
    
    Returns:
        Amount in target currency's smallest unit (cents/pence)
    """
    if target_currency == 'USD':
        return amount_usd
    
    rate = CURRENCY_RATES.get(target_currency, 1.0)
    return int(amount_usd * rate)


class StripeManager:
    """Manages all Stripe-related operations"""
    
    @staticmethod
    def create_or_update_products() -> Dict[str, Any]:
        """Create or update Stripe products and prices for all tiers in multiple currencies with weekly and monthly options"""
        results = {}
        
        # Define supported currencies for monthly billing
        monthly_currencies = {
            'usd': {'field': 'price_monthly', 'db_field': 'stripe_price_monthly_id'},
            'eur': {'field': 'price_eur', 'db_field': 'stripe_price_eur_id'},
            'gbp': {'field': 'price_gbp', 'db_field': 'stripe_price_gbp_id'},
            'usdc': {'field': 'price_usdc', 'db_field': 'stripe_price_usdc_id'}
        }
        
        # Define supported currencies for weekly billing
        weekly_currencies = {
            'usd': {'field': 'price_weekly', 'db_field': 'stripe_price_weekly_id'},
            'eur': {'field': 'price_eur_weekly', 'db_field': 'stripe_price_weekly_eur_id'},
            'gbp': {'field': 'price_gbp_weekly', 'db_field': 'stripe_price_weekly_gbp_id'},
            'usdc': {'field': 'price_usdc_weekly', 'db_field': 'stripe_price_weekly_usdc_id'}
        }
        
        for tier, config in PLAN_PRICES.items():
            if tier == PlanTier.FREE:
                # Skip free tier - no Stripe product needed
                continue
            
            try:
                # Create or retrieve product
                product_id = f'prod_{tier.value}_options_scanner'
                
                try:
                    product = stripe.Product.retrieve(product_id)
                    # Update existing product
                    product = stripe.Product.modify(
                        product_id,
                        name=config['name'],
                        description=config['features']['description'],
                        metadata={
                            'tier': tier.value,
                            'scans_per_day': str(config['features']['scans_per_day']),
                            'api_calls_per_minute': str(config['features']['api_calls_per_minute'])
                        }
                    )
                except stripe.error.InvalidRequestError:
                    # Create new product
                    product = stripe.Product.create(
                        id=product_id,
                        name=config['name'],
                        description=config['features']['description'],
                        metadata={
                            'tier': tier.value,
                            'scans_per_day': str(config['features']['scans_per_day']),
                            'api_calls_per_minute': str(config['features']['api_calls_per_minute'])
                        }
                    )
                
                # Create prices for each currency (monthly)
                monthly_price_ids = {}
                for currency, currency_info in monthly_currencies.items():
                    price_field = currency_info['field']
                    
                    # Get price amount for this currency
                    if currency == 'usd':
                        price_amount = config.get('price_monthly', 0)
                    else:
                        price_amount = config.get(price_field, config['price_monthly'])
                    
                    if price_amount == 0 and tier != PlanTier.FREE:
                        continue  # Skip creating price for non-supported currency
                    
                    # For USDC (stablecoin), use USD pricing but mark as crypto
                    if currency == 'usdc':
                        # USDC uses USD pricing as it's a stablecoin
                        price_amount = config.get('price_monthly', 0)
                    
                    # Create or retrieve price
                    price_id = f'price_{tier.value}_{currency}_monthly'
                    
                    # Search for existing price
                    prices = stripe.Price.list(product=product.id, active=True, currency=currency if currency != 'usdc' else 'usd')
                    existing_price = None
                    for price in prices.data:
                        if price.recurring and price.recurring.interval == 'month':
                            if currency == 'usdc' and price.metadata.get('is_crypto') == 'true':
                                existing_price = price
                                break
                            elif currency != 'usdc' and not price.metadata.get('is_crypto'):
                                existing_price = price
                                break
                    
                    if not existing_price:
                        # Create new price
                        price_metadata = {'tier': tier.value}
                        if currency == 'usdc':
                            price_metadata['is_crypto'] = 'true'
                            price_metadata['currency_type'] = 'usdc'
                        
                        price = stripe.Price.create(
                            product=product.id,
                            unit_amount=price_amount,
                            currency='usd' if currency == 'usdc' else currency,
                            recurring={'interval': 'month'},
                            metadata=price_metadata
                        )
                    else:
                        price = existing_price
                    
                    monthly_price_ids[currency_info['db_field']] = price.id
                
                # Create prices for each currency (weekly)
                weekly_price_ids = {}
                for currency, currency_info in weekly_currencies.items():
                    price_field = currency_info['field']
                    
                    # Get price amount for this currency
                    if currency == 'usd':
                        price_amount = config.get('price_weekly', 0)
                    else:
                        price_amount = config.get(price_field, 0)
                    
                    if price_amount == 0 and tier != PlanTier.FREE:
                        continue  # Skip creating price for non-supported currency
                    
                    # For USDC (stablecoin), use USD pricing but mark as crypto
                    if currency == 'usdc':
                        # USDC uses USD pricing as it's a stablecoin
                        price_amount = config.get('price_weekly', 0)
                    
                    # Create or retrieve price
                    price_id = f'price_{tier.value}_{currency}_weekly'
                    
                    # Search for existing price
                    prices = stripe.Price.list(product=product.id, active=True, currency=currency if currency != 'usdc' else 'usd')
                    existing_price = None
                    for price in prices.data:
                        if price.recurring and price.recurring.interval == 'week':
                            if currency == 'usdc' and price.metadata.get('is_crypto') == 'true':
                                existing_price = price
                                break
                            elif currency != 'usdc' and not price.metadata.get('is_crypto'):
                                existing_price = price
                                break
                    
                    if not existing_price and price_amount > 0:
                        # Create new price
                        price_metadata = {'tier': tier.value, 'billing_period': 'weekly'}
                        if currency == 'usdc':
                            price_metadata['is_crypto'] = 'true'
                            price_metadata['currency_type'] = 'usdc'
                        
                        price = stripe.Price.create(
                            product=product.id,
                            unit_amount=price_amount,
                            currency='usd' if currency == 'usdc' else currency,
                            recurring={'interval': 'week'},
                            metadata=price_metadata
                        )
                        weekly_price_ids[currency_info['db_field']] = price.id
                        logger.info(f"Created weekly price {price.id} for {tier.value} in {currency}")
                    elif existing_price:
                        weekly_price_ids[currency_info['db_field']] = existing_price.id
                
                # Update database with Stripe IDs
                plan = Plan.query.filter_by(tier=tier).first()
                if not plan:
                    plan = Plan(
                        code=tier.value,
                        name=config['name'],
                        tier=tier,
                        price_monthly=config['price_monthly'] / 100,  # Convert cents to dollars
                        price_weekly=config.get('price_weekly', 0) / 100,  # Convert cents to dollars
                        quotas_json={
                            'scans_per_day': config['features']['scans_per_day'],
                            'api_calls_per_minute': config['features']['api_calls_per_minute']
                        },
                        allowed_endpoints_json=config['features']['endpoints'],
                        features_json={'description': config['features']['description']}
                    )
                    db.session.add(plan)
                else:
                    # Update existing plan with weekly pricing
                    plan.price_weekly = config.get('price_weekly', 0) / 100
                
                plan.stripe_product_id = product.id
                # Set all currency price IDs (monthly)
                for db_field, price_id in monthly_price_ids.items():
                    setattr(plan, db_field, price_id)
                
                # Set all currency price IDs (weekly)
                for db_field, price_id in weekly_price_ids.items():
                    setattr(plan, db_field, price_id)
                
                db.session.commit()
                
                results[tier.value] = {
                    'product_id': product.id,
                    'price_ids': price_ids,
                    'status': 'success'
                }
                
            except Exception as e:
                logger.error(f"Error creating Stripe product for {tier.value}: {str(e)}")
                results[tier.value] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    @staticmethod
    def create_checkout_session(
        user_id: int,
        plan_tier: PlanTier,
        success_url: str,
        cancel_url: str,
        currency: str = 'usd',
        payment_type: str = 'card'
    ) -> Optional[Dict[str, Any]]:
        """Create a Stripe checkout session for subscription with multi-currency and crypto support
        
        Args:
            user_id: User ID
            plan_tier: Plan tier to subscribe to
            success_url: URL to redirect to on success
            cancel_url: URL to redirect to on cancel
            currency: Currency to use (usd, eur, gbp, usdc)
            payment_type: Payment type (card, crypto)
        """
        try:
            user = DatabaseManager.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Get plan details
            plan = Plan.query.filter_by(tier=plan_tier).first()
            if not plan:
                raise ValueError(f"Plan {plan_tier.value} not found")
            
            # Determine which price ID to use based on currency
            price_id = None
            if currency == 'usd' or (currency == 'usdc' and payment_type != 'crypto'):
                price_id = plan.stripe_price_monthly_id
            elif currency == 'eur':
                price_id = plan.stripe_price_eur_id
            elif currency == 'gbp':
                price_id = plan.stripe_price_gbp_id
            elif currency == 'usdc' and payment_type == 'crypto':
                price_id = plan.stripe_price_usdc_id
            
            if not price_id:
                raise ValueError(f"Price not configured for {currency} in {plan_tier.value} plan")
            
            # Create or retrieve Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={
                        'user_id': str(user.id),
                        'first_name': user.first_name or '',
                        'last_name': user.last_name or ''
                    }
                )
                user.stripe_customer_id = customer.id
                db.session.commit()
            else:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
            
            # Check for trial eligibility
            trial_period_days = None
            if plan_tier in PLAN_PRICES and 'trial_days' in PLAN_PRICES[plan_tier]:
                # Check if user has used trial before
                existing_subs = Subscription.query.filter_by(
                    user_id=user_id,
                    plan_id=plan.id
                ).filter(Subscription.trial_start.isnot(None)).first()
                
                if not existing_subs:
                    trial_period_days = PLAN_PRICES[plan_tier]['trial_days']
            
            # Determine payment method types
            if payment_type == 'crypto' and currency == 'usdc':
                # For crypto payments (USDC stablecoin)
                payment_method_types = ['card', 'link', 'crypto']
            else:
                # Standard card payments
                payment_method_types = ['card']
            
            # Create checkout session
            session_params = {
                'customer': customer.id,
                'payment_method_types': payment_method_types,
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    'user_id': str(user.id),
                    'plan_tier': plan_tier.value,
                    'currency': currency,
                    'payment_type': payment_type
                }
            }
            
            # Add automatic tax collection if needed
            session_params['automatic_tax'] = {'enabled': True}
            
            # Enable customer to choose their preferred currency
            if currency != 'usdc':
                session_params['currency'] = currency
            
            if trial_period_days:
                session_params['subscription_data'] = {
                    'trial_period_days': trial_period_days,
                    'metadata': {
                        'user_id': str(user.id),
                        'plan_tier': plan_tier.value,
                        'currency': currency
                    }
                }
            
            session = stripe.checkout.Session.create(**session_params)
            
            return {
                'session_id': session.id,
                'url': session.url,
                'customer_id': customer.id,
                'trial_days': trial_period_days,
                'currency': currency,
                'payment_type': payment_type
            }
            
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return None
    
    @staticmethod
    def create_portal_session(user_id: int, return_url: str) -> Optional[str]:
        """Create a Stripe customer portal session for subscription management"""
        try:
            user = DatabaseManager.get_user_by_id(user_id)
            if not user or not user.stripe_customer_id:
                raise ValueError("User not found or no Stripe customer")
            
            # Create portal session
            # Note: This requires configuration in Stripe Dashboard
            # Go to https://dashboard.stripe.com/settings/billing/portal to configure
            try:
                session = stripe.billing_portal.Session.create(
                    customer=user.stripe_customer_id,
                    return_url=return_url
                )
                return session.url
            except stripe.error.InvalidRequestError as e:
                # If portal not configured, return a message
                logger.warning(f"Customer portal not configured: {str(e)}")
                # Return None to indicate portal not available
                return None
            
        except Exception as e:
            logger.error(f"Error creating portal session: {str(e)}")
            return None
    
    @staticmethod
    def handle_webhook_event(payload: str, signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            # Verify webhook signature
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(
                    payload, signature, STRIPE_WEBHOOK_SECRET
                )
            else:
                # For testing without webhook secret
                event = json.loads(payload)
            
            # Process event based on type
            event_type = event['type']
            data = event['data']['object']
            
            logger.info(f"Processing Stripe webhook: {event_type}")
            
            if event_type == 'checkout.session.completed':
                # Check if this is a top-up session
                metadata = data.get('metadata', {})
                if metadata.get('type') == 'topup':
                    return StripeManager._handle_topup_completed(data)
                else:
                    return StripeManager._handle_checkout_completed(data)
            
            elif event_type == 'customer.subscription.created':
                return StripeManager._handle_subscription_created(data)
            
            elif event_type == 'customer.subscription.updated':
                return StripeManager._handle_subscription_updated(data)
            
            elif event_type == 'customer.subscription.deleted':
                return StripeManager._handle_subscription_deleted(data)
            
            elif event_type == 'invoice.payment_succeeded':
                return StripeManager._handle_payment_succeeded(data)
            
            elif event_type == 'invoice.payment_failed':
                return StripeManager._handle_payment_failed(data)
            
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return {'status': 'unhandled', 'event_type': event_type}
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return {'status': 'error', 'error': 'Invalid signature'}
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_topup_completed(session: Dict) -> Dict[str, Any]:
        """Handle successful top-up checkout session completion"""
        try:
            session_id = session.get('id')
            
            # Process the top-up payment
            success = StripeManager.process_topup_payment(session_id)
            
            if success:
                logger.info(f"Top-up session {session_id} processed successfully")
                return {'status': 'success', 'message': 'Top-up processed'}
            else:
                logger.error(f"Failed to process top-up session {session_id}")
                return {'status': 'error', 'error': 'Top-up processing failed'}
                
        except Exception as e:
            logger.error(f"Error handling top-up completion: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_checkout_completed(session: Dict) -> Dict[str, Any]:
        """Handle successful checkout session completion"""
        try:
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            metadata = session.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            
            if not user_id:
                # Try to find user by customer ID
                user = User.query.filter_by(stripe_customer_id=customer_id).first()
                if user:
                    user_id = user.id
            
            if user_id and subscription_id:
                # Update user's subscription info
                logger.info(f"Checkout completed for user {user_id}, subscription {subscription_id}")
                
                # The subscription will be handled by subscription.created webhook
                return {'status': 'success', 'user_id': user_id}
            
            return {'status': 'error', 'error': 'Missing user or subscription ID'}
            
        except Exception as e:
            logger.error(f"Error handling checkout completion: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_subscription_created(subscription: Dict) -> Dict[str, Any]:
        """Handle new subscription creation"""
        try:
            customer_id = subscription.get('customer')
            stripe_sub_id = subscription.get('id')
            status = subscription.get('status')
            metadata = subscription.get('metadata', {})
            
            # Find user
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if not user:
                user_id = int(metadata.get('user_id', 0))
                if user_id:
                    user = DatabaseManager.get_user_by_id(user_id)
            
            if not user:
                logger.error(f"User not found for customer {customer_id}")
                return {'status': 'error', 'error': 'User not found'}
            
            # Get plan tier from price ID
            price_id = subscription['items']['data'][0]['price']['id']
            plan = Plan.query.filter_by(stripe_price_monthly_id=price_id).first()
            
            if not plan:
                logger.error(f"Plan not found for price {price_id}")
                return {'status': 'error', 'error': 'Plan not found'}
            
            # Check if subscription already exists
            existing_sub = Subscription.query.filter_by(
                stripe_subscription_id=stripe_sub_id
            ).first()
            
            if existing_sub:
                # Update existing subscription
                existing_sub.status = StripeManager._map_stripe_status(status)
                existing_sub.updated_at = datetime.utcnow()
            else:
                # Create new subscription record
                new_sub = Subscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    stripe_subscription_id=stripe_sub_id,
                    status=StripeManager._map_stripe_status(status),
                    period_start=datetime.fromtimestamp(subscription['current_period_start']),
                    period_end=datetime.fromtimestamp(subscription['current_period_end'])
                )
                
                # Set trial dates if applicable
                if subscription.get('trial_start'):
                    new_sub.trial_start = datetime.fromtimestamp(subscription['trial_start'])
                    new_sub.trial_end = datetime.fromtimestamp(subscription['trial_end'])
                
                db.session.add(new_sub)
            
            # Cancel any other active subscriptions
            other_subs = Subscription.query.filter(
                Subscription.user_id == user.id,
                Subscription.id != (existing_sub.id if existing_sub else -1),
                Subscription.status == SubscriptionStatus.ACTIVE
            ).all()
            
            for sub in other_subs:
                sub.status = SubscriptionStatus.CANCELED
                sub.canceled_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Subscription created/updated for user {user.id}, plan {plan.tier.value}")
            return {'status': 'success', 'user_id': user.id, 'plan': plan.tier.value}
            
        except Exception as e:
            logger.error(f"Error handling subscription creation: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_subscription_updated(subscription: Dict) -> Dict[str, Any]:
        """Handle subscription updates"""
        try:
            stripe_sub_id = subscription.get('id')
            status = subscription.get('status')
            
            # Find subscription
            sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
            if not sub:
                # Try to create it
                return StripeManager._handle_subscription_created(subscription)
            
            # Update subscription
            sub.status = StripeManager._map_stripe_status(status)
            sub.period_start = datetime.fromtimestamp(subscription['current_period_start'])
            sub.period_end = datetime.fromtimestamp(subscription['current_period_end'])
            sub.updated_at = datetime.utcnow()
            
            # Check if plan changed
            price_id = subscription['items']['data'][0]['price']['id']
            new_plan = Plan.query.filter_by(stripe_price_monthly_id=price_id).first()
            
            if new_plan and new_plan.id != sub.plan_id:
                sub.plan_id = new_plan.id
                logger.info(f"User {sub.user_id} plan changed to {new_plan.tier.value}")
            
            db.session.commit()
            
            return {'status': 'success', 'subscription_id': sub.id}
            
        except Exception as e:
            logger.error(f"Error handling subscription update: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_subscription_deleted(subscription: Dict) -> Dict[str, Any]:
        """Handle subscription cancellation/deletion"""
        try:
            stripe_sub_id = subscription.get('id')
            
            # Find subscription
            sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
            if not sub:
                logger.warning(f"Subscription {stripe_sub_id} not found for deletion")
                return {'status': 'warning', 'message': 'Subscription not found'}
            
            # Mark as canceled
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.utcnow()
            sub.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Subscription canceled for user {sub.user_id}")
            return {'status': 'success', 'user_id': sub.user_id}
            
        except Exception as e:
            logger.error(f"Error handling subscription deletion: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_payment_succeeded(invoice: Dict) -> Dict[str, Any]:
        """Handle successful payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return {'status': 'skipped', 'reason': 'No subscription ID'}
            
            # Update subscription status if needed
            sub = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
            if sub and sub.status == SubscriptionStatus.PAST_DUE:
                sub.status = SubscriptionStatus.ACTIVE
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Subscription {sub.id} reactivated after payment")
            
            return {'status': 'success'}
            
        except Exception as e:
            logger.error(f"Error handling payment success: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def _handle_payment_failed(invoice: Dict) -> Dict[str, Any]:
        """Handle failed payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return {'status': 'skipped', 'reason': 'No subscription ID'}
            
            # Update subscription status
            sub = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
            if sub:
                sub.status = SubscriptionStatus.PAST_DUE
                sub.updated_at = datetime.utcnow()
                db.session.commit()
                logger.warning(f"Payment failed for subscription {sub.id}, user {sub.user_id}")
            
            return {'status': 'success'}
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def create_topup_session(user_id: int, amount: int, currency: str = 'usd', success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """Create a Stripe checkout session for account top-up
        
        Args:
            user_id: User ID
            amount: Amount in cents
            currency: Currency code (default 'usd')
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
        
        Returns:
            Dict with checkout session details
        """
        try:
            # Get user and ensure they have a Stripe customer ID
            from db_utils import DatabaseManager
            user = User.query.get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create or get Stripe customer
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': str(user.id)}
                )
                user.stripe_customer_id = customer.id
                db.session.commit()
            
            # Create checkout session for one-time payment
            session = stripe.checkout.Session.create(
                customer=user.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': 'Account Credits Top-up',
                            'description': f'Add ${amount/100:.2f} to your account balance'
                        },
                        'unit_amount': amount,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url or 'http://localhost:5000/dashboard?topup=success',
                cancel_url=cancel_url or 'http://localhost:5000/dashboard?topup=cancelled',
                metadata={
                    'user_id': str(user_id),
                    'type': 'topup',
                    'amount': str(amount)
                }
            )
            
            logger.info(f"Created top-up session {session.id} for user {user_id}, amount: {amount}")
            return {
                'session_id': session.id,
                'url': session.url
            }
            
        except Exception as e:
            logger.error(f"Error creating top-up session: {str(e)}")
            raise
    
    @staticmethod
    def process_topup_payment(session_id: str) -> bool:
        """Process successful top-up payment and update user balance
        
        Args:
            session_id: Stripe checkout session ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Retrieve the session
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status != 'paid':
                logger.warning(f"Session {session_id} is not paid yet")
                return False
            
            # Get user and amount from metadata
            user_id = int(session.metadata.get('user_id'))
            amount_cents = int(session.metadata.get('amount'))
            amount_dollars = amount_cents / 100
            
            # Get payment intent for transaction tracking
            payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
            
            # Update user balance
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found for top-up")
                return False
            
            # Create transaction record
            transaction = AccountTransaction(
                user_id=user_id,
                amount=amount_dollars,
                balance_after=user.account_balance + amount_dollars,
                type=TransactionType.TOP_UP,
                description=f'Account top-up via Stripe',
                stripe_payment_intent_id=payment_intent.id,
                status='completed'
            )
            
            # Update user balance
            user.account_balance += amount_dollars
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Successfully processed top-up for user {user_id}: ${amount_dollars}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing top-up payment: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def charge_from_balance(user_id: int, amount: float, description: str, subscription_id: int = None) -> bool:
        """Charge amount from user's account balance
        
        Args:
            user_id: User ID
            amount: Amount to charge in dollars
            description: Description of the charge
            subscription_id: Related subscription ID if applicable
        
        Returns:
            True if successful, False if insufficient balance
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            if user.account_balance < amount:
                logger.warning(f"Insufficient balance for user {user_id}: {user.account_balance} < {amount}")
                return False
            
            # Create transaction record
            transaction = AccountTransaction(
                user_id=user_id,
                amount=-amount,  # Negative for charges
                balance_after=user.account_balance - amount,
                type=TransactionType.SUBSCRIPTION_CHARGE,
                description=description,
                subscription_id=subscription_id,
                status='completed'
            )
            
            # Update user balance
            user.account_balance -= amount
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Successfully charged ${amount} from user {user_id} balance")
            return True
            
        except Exception as e:
            logger.error(f"Error charging from balance: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def _map_stripe_status(stripe_status: str) -> SubscriptionStatus:
        """Map Stripe subscription status to our internal status"""
        status_map = {
            'active': SubscriptionStatus.ACTIVE,
            'past_due': SubscriptionStatus.PAST_DUE,
            'canceled': SubscriptionStatus.CANCELED,
            'incomplete': SubscriptionStatus.INCOMPLETE,
            'incomplete_expired': SubscriptionStatus.INCOMPLETE_EXPIRED,
            'trialing': SubscriptionStatus.TRIALING,
            'unpaid': SubscriptionStatus.UNPAID
        }
        return status_map.get(stripe_status, SubscriptionStatus.UNPAID)
    
    @staticmethod
    def cancel_subscription(user_id: int, immediately: bool = False) -> bool:
        """Cancel a user's subscription"""
        try:
            subscription = DatabaseManager.get_active_subscription(user_id)
            if not subscription or not subscription.stripe_subscription_id:
                return False
            
            # Cancel in Stripe
            if immediately:
                stripe.Subscription.delete(subscription.stripe_subscription_id)
            else:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error canceling subscription: {str(e)}")
            return False
    
    @staticmethod
    def get_subscription_info(user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed subscription information for a user"""
        try:
            subscription = DatabaseManager.get_active_subscription(user_id)
            if not subscription:
                return None
            
            info = {
                'plan': subscription.plan.name,
                'tier': subscription.plan.tier.value,
                'status': subscription.status.value,
                'period_start': subscription.period_start.isoformat(),
                'period_end': subscription.period_end.isoformat(),
                'price': subscription.plan.price_monthly,
                'features': subscription.plan.features_json
            }
            
            # Get Stripe subscription details if available
            if subscription.stripe_subscription_id:
                try:
                    stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
                    info['cancel_at_period_end'] = stripe_sub.cancel_at_period_end
                    info['current_period_end'] = datetime.fromtimestamp(
                        stripe_sub.current_period_end
                    ).isoformat()
                    
                    if stripe_sub.trial_end:
                        info['trial_end'] = datetime.fromtimestamp(
                            stripe_sub.trial_end
                        ).isoformat()
                        
                except Exception as e:
                    logger.warning(f"Could not retrieve Stripe subscription: {str(e)}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting subscription info: {str(e)}")
            return None
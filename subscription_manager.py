"""
Subscription Manager - Handles credit-based subscriptions, expiry, and renewals
"""
from datetime import datetime, timedelta
from models import db, User, Plan, Subscription, AccountTransaction
from models import UserRole, UserStatus, SubscriptionStatus, PlanTier, TransactionType
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages credit-based subscriptions"""
    
    @staticmethod
    def check_and_update_expired_subscriptions():
        """Check and update expired subscriptions"""
        try:
            now = datetime.utcnow()
            
            # Find all active subscriptions that have expired
            expired_subs = Subscription.query.filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.period_end < now,
                Subscription.stripe_subscription_id.is_(None)  # Only for credit-based subscriptions
            ).all()
            
            updated_count = 0
            for sub in expired_subs:
                # Check if auto-renewal is possible (user has sufficient balance)
                if SubscriptionManager.can_auto_renew(sub):
                    # Attempt auto-renewal
                    success, message = SubscriptionManager.auto_renew_subscription(sub)
                    if success:
                        logger.info(f"Auto-renewed subscription {sub.id} for user {sub.user_id}")
                    else:
                        # Mark as expired if auto-renewal fails
                        sub.status = SubscriptionStatus.CANCELED
                        sub.canceled_at = now
                        logger.info(f"Marked subscription {sub.id} as canceled - auto-renewal failed: {message}")
                else:
                    # Mark as expired
                    sub.status = SubscriptionStatus.CANCELED
                    sub.canceled_at = now
                    logger.info(f"Marked subscription {sub.id} as canceled - expired")
                
                updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                logger.info(f"Updated {updated_count} expired subscriptions")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error checking expired subscriptions: {str(e)}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def can_auto_renew(subscription: Subscription) -> bool:
        """Check if a subscription can be auto-renewed with credits"""
        try:
            user = subscription.user
            plan = subscription.plan
            
            # Check if user has enabled auto-renewal (you could add this as a user preference)
            # For now, we'll assume auto-renewal is enabled by default
            
            # Calculate renewal cost
            if subscription.billing_period == 'weekly':
                cost = plan.price_weekly
            else:
                cost = plan.price_monthly
            
            # Check if user has sufficient balance
            return user.account_balance >= cost
            
        except Exception as e:
            logger.error(f"Error checking auto-renewal eligibility: {str(e)}")
            return False
    
    @staticmethod
    def auto_renew_subscription(subscription: Subscription) -> Tuple[bool, str]:
        """Automatically renew a subscription using account credits"""
        try:
            user = subscription.user
            plan = subscription.plan
            
            # Calculate renewal cost and period
            if subscription.billing_period == 'weekly':
                cost = plan.price_weekly
                days = 7
            else:
                cost = plan.price_monthly
                days = 30
            
            # Double-check balance
            if user.account_balance < cost:
                return False, "Insufficient balance"
            
            # Deduct from balance
            user.account_balance -= cost
            
            # Update subscription dates
            subscription.period_start = datetime.utcnow()
            subscription.period_end = datetime.utcnow() + timedelta(days=days)
            subscription.status = SubscriptionStatus.ACTIVE
            
            # Log the transaction
            transaction = AccountTransaction(
                user_id=user.id,
                type=TransactionType.SUBSCRIPTION_CHARGE,
                amount=-cost,
                balance_after=user.account_balance,
                description=f'{plan.name} - {subscription.billing_period.capitalize()} Auto-Renewal',
                metadata={
                    'plan_tier': plan.tier.value,
                    'billing_interval': subscription.billing_period,
                    'subscription_id': subscription.id,
                    'auto_renewal': True
                },
                status='completed'
            )
            db.session.add(transaction)
            db.session.commit()
            
            return True, "Successfully renewed"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during auto-renewal: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def manual_renew_subscription(user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """Manually renew a user's subscription"""
        try:
            # Get user's most recent subscription
            subscription = Subscription.query.filter_by(
                user_id=user_id
            ).order_by(Subscription.created_at.desc()).first()
            
            if not subscription:
                return False, {'error': 'No subscription found'}
            
            if subscription.status == SubscriptionStatus.ACTIVE:
                # Check if nearing expiry (within 7 days)
                days_until_expiry = (subscription.period_end - datetime.utcnow()).days
                if days_until_expiry > 7:
                    return False, {
                        'error': 'Subscription is still active',
                        'days_remaining': days_until_expiry
                    }
            
            user = db.session.get(User, user_id)
            plan = subscription.plan
            
            # Calculate renewal cost
            if subscription.billing_period == 'weekly':
                cost = plan.price_weekly
                days = 7
            else:
                cost = plan.price_monthly
                days = 30
            
            # Check balance
            if user.account_balance < cost:
                return False, {
                    'error': 'Insufficient balance',
                    'required': cost,
                    'balance': user.account_balance
                }
            
            # Process renewal
            user.account_balance -= cost
            
            # If subscription is expired, start from now
            # If still active, extend from current end date
            if subscription.status != SubscriptionStatus.ACTIVE:
                subscription.period_start = datetime.utcnow()
                subscription.period_end = datetime.utcnow() + timedelta(days=days)
            else:
                # Extend from current end date
                subscription.period_end = subscription.period_end + timedelta(days=days)
            
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.canceled_at = None
            
            # Log transaction
            transaction = AccountTransaction(
                user_id=user.id,
                type=TransactionType.SUBSCRIPTION_CHARGE,
                amount=-cost,
                balance_after=user.account_balance,
                description=f'{plan.name} - {subscription.billing_period.capitalize()} Manual Renewal',
                metadata={
                    'plan_tier': plan.tier.value,
                    'billing_interval': subscription.billing_period,
                    'subscription_id': subscription.id,
                    'manual_renewal': True
                },
                status='completed'
            )
            db.session.add(transaction)
            db.session.commit()
            
            return True, {
                'message': 'Subscription renewed successfully',
                'subscription': {
                    'id': subscription.id,
                    'plan': plan.name,
                    'tier': plan.tier.value,
                    'billing_interval': subscription.billing_period,
                    'period_start': subscription.period_start.isoformat(),
                    'period_end': subscription.period_end.isoformat(),
                    'status': subscription.status.value
                },
                'transaction': {
                    'id': transaction.id,
                    'amount': cost,
                    'balance_after': user.account_balance
                },
                'remaining_balance': user.account_balance
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during manual renewal: {str(e)}")
            return False, {'error': str(e)}
    
    @staticmethod
    def get_subscription_status(user_id: int) -> Dict[str, Any]:
        """Get detailed subscription status for a user"""
        try:
            # Get active subscription
            active_sub = Subscription.query.filter_by(
                user_id=user_id,
                status=SubscriptionStatus.ACTIVE
            ).first()
            
            if not active_sub:
                # Get most recent canceled subscription
                last_sub = Subscription.query.filter_by(
                    user_id=user_id
                ).order_by(Subscription.created_at.desc()).first()
                
                if last_sub:
                    return {
                        'has_active_subscription': False,
                        'status': 'expired',
                        'last_subscription': {
                            'plan': last_sub.plan.name,
                            'tier': last_sub.plan.tier.value,
                            'expired_at': last_sub.period_end.isoformat(),
                            'can_renew': True
                        }
                    }
                else:
                    return {
                        'has_active_subscription': False,
                        'status': 'never_subscribed'
                    }
            
            # Check if nearing expiry
            now = datetime.utcnow()
            days_remaining = (active_sub.period_end - now).days
            hours_remaining = int((active_sub.period_end - now).total_seconds() / 3600)
            
            # Check auto-renewal eligibility
            can_auto_renew = SubscriptionManager.can_auto_renew(active_sub)
            
            return {
                'has_active_subscription': True,
                'status': 'active',
                'subscription': {
                    'id': active_sub.id,
                    'plan': active_sub.plan.name,
                    'tier': active_sub.plan.tier.value,
                    'billing_period': active_sub.billing_period,
                    'period_start': active_sub.period_start.isoformat(),
                    'period_end': active_sub.period_end.isoformat(),
                    'days_remaining': days_remaining,
                    'hours_remaining': hours_remaining,
                    'is_expiring_soon': days_remaining <= 3,
                    'can_auto_renew': can_auto_renew,
                    'is_credit_based': active_sub.stripe_subscription_id is None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription status: {str(e)}")
            return {
                'has_active_subscription': False,
                'status': 'error',
                'error': str(e)
            }
    
    @staticmethod
    def validate_subscription_access(user_id: int, required_tier: PlanTier = None) -> Tuple[bool, str]:
        """Validate if user has active subscription and required tier access"""
        try:
            # First check for expired subscriptions
            SubscriptionManager.check_and_update_expired_subscriptions()
            
            # Get active subscription
            active_sub = Subscription.query.filter_by(
                user_id=user_id,
                status=SubscriptionStatus.ACTIVE
            ).first()
            
            if not active_sub:
                return False, "No active subscription"
            
            # Check if subscription is expired
            if active_sub.period_end < datetime.utcnow():
                # Try auto-renewal
                if SubscriptionManager.can_auto_renew(active_sub):
                    success, message = SubscriptionManager.auto_renew_subscription(active_sub)
                    if success:
                        return SubscriptionManager.validate_subscription_access(user_id, required_tier)
                
                # Mark as expired
                active_sub.status = SubscriptionStatus.CANCELED
                active_sub.canceled_at = datetime.utcnow()
                db.session.commit()
                return False, "Subscription expired"
            
            # Check tier if required
            if required_tier:
                if active_sub.plan.tier.value < required_tier.value:
                    return False, f"Requires {required_tier.value} tier or higher"
            
            return True, "Access granted"
            
        except Exception as e:
            logger.error(f"Error validating subscription access: {str(e)}")
            return False, "Validation error"
    
    @staticmethod
    def cancel_subscription(user_id: int, immediate: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a user's subscription"""
        try:
            # Get active subscription
            active_sub = Subscription.query.filter_by(
                user_id=user_id,
                status=SubscriptionStatus.ACTIVE
            ).first()
            
            if not active_sub:
                return False, {'error': 'No active subscription found'}
            
            # For credit-based subscriptions
            if active_sub.stripe_subscription_id is None:
                if immediate:
                    # Cancel immediately
                    active_sub.status = SubscriptionStatus.CANCELED
                    active_sub.canceled_at = datetime.utcnow()
                    message = "Subscription canceled immediately"
                else:
                    # Mark for cancellation at period end
                    active_sub.canceled_at = datetime.utcnow()
                    message = f"Subscription will be canceled at period end ({active_sub.period_end.isoformat()})"
                
                db.session.commit()
                
                return True, {
                    'message': message,
                    'subscription_id': active_sub.id,
                    'canceled_at': active_sub.canceled_at.isoformat() if active_sub.canceled_at else None,
                    'period_end': active_sub.period_end.isoformat()
                }
            else:
                # For Stripe subscriptions, use Stripe API
                return False, {'error': 'Use Stripe portal for Stripe subscriptions'}
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error canceling subscription: {str(e)}")
            return False, {'error': str(e)}
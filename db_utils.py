"""
Database utility module for the Options Scanner SaaS platform
"""
from datetime import datetime, timedelta
from models import db, User, Plan, Subscription, ApiKey, UsageEvent, AuditLog
from models import UserRole, UserStatus, SubscriptionStatus, PlanTier
import hashlib
import secrets
from sqlalchemy import func, and_, or_
from typing import Optional, Dict, List, Any


class DatabaseManager:
    """Database manager class for handling common database operations"""
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email address"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.session.get(User, user_id)
    
    @staticmethod
    def get_user_by_api_key(api_key: str) -> Optional[User]:
        """Get user by API key"""
        key_hash = ApiKey.hash_key(api_key)
        api_key_obj = ApiKey.query.filter_by(key_hash=key_hash, active=True).first()
        if api_key_obj:
            # Update last_used_at
            api_key_obj.last_used_at = datetime.utcnow()
            db.session.commit()
            return api_key_obj.user
        return None
    
    @staticmethod
    def get_active_subscription(user_id: int) -> Optional[Subscription]:
        """Get user's active subscription"""
        return Subscription.query.filter_by(
            user_id=user_id,
            status=SubscriptionStatus.ACTIVE
        ).first()
    
    @staticmethod
    def get_user_plan(user_id: int) -> Optional[Plan]:
        """Get user's current subscription plan"""
        subscription = DatabaseManager.get_active_subscription(user_id)
        if subscription:
            return subscription.plan
        # Return free plan if no active subscription
        return Plan.query.filter_by(tier=PlanTier.FREE).first()
    
    @staticmethod
    def check_endpoint_access(user_id: int, endpoint: str) -> bool:
        """Check if user has access to a specific endpoint"""
        plan = DatabaseManager.get_user_plan(user_id)
        if not plan:
            return False
        
        # Premium tier has access to all endpoints
        if plan.tier == PlanTier.PREMIUM:
            return True
        
        # Check if endpoint is in allowed list
        allowed_endpoints = plan.allowed_endpoints_json or []
        return endpoint in allowed_endpoints or "*" in allowed_endpoints
    
    @staticmethod
    def check_rate_limit(user_id: int, endpoint: str) -> Dict[str, Any]:
        """Check if user has exceeded rate limits"""
        plan = DatabaseManager.get_user_plan(user_id)
        if not plan:
            return {"allowed": False, "reason": "No active plan"}
        
        quotas = plan.quotas_json or {}
        
        # Check daily scan limit
        if "scans_per_day" in quotas:
            daily_limit = quotas["scans_per_day"]
            if daily_limit > 0:  # -1 means unlimited
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                today_scans = UsageEvent.query.filter(
                    and_(
                        UsageEvent.user_id == user_id,
                        UsageEvent.endpoint == endpoint,
                        UsageEvent.created_at >= today_start
                    )
                ).count()
                
                if today_scans >= daily_limit:
                    return {
                        "allowed": False,
                        "reason": f"Daily limit of {daily_limit} scans exceeded",
                        "limit": daily_limit,
                        "used": today_scans
                    }
        
        # Check API calls per minute
        if "api_calls_per_minute" in quotas:
            minute_limit = quotas["api_calls_per_minute"]
            if minute_limit > 0:  # -1 means unlimited
                one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
                minute_calls = UsageEvent.query.filter(
                    and_(
                        UsageEvent.user_id == user_id,
                        UsageEvent.created_at >= one_minute_ago
                    )
                ).count()
                
                if minute_calls >= minute_limit:
                    return {
                        "allowed": False,
                        "reason": f"Rate limit of {minute_limit} calls/minute exceeded",
                        "limit": minute_limit,
                        "used": minute_calls
                    }
        
        return {"allowed": True, "reason": "Within limits"}
    
    @staticmethod
    def log_usage_event(
        user_id: int,
        endpoint: str,
        units: int = 1,
        symbols_count: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        request_params: Optional[Dict] = None,
        response_status: int = 200,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UsageEvent:
        """Log an API usage event"""
        event = UsageEvent(
            user_id=user_id,
            endpoint=endpoint,
            units=units,
            symbols_count=symbols_count,
            response_time_ms=response_time_ms,
            request_params=request_params,
            response_status=response_status,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(event)
        db.session.commit()
        return event
    
    @staticmethod
    def get_usage_stats(user_id: int, period_days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        start_date = datetime.utcnow() - timedelta(days=period_days)
        
        # Get total usage
        total_usage = db.session.query(
            func.count(UsageEvent.id).label('total_calls'),
            func.sum(UsageEvent.units).label('total_units'),
            func.avg(UsageEvent.response_time_ms).label('avg_response_time')
        ).filter(
            and_(
                UsageEvent.user_id == user_id,
                UsageEvent.created_at >= start_date
            )
        ).first()
        
        # Get usage by endpoint
        endpoint_usage = db.session.query(
            UsageEvent.endpoint,
            func.count(UsageEvent.id).label('calls'),
            func.sum(UsageEvent.units).label('units')
        ).filter(
            and_(
                UsageEvent.user_id == user_id,
                UsageEvent.created_at >= start_date
            )
        ).group_by(UsageEvent.endpoint).all()
        
        # Get daily usage trend
        daily_usage = db.session.query(
            func.date(UsageEvent.created_at).label('date'),
            func.count(UsageEvent.id).label('calls')
        ).filter(
            and_(
                UsageEvent.user_id == user_id,
                UsageEvent.created_at >= start_date
            )
        ).group_by(func.date(UsageEvent.created_at)).all()
        
        return {
            "period_days": period_days,
            "total_calls": total_usage.total_calls or 0,
            "total_units": total_usage.total_units or 0,
            "avg_response_time_ms": float(total_usage.avg_response_time or 0),
            "endpoint_usage": [
                {
                    "endpoint": eu.endpoint,
                    "calls": eu.calls,
                    "units": eu.units or 0
                }
                for eu in endpoint_usage
            ],
            "daily_trend": [
                {
                    "date": du.date.isoformat(),
                    "calls": du.calls
                }
                for du in daily_usage
            ]
        }
    
    @staticmethod
    def create_api_key(user_id: int, name: str) -> str:
        """Create a new API key for a user"""
        api_key_value = ApiKey.generate_key()
        api_key = ApiKey(
            user_id=user_id,
            key_hash=ApiKey.hash_key(api_key_value),
            name=name,
            active=True
        )
        db.session.add(api_key)
        db.session.commit()
        return api_key_value
    
    @staticmethod
    def revoke_api_key(api_key: str) -> bool:
        """Revoke an API key"""
        key_hash = ApiKey.hash_key(api_key)
        api_key_obj = ApiKey.query.filter_by(key_hash=key_hash).first()
        if api_key_obj:
            api_key_obj.active = False
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def log_audit_event(
        actor_user_id: int,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        metadata: Optional[Dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event"""
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(audit_log)
        db.session.commit()
        return audit_log
    
    @staticmethod
    def get_plan_by_code(code: str) -> Optional[Plan]:
        """Get a plan by its code"""
        return Plan.query.filter_by(code=code, active=True).first()
    
    @staticmethod
    def get_all_active_plans() -> List[Plan]:
        """Get all active subscription plans"""
        return Plan.query.filter_by(active=True).order_by(Plan.price_monthly).all()
    
    @staticmethod
    def update_subscription_usage(
        subscription_id: int,
        usage_type: str,
        increment: int = 1
    ) -> None:
        """Update subscription usage counters"""
        subscription = db.session.get(Subscription, subscription_id)
        if subscription:
            # Make a copy of the JSON to ensure SQLAlchemy detects the change
            current_usage = dict(subscription.current_period_usage or {})
            current_usage[usage_type] = current_usage.get(usage_type, 0) + increment
            # Reassign to trigger SQLAlchemy change detection
            subscription.current_period_usage = current_usage
            # Mark the attribute as modified explicitly for JSON fields
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(subscription, 'current_period_usage')
            db.session.commit()
    
    @staticmethod
    def reset_subscription_usage(subscription_id: int) -> None:
        """Reset subscription usage counters (typically at period start)"""
        subscription = db.session.get(Subscription, subscription_id)
        if subscription:
            subscription.current_period_usage = {}
            db.session.commit()


class QueryOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def get_user_with_subscription(user_id: int) -> Optional[User]:
        """Get user with subscription eagerly loaded"""
        return db.session.query(User).options(
            db.joinedload(User.subscriptions).joinedload(Subscription.plan)
        ).filter(User.id == user_id).first()
    
    @staticmethod
    def get_active_users_count() -> int:
        """Get count of active users"""
        return User.query.filter_by(status=UserStatus.ACTIVE).count()
    
    @staticmethod
    def get_subscription_metrics() -> Dict[str, Any]:
        """Get subscription metrics for dashboard"""
        # Count users by plan tier
        plan_counts = db.session.query(
            Plan.tier,
            func.count(Subscription.id).label('count')
        ).join(
            Subscription, Plan.id == Subscription.plan_id
        ).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).group_by(Plan.tier).all()
        
        # Total revenue (monthly equivalent)
        total_revenue = db.session.query(
            func.sum(Plan.price_monthly).label('total')
        ).join(
            Subscription, Plan.id == Subscription.plan_id
        ).filter(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).scalar() or 0
        
        return {
            "plan_distribution": {pc.tier.value: pc.count for pc in plan_counts},
            "total_active_subscriptions": sum(pc.count for pc in plan_counts),
            "monthly_recurring_revenue": float(total_revenue)
        }

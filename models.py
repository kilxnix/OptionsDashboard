"""
Database models for the Options Scanner SaaS platform
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Index, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime
import enum
import hashlib
import secrets


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class UserRole(enum.Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(enum.Enum):
    """User account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    PENDING = "pending"


class SubscriptionStatus(enum.Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class PlanTier(enum.Enum):
    """Subscription plan tiers"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class User(db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    
    # Additional user profile fields
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(255))
    phone = Column(String(50))
    
    # Relationships
    subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')
    api_keys = relationship('ApiKey', back_populates='user', cascade='all, delete-orphan')
    usage_events = relationship('UsageEvent', back_populates='user', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_status', 'email', 'status'),
    )
    
    def __repr__(self):
        return f'<User {self.email}>'


class Plan(db.Model):
    """Subscription plan model"""
    __tablename__ = 'plans'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    tier = Column(Enum(PlanTier), nullable=False)
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float)
    
    # JSON fields for flexible configuration
    quotas_json = Column(JSON, nullable=False, default={})  # {"scans_per_day": 100, "api_calls_per_minute": 60}
    allowed_endpoints_json = Column(JSON, nullable=False, default=[])  # ["/scan", "/explosive-scan"]
    features_json = Column(JSON, default={})  # {"priority_support": true, "custom_alerts": false}
    
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Stripe product and price IDs
    stripe_product_id = Column(String(255), index=True)
    stripe_price_monthly_id = Column(String(255))
    stripe_price_yearly_id = Column(String(255))
    
    # Relationships
    subscriptions = relationship('Subscription', back_populates='plan')
    
    # Indexes
    __table_args__ = (
        Index('idx_plan_tier_active', 'tier', 'active'),
    )
    
    def __repr__(self):
        return f'<Plan {self.name} ({self.tier.value})>'


class Subscription(db.Model):
    """User subscription model"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey('plans.id'), nullable=False, index=True)
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    status = Column(Enum(SubscriptionStatus), nullable=False)
    
    # Billing period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Usage tracking
    current_period_usage = Column(JSON, default={})  # {"scans": 45, "api_calls": 1200}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    canceled_at = Column(DateTime)
    
    # Trial information
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    
    # Relationships
    user = relationship('User', back_populates='subscriptions')
    plan = relationship('Plan', back_populates='subscriptions')
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_user_status', 'user_id', 'status'),
        Index('idx_subscription_period', 'period_start', 'period_end'),
    )
    
    def __repr__(self):
        return f'<Subscription user={self.user_id} plan={self.plan_id} status={self.status.value}>'


class ApiKey(db.Model):
    """API key for user authentication"""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Status
    active = Column(Boolean, default=True, nullable=False)
    
    # Rate limiting
    rate_limit_override = Column(JSON)  # {"requests_per_minute": 100}
    
    # Relationships
    user = relationship('User', back_populates='api_keys')
    
    # Indexes
    __table_args__ = (
        Index('idx_apikey_user_active', 'user_id', 'active'),
    )
    
    @staticmethod
    def generate_key():
        """Generate a new API key"""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key):
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def __repr__(self):
        return f'<ApiKey {self.name} user={self.user_id}>'


class UsageEvent(db.Model):
    """Track API usage events"""
    __tablename__ = 'usage_events'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    
    # Usage metrics
    units = Column(Integer, default=1)  # Number of units consumed
    symbols_count = Column(Integer)  # Number of symbols processed
    response_time_ms = Column(Integer)  # Response time in milliseconds
    
    # Request details
    request_params = Column(JSON)  # Store request parameters
    response_status = Column(Integer)  # HTTP response status
    error_message = Column(Text)  # Error message if any
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # IP and user agent for security
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(String(500))
    
    # Relationships
    user = relationship('User', back_populates='usage_events')
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_user_endpoint_time', 'user_id', 'endpoint', 'created_at'),
        Index('idx_usage_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<UsageEvent user={self.user_id} endpoint={self.endpoint}>'


class AuditLog(db.Model):
    """Audit log for tracking admin actions"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    
    # Target of the action
    target_type = Column(String(50))  # 'user', 'subscription', 'plan', etc.
    target_id = Column(Integer)
    
    # Additional data
    metadata_json = Column(JSON)  # Store additional context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    actor = relationship('User', foreign_keys=[actor_user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_actor_action', 'actor_user_id', 'action'),
        Index('idx_audit_target', 'target_type', 'target_id'),
        Index('idx_audit_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f'<AuditLog actor={self.actor_user_id} action={self.action}>'


# Additional utility tables

class WebhookEvent(db.Model):
    """Store webhook events from Stripe and other services"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    source = Column(String(50), nullable=False)  # 'stripe', 'sendgrid', etc.
    event_type = Column(String(100), nullable=False)
    event_id = Column(String(255), unique=True, index=True)
    
    # Payload
    payload = Column(JSON, nullable=False)
    
    # Processing
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_webhook_source_type', 'source', 'event_type'),
        Index('idx_webhook_processed', 'processed', 'created_at'),
    )
    
    def __repr__(self):
        return f'<WebhookEvent {self.source}:{self.event_type}>'


class FeatureFlag(db.Model):
    """Feature flags for gradual rollout and A/B testing"""
    __tablename__ = 'feature_flags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=False)
    
    # Targeting
    user_percentage = Column(Integer, default=0)  # 0-100
    user_whitelist = Column(JSON, default=[])  # List of user IDs
    plan_whitelist = Column(JSON, default=[])  # List of plan tiers
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FeatureFlag {self.name} enabled={self.enabled}>'
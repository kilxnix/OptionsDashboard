"""
Comprehensive database testing script
"""
from datetime import datetime, timedelta
from models import db, User, Plan, Subscription, ApiKey, UsageEvent, AuditLog
from models import UserRole, UserStatus, SubscriptionStatus, PlanTier
from db_utils import DatabaseManager, QueryOptimizer
from flask import Flask
import os
import json

def create_app():
    """Create Flask app for testing"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app

def test_user_operations():
    """Test user-related database operations"""
    print("\n=== Testing User Operations ===")
    
    # Create a test user
    test_email = f"test_{datetime.now().timestamp()}@example.com"
    test_user = User(
        email=test_email,
        password_hash="pbkdf2:sha256:600000$test$abcdef123456",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        first_name="Test",
        last_name="User"
    )
    db.session.add(test_user)
    db.session.commit()
    print(f"✓ Created user: {test_user.email} (ID: {test_user.id})")
    
    # Retrieve user by email
    retrieved_user = DatabaseManager.get_user_by_email(test_email)
    assert retrieved_user is not None
    assert retrieved_user.email == test_email
    print(f"✓ Retrieved user by email")
    
    # Retrieve user by ID
    user_by_id = DatabaseManager.get_user_by_id(test_user.id)
    assert user_by_id is not None
    assert user_by_id.id == test_user.id
    print(f"✓ Retrieved user by ID")
    
    return test_user

def test_plan_operations():
    """Test plan-related database operations"""
    print("\n=== Testing Plan Operations ===")
    
    # Get all active plans
    plans = DatabaseManager.get_all_active_plans()
    assert len(plans) > 0
    print(f"✓ Found {len(plans)} active plans")
    
    # Get specific plan by code
    free_plan = DatabaseManager.get_plan_by_code("free")
    assert free_plan is not None
    assert free_plan.tier == PlanTier.FREE
    print(f"✓ Retrieved Free plan: {free_plan.name}")
    
    premium_plan = DatabaseManager.get_plan_by_code("premium")
    assert premium_plan is not None
    assert premium_plan.tier == PlanTier.PREMIUM
    print(f"✓ Retrieved Premium plan: {premium_plan.name}")
    
    # Check plan quotas
    assert "scans_per_day" in free_plan.quotas_json
    assert free_plan.quotas_json["scans_per_day"] == 10
    print(f"✓ Free plan daily scan limit: {free_plan.quotas_json['scans_per_day']}")
    
    return plans

def test_api_key_operations(user):
    """Test API key operations"""
    print("\n=== Testing API Key Operations ===")
    
    # Create API key
    api_key_value = DatabaseManager.create_api_key(user.id, "Test API Key")
    assert api_key_value.startswith("sk_")
    print(f"✓ Created API key: {api_key_value[:12]}...")
    
    # Get user by API key
    user_from_key = DatabaseManager.get_user_by_api_key(api_key_value)
    assert user_from_key is not None
    assert user_from_key.id == user.id
    print(f"✓ Retrieved user by API key")
    
    # Check that last_used_at was updated
    api_key_obj = ApiKey.query.filter_by(user_id=user.id).first()
    assert api_key_obj.last_used_at is not None
    print(f"✓ API key last_used_at updated")
    
    # Revoke API key
    revoked = DatabaseManager.revoke_api_key(api_key_value)
    assert revoked == True
    print(f"✓ Revoked API key")
    
    # Verify revoked key doesn't work
    user_from_revoked = DatabaseManager.get_user_by_api_key(api_key_value)
    assert user_from_revoked is None
    print(f"✓ Revoked key no longer authenticates")
    
    return api_key_value

def test_subscription_operations(user):
    """Test subscription operations"""
    print("\n=== Testing Subscription Operations ===")
    
    # Get premium plan
    premium_plan = DatabaseManager.get_plan_by_code("premium")
    
    # Create subscription
    subscription = Subscription(
        user_id=user.id,
        plan_id=premium_plan.id,
        status=SubscriptionStatus.ACTIVE,
        period_start=datetime.utcnow(),
        period_end=datetime.utcnow() + timedelta(days=30),
        current_period_usage={"scans": 0, "api_calls": 0}
    )
    db.session.add(subscription)
    db.session.commit()
    print(f"✓ Created subscription for user {user.id}")
    
    # Get active subscription
    active_sub = DatabaseManager.get_active_subscription(user.id)
    assert active_sub is not None
    assert active_sub.plan_id == premium_plan.id
    print(f"✓ Retrieved active subscription")
    
    # Get user's plan
    user_plan = DatabaseManager.get_user_plan(user.id)
    assert user_plan is not None
    assert user_plan.tier == PlanTier.PREMIUM
    print(f"✓ User has {user_plan.name} plan")
    
    # Update subscription usage
    DatabaseManager.update_subscription_usage(subscription.id, "scans", 5)
    DatabaseManager.update_subscription_usage(subscription.id, "api_calls", 20)
    
    # Verify usage was updated
    updated_sub = db.session.get(Subscription, subscription.id)
    if not updated_sub:
        raise AssertionError(f"Could not retrieve subscription with id {subscription.id}")
    
    usage = updated_sub.current_period_usage
    if usage is None:
        raise AssertionError("current_period_usage is None")
    
    if "scans" not in usage:
        raise AssertionError(f"'scans' not in usage. Current usage: {usage}")
    
    if usage["scans"] != 5:
        raise AssertionError(f"Expected scans=5, got {usage['scans']}. Full usage: {usage}")
    
    if usage["api_calls"] != 20:
        raise AssertionError(f"Expected api_calls=20, got {usage['api_calls']}. Full usage: {usage}")
    
    print(f"✓ Updated subscription usage: {usage}")
    
    # Reset usage
    DatabaseManager.reset_subscription_usage(subscription.id)
    reset_sub = db.session.get(Subscription, subscription.id)
    assert reset_sub.current_period_usage == {}
    print(f"✓ Reset subscription usage")
    
    return subscription

def test_endpoint_access(user):
    """Test endpoint access control"""
    print("\n=== Testing Endpoint Access Control ===")
    
    # Test premium user access
    has_scan_access = DatabaseManager.check_endpoint_access(user.id, "/scan")
    assert has_scan_access == True
    print(f"✓ Premium user has access to /scan")
    
    has_explosive_access = DatabaseManager.check_endpoint_access(user.id, "/explosive-scan")
    assert has_explosive_access == True
    print(f"✓ Premium user has access to /explosive-scan")
    
    has_jpm_access = DatabaseManager.check_endpoint_access(user.id, "/jpm-explosion-hunter")
    assert has_jpm_access == True
    print(f"✓ Premium user has access to /jpm-explosion-hunter")
    
    # Create a free user
    free_user = User(
        email=f"free_{datetime.now().timestamp()}@example.com",
        password_hash="pbkdf2:sha256:600000$free$123456",
        role=UserRole.USER,
        status=UserStatus.ACTIVE
    )
    db.session.add(free_user)
    db.session.commit()
    
    # Free user should only have limited access
    free_scan_access = DatabaseManager.check_endpoint_access(free_user.id, "/scan")
    assert free_scan_access == True
    print(f"✓ Free user has access to /scan")
    
    free_explosive_access = DatabaseManager.check_endpoint_access(free_user.id, "/explosive-scan")
    assert free_explosive_access == False
    print(f"✓ Free user blocked from /explosive-scan")

def test_usage_tracking(user):
    """Test usage event tracking"""
    print("\n=== Testing Usage Tracking ===")
    
    # Log several usage events
    for i in range(5):
        DatabaseManager.log_usage_event(
            user_id=user.id,
            endpoint="/scan",
            units=1,
            symbols_count=10,
            response_time_ms=250 + i * 50,
            request_params={"min_delta": 0.25, "max_delta": 0.68},
            response_status=200,
            ip_address="192.168.1.1",
            user_agent="TestClient/1.0"
        )
    print(f"✓ Logged 5 usage events")
    
    # Log an error event
    DatabaseManager.log_usage_event(
        user_id=user.id,
        endpoint="/explosive-scan",
        units=1,
        response_status=500,
        error_message="Test error",
        ip_address="192.168.1.1"
    )
    print(f"✓ Logged error event")
    
    # Get usage statistics
    stats = DatabaseManager.get_usage_stats(user.id, period_days=1)
    assert stats["total_calls"] == 6
    assert stats["total_units"] == 6
    assert len(stats["endpoint_usage"]) == 2
    print(f"✓ Usage stats: {stats['total_calls']} calls, avg response time: {stats['avg_response_time_ms']:.0f}ms")
    
    # Test rate limiting
    rate_check = DatabaseManager.check_rate_limit(user.id, "/scan")
    assert rate_check["allowed"] == True
    print(f"✓ Rate limit check passed: {rate_check['reason']}")

def test_audit_logging(user):
    """Test audit logging"""
    print("\n=== Testing Audit Logging ===")
    
    # Log various audit events
    DatabaseManager.log_audit_event(
        actor_user_id=user.id,
        action="user.login",
        success=True,
        ip_address="192.168.1.1"
    )
    print(f"✓ Logged login event")
    
    DatabaseManager.log_audit_event(
        actor_user_id=user.id,
        action="api_key.create",
        target_type="api_key",
        target_id=1,
        metadata={"key_name": "Test Key"},
        success=True
    )
    print(f"✓ Logged API key creation")
    
    DatabaseManager.log_audit_event(
        actor_user_id=user.id,
        action="subscription.upgrade",
        target_type="subscription",
        target_id=1,
        metadata={"from_plan": "basic", "to_plan": "premium"},
        success=False,
        error_message="Payment failed"
    )
    print(f"✓ Logged failed subscription upgrade")
    
    # Verify audit logs exist
    audit_logs = AuditLog.query.filter_by(actor_user_id=user.id).all()
    assert len(audit_logs) >= 3
    print(f"✓ Found {len(audit_logs)} audit log entries")

def test_query_optimizations():
    """Test query optimization utilities"""
    print("\n=== Testing Query Optimizations ===")
    
    # Get active users count
    active_count = QueryOptimizer.get_active_users_count()
    assert active_count >= 0
    print(f"✓ Active users count: {active_count}")
    
    # Get subscription metrics
    metrics = QueryOptimizer.get_subscription_metrics()
    assert "monthly_recurring_revenue" in metrics
    assert "total_active_subscriptions" in metrics
    print(f"✓ Subscription metrics:")
    print(f"  - Active subscriptions: {metrics['total_active_subscriptions']}")
    print(f"  - MRR: ${metrics['monthly_recurring_revenue']:.2f}")
    if metrics['plan_distribution']:
        print(f"  - Plan distribution: {metrics['plan_distribution']}")

def run_all_tests():
    """Run all database tests"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*50)
        print("RUNNING DATABASE TESTS")
        print("="*50)
        
        try:
            # Run test suites
            test_user = test_user_operations()
            test_plan_operations()
            test_api_key_operations(test_user)
            subscription = test_subscription_operations(test_user)
            test_endpoint_access(test_user)
            test_usage_tracking(test_user)
            test_audit_logging(test_user)
            test_query_optimizations()
            
            print("\n" + "="*50)
            print("✅ ALL DATABASE TESTS PASSED!")
            print("="*50)
            
            # Display database summary
            print("\n📊 Database Summary:")
            print(f"  - Users: {User.query.count()}")
            print(f"  - Plans: {Plan.query.count()}")
            print(f"  - Subscriptions: {Subscription.query.count()}")
            print(f"  - API Keys: {ApiKey.query.count()}")
            print(f"  - Usage Events: {UsageEvent.query.count()}")
            print(f"  - Audit Logs: {AuditLog.query.count()}")
            
            return True
            
        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            return False
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
"""
Authentication module for the Options Scanner SaaS platform
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app
from models import db, User, ApiKey, UsageEvent, UserRole, UserStatus
from db_utils import DatabaseManager
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRY = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRY = timedelta(days=30)

# Cache for revoked tokens (in production, use Redis)
revoked_tokens = set()


class AuthManager:
    """Handles authentication and authorization operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def generate_access_token(user_id: int, email: str, role: str = 'user') -> str:
        """Generate a JWT access token"""
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'type': 'access',
            'exp': datetime.now(timezone.utc) + JWT_ACCESS_TOKEN_EXPIRY,
            'iat': datetime.now(timezone.utc)
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def generate_refresh_token(user_id: int) -> str:
        """Generate a JWT refresh token"""
        payload = {
            'user_id': user_id,
            'type': 'refresh',
            'exp': datetime.now(timezone.utc) + JWT_REFRESH_TOKEN_EXPIRY,
            'iat': datetime.now(timezone.utc)
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token"""
        try:
            # Check if token is revoked
            if token in revoked_tokens:
                return None
            
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def revoke_token(token: str):
        """Add token to revoked list"""
        revoked_tokens.add(token)
    
    @staticmethod
    def get_current_user_from_token() -> Optional[User]:
        """Get current user from JWT token in request headers"""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        payload = AuthManager.decode_token(token)
        
        if not payload or payload.get('type') != 'access':
            return None
        
        user_id = payload.get('user_id')
        if not user_id:
            return None
        
        return DatabaseManager.get_user_by_id(user_id)
    
    @staticmethod
    def get_current_user_from_api_key() -> Optional[User]:
        """Get current user from API key in request headers"""
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return None
        
        return DatabaseManager.get_user_by_api_key(api_key)
    
    @staticmethod
    def get_current_user() -> Optional[User]:
        """Get current user from either JWT token or API key"""
        # Try JWT token first
        user = AuthManager.get_current_user_from_token()
        if user:
            return user
        
        # Try API key
        return AuthManager.get_current_user_from_api_key()


# Decorators

def require_auth(f):
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = AuthManager.get_current_user()
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        
        if user.status != UserStatus.ACTIVE:
            return jsonify({
                'status': 'error',
                'message': f'Account is {user.status.value}'
            }), 403
        
        # Log API usage
        endpoint = request.path
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        
        usage_event = UsageEvent(
            user_id=user.id,
            endpoint=endpoint,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(usage_event)
        db.session.commit()
        
        # Add user to request context
        request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_admin(f):
    """Decorator to require admin role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = AuthManager.get_current_user()
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        
        # Add user to request context
        request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_tier(allowed_tiers):
    """Decorator to require specific subscription tiers for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = AuthManager.get_current_user()
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required'
                }), 401
            
            # Get user's current plan
            plan = DatabaseManager.get_user_plan(user.id)
            if not plan:
                return jsonify({
                    'status': 'error',
                    'message': 'No active subscription'
                }), 403
            
            # Check if user's tier is allowed
            if plan.tier not in allowed_tiers:
                return jsonify({
                    'status': 'error',
                    'message': f'This feature requires {", ".join([t.value for t in allowed_tiers])} tier',
                    'current_tier': plan.tier.value
                }), 403
            
            # Check rate limits
            rate_limit_check = DatabaseManager.check_rate_limit(user.id, request.path)
            if not rate_limit_check['allowed']:
                return jsonify({
                    'status': 'error',
                    'message': rate_limit_check['reason'],
                    'limit': rate_limit_check.get('limit'),
                    'used': rate_limit_check.get('used')
                }), 429
            
            # Add user and plan to request context
            request.current_user = user
            request.current_plan = plan
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def rate_limit(max_requests_per_minute=60):
    """Decorator to apply rate limiting to a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user or IP address for rate limiting
            user = AuthManager.get_current_user()
            if user:
                identifier = f"user:{user.id}"
            else:
                identifier = f"ip:{request.remote_addr}"
            
            # Check rate limit (simplified - in production use Redis)
            # For now, we'll rely on the database rate limiting in require_tier
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Validation helpers

def validate_email(email: str) -> bool:
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
"""
Security utilities for Discord bot API
"""

import os
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class JWTClaims(BaseModel):
    sub: str  # Subject (service ID)
    scope: List[str]  # Permissions
    exp: datetime  # Expiration
    iat: datetime  # Issued at


def create_service_jwt(service_id: str, scopes: List[str]) -> str:
    """Create a JWT token for service-to-service authentication"""
    now = datetime.utcnow()
    claims = {
        "sub": service_id,
        "scope": scopes,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": now
    }
    
    token = jwt.encode(claims, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(authorization_header: str) -> JWTClaims:
    """Verify JWT token from Authorization header"""
    try:
        if not authorization_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization_header.split("Bearer ")[1]
        
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        return JWTClaims(
            sub=payload["sub"],
            scope=payload.get("scope", []),
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"])
        )
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except KeyError as e:
        logger.warning(f"Missing required claim in JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )


def create_webhook_signature(payload: str, secret: str) -> str:
    """Create HMAC signature for webhook payloads"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected_signature = create_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected_signature)


class SecurityConfig:
    """Security configuration and utilities"""
    
    @staticmethod
    def get_platform_scopes() -> List[str]:
        """Get standard scopes for platform services"""
        return [
            "bot:configure",
            "bot:read",
            "faq:sync",
            "events:receive"
        ]
    
    @staticmethod
    def get_bot_scopes() -> List[str]:
        """Get standard scopes for bot services"""
        return [
            "platform:webhook",
            "faq:read",
            "schedule:read"
        ]
    
    @staticmethod
    def validate_discord_permissions(permissions: int) -> bool:
        """Validate that bot has required Discord permissions"""
        required_permissions = [
            0x800,      # Send Messages
            0x2000,     # Manage Messages
            0x400000,   # Manage Threads
            0x10000,    # Read Message History
            0x20000     # Mention Everyone (optional)
        ]
        
        for perm in required_permissions[:-1]:  # Exclude optional ones
            if not (permissions & perm):
                return False
        
        return True
    
    @staticmethod
    def generate_webhook_secret() -> str:
        """Generate a secure webhook secret"""
        import secrets
        return secrets.token_urlsafe(32)


def require_scopes(required_scopes: List[str]):
    """Decorator to require specific scopes"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be used with dependency injection in FastAPI
            # Implementation depends on how you want to pass the claims
            pass
        return wrapper
    return decorator


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self._requests = {}
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.utcnow()
        
        if key not in self._requests:
            self._requests[key] = []
        
        # Clean old requests
        cutoff = now - timedelta(seconds=window_seconds)
        self._requests[key] = [
            req_time for req_time in self._requests[key] 
            if req_time > cutoff
        ]
        
        # Check if under limit
        if len(self._requests[key]) >= max_requests:
            return False
        
        # Add current request
        self._requests[key].append(now)
        return True
    
    def cleanup(self, max_age_hours: int = 1):
        """Clean up old rate limit entries"""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        keys_to_remove = []
        for key, requests in self._requests.items():
            self._requests[key] = [
                req_time for req_time in requests 
                if req_time > cutoff
            ]
            if not self._requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()

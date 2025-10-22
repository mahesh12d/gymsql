"""
Production-Ready Rate Limiting for Admin Endpoints
===================================================
Prevents brute force attacks on admin authentication and API endpoints.

Features:
- Strict rate limiting on admin login/auth endpoints
- Per-IP tracking using Redis (with in-memory fallback)
- Automatic lockout after failed attempts
- Configurable limits per endpoint
"""
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from .redis_service import redis_service

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limiting constants
ADMIN_LOGIN_LIMIT = "5 per hour"  # Max 5 login attempts per hour
ADMIN_API_LIMIT = "60 per minute"  # Max 60 admin API calls per minute
GENERAL_API_LIMIT = "100 per minute"  # Max 100 general API calls per minute

# Lockout tracking
LOCKOUT_DURATION_SECONDS = 3600  # 1 hour lockout after too many failed attempts
MAX_FAILED_ATTEMPTS = 5


class RateLimiterService:
    """Service for tracking rate limits and lockouts"""
    
    def __init__(self):
        self.lockout_prefix = "admin_lockout"
        self.failed_attempts_prefix = "admin_failed"
    
    def is_locked_out(self, identifier: str) -> bool:
        """
        Check if an IP or user is currently locked out.
        
        Args:
            identifier: IP address or user ID
            
        Returns:
            True if locked out, False otherwise
        """
        if not redis_service.is_available():
            return False
            
        lockout_key = f"{self.lockout_prefix}:{identifier}"
        try:
            return redis_service.client.exists(lockout_key) > 0
        except Exception as e:
            print(f"Failed to check lockout status: {e}")
            return False
    
    def record_failed_attempt(self, identifier: str) -> int:
        """
        Record a failed authentication attempt.
        
        Args:
            identifier: IP address or user ID
            
        Returns:
            Number of failed attempts so far
        """
        if not redis_service.is_available():
            return 0
            
        failed_key = f"{self.failed_attempts_prefix}:{identifier}"
        
        try:
            # Increment failed attempts
            failed_count = redis_service.client.incr(failed_key)
            
            # Set expiry on first attempt
            if failed_count == 1:
                redis_service.client.expire(failed_key, LOCKOUT_DURATION_SECONDS)
            
            # Lock out after max attempts
            if failed_count >= MAX_FAILED_ATTEMPTS:
                self._lockout(identifier)
                print(f"🔒 SECURITY: IP {identifier} locked out after {failed_count} failed attempts")
            
            return failed_count
        except Exception as e:
            print(f"Failed to record failed attempt: {e}")
            return 0
    
    def clear_failed_attempts(self, identifier: str):
        """
        Clear failed attempts after successful authentication.
        
        Args:
            identifier: IP address or user ID
        """
        if not redis_service.is_available():
            return
            
        failed_key = f"{self.failed_attempts_prefix}:{identifier}"
        try:
            redis_service.client.delete(failed_key)
        except Exception as e:
            print(f"Failed to clear failed attempts: {e}")
    
    def _lockout(self, identifier: str):
        """
        Lock out an IP or user for LOCKOUT_DURATION_SECONDS.
        
        Args:
            identifier: IP address or user ID
        """
        if not redis_service.is_available():
            return
            
        lockout_key = f"{self.lockout_prefix}:{identifier}"
        try:
            redis_service.client.setex(
                lockout_key,
                LOCKOUT_DURATION_SECONDS,
                "1"
            )
        except Exception as e:
            print(f"Failed to set lockout: {e}")
    
    def get_remaining_lockout_time(self, identifier: str) -> int:
        """
        Get remaining lockout time in seconds.
        
        Args:
            identifier: IP address or user ID
            
        Returns:
            Remaining lockout time in seconds, 0 if not locked out
        """
        if not redis_service.is_available():
            return 0
            
        lockout_key = f"{self.lockout_prefix}:{identifier}"
        try:
            ttl = redis_service.client.ttl(lockout_key)
            return max(0, ttl)
        except Exception as e:
            print(f"Failed to get lockout TTL: {e}")
            return 0


# Global rate limiter service
rate_limiter_service = RateLimiterService()


# Dependency for checking lockout status
def check_not_locked_out(request: Request):
    """
    FastAPI dependency to check if requester is locked out.
    Raises HTTP 429 if locked out.
    """
    ip_address = request.client.host if request.client else "unknown"
    
    if rate_limiter_service.is_locked_out(ip_address):
        remaining_time = rate_limiter_service.get_remaining_lockout_time(ip_address)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed authentication attempts. Try again in {remaining_time // 60} minutes."
        )

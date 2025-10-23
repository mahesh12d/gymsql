"""
Production-Ready Rate Limiting for Admin Endpoints (PostgreSQL-based)
======================================================================
Prevents brute force attacks on admin authentication without Redis.

Features:
- Strict rate limiting on admin login/auth endpoints
- Per-IP tracking using PostgreSQL
- Automatic lockout after failed attempts
- Automatic cleanup of expired records
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import delete

# Rate limiting constants
LOCKOUT_DURATION_SECONDS = 3600  # 1 hour lockout after too many failed attempts
MAX_FAILED_ATTEMPTS = 5


class RateLimiterService:
    """PostgreSQL-based rate limiting service"""
    
    def is_locked_out(self, identifier: str, db: Session) -> bool:
        """
        Check if an IP or user is currently locked out.
        
        Args:
            identifier: IP address or user ID
            db: Database session
            
        Returns:
            True if locked out, False otherwise
        """
        from .models import AdminLockout
        
        try:
            # Clean up expired lockouts first
            self._cleanup_expired_lockouts(db)
            
            # Check if lockout exists and is still valid
            lockout = db.query(AdminLockout).filter(
                AdminLockout.identifier == identifier,
                AdminLockout.expires_at > datetime.utcnow()
            ).first()
            
            return lockout is not None
        except Exception as e:
            print(f"Failed to check lockout status: {e}")
            return False
    
    def record_failed_attempt(self, identifier: str, db: Session) -> int:
        """
        Record a failed authentication attempt.
        
        Args:
            identifier: IP address or user ID
            db: Database session
            
        Returns:
            Number of failed attempts so far
        """
        from .models import AdminFailedAttempt
        import uuid
        
        try:
            # Clean up expired attempts first
            self._cleanup_expired_attempts(db)
            
            # Find or create failed attempt record
            attempt = db.query(AdminFailedAttempt).filter(
                AdminFailedAttempt.identifier == identifier,
                AdminFailedAttempt.expires_at > datetime.utcnow()
            ).first()
            
            if attempt:
                # Increment existing record
                attempt.attempt_count += 1
                attempt.last_attempt_at = datetime.utcnow()
            else:
                # Create new record
                attempt = AdminFailedAttempt(
                    id=str(uuid.uuid4()),
                    identifier=identifier,
                    attempt_count=1,
                    first_attempt_at=datetime.utcnow(),
                    last_attempt_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(seconds=LOCKOUT_DURATION_SECONDS)
                )
                db.add(attempt)
            
            db.commit()
            
            # Lock out after max attempts
            if attempt.attempt_count >= MAX_FAILED_ATTEMPTS:
                self._lockout(identifier, db)
                print(f"🔒 SECURITY: IP {identifier} locked out after {attempt.attempt_count} failed attempts")
            
            return attempt.attempt_count
        except Exception as e:
            db.rollback()
            print(f"Failed to record failed attempt: {e}")
            return 0
    
    def clear_failed_attempts(self, identifier: str, db: Session):
        """
        Clear failed attempts after successful authentication.
        
        Args:
            identifier: IP address or user ID
            db: Database session
        """
        from .models import AdminFailedAttempt
        
        try:
            db.query(AdminFailedAttempt).filter(
                AdminFailedAttempt.identifier == identifier
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Failed to clear failed attempts: {e}")
    
    def _lockout(self, identifier: str, db: Session):
        """
        Lock out an IP or user for LOCKOUT_DURATION_SECONDS.
        
        Args:
            identifier: IP address or user ID
            db: Database session
        """
        from .models import AdminLockout
        import uuid
        
        try:
            # Check if lockout already exists
            existing = db.query(AdminLockout).filter(
                AdminLockout.identifier == identifier
            ).first()
            
            if existing:
                # Update existing lockout
                existing.locked_at = datetime.utcnow()
                existing.expires_at = datetime.utcnow() + timedelta(seconds=LOCKOUT_DURATION_SECONDS)
                existing.reason = f"Too many failed attempts (max: {MAX_FAILED_ATTEMPTS})"
            else:
                # Create new lockout
                lockout = AdminLockout(
                    id=str(uuid.uuid4()),
                    identifier=identifier,
                    locked_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(seconds=LOCKOUT_DURATION_SECONDS),
                    reason=f"Too many failed attempts (max: {MAX_FAILED_ATTEMPTS})"
                )
                db.add(lockout)
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Failed to set lockout: {e}")
    
    def get_remaining_lockout_time(self, identifier: str, db: Session) -> int:
        """
        Get remaining lockout time in seconds.
        
        Args:
            identifier: IP address or user ID
            db: Database session
            
        Returns:
            Remaining lockout time in seconds, 0 if not locked out
        """
        from .models import AdminLockout
        
        try:
            lockout = db.query(AdminLockout).filter(
                AdminLockout.identifier == identifier,
                AdminLockout.expires_at > datetime.utcnow()
            ).first()
            
            if lockout:
                remaining = (lockout.expires_at - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
            return 0
        except Exception as e:
            print(f"Failed to get lockout TTL: {e}")
            return 0
    
    def _cleanup_expired_attempts(self, db: Session):
        """Clean up expired failed attempt records"""
        from .models import AdminFailedAttempt
        
        try:
            db.query(AdminFailedAttempt).filter(
                AdminFailedAttempt.expires_at < datetime.utcnow()
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Failed to cleanup expired attempts: {e}")
    
    def _cleanup_expired_lockouts(self, db: Session):
        """Clean up expired lockout records"""
        from .models import AdminLockout
        
        try:
            db.query(AdminLockout).filter(
                AdminLockout.expires_at < datetime.utcnow()
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Failed to cleanup expired lockouts: {e}")


# Global rate limiter service
rate_limiter_service = RateLimiterService()


# Dependency for checking lockout status
def check_not_locked_out(request: Request, db: Session):
    """
    FastAPI dependency to check if requester is locked out.
    Raises HTTP 429 if locked out.
    
    Args:
        request: FastAPI Request
        db: Database session (injected)
    """
    ip_address = request.client.host if request.client else "unknown"
    
    if rate_limiter_service.is_locked_out(ip_address, db):
        remaining_time = rate_limiter_service.get_remaining_lockout_time(ip_address, db)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed authentication attempts. Try again in {remaining_time // 60} minutes."
        )

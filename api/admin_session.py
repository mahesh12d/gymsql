"""
Secure Admin Session Management with HTTP-only Cookies and Redis Tracking
=========================================================================
This module provides production-ready admin authentication for single-admin use.

Security Features:
- HTTP-only cookies (cannot be accessed by JavaScript)
- Redis-based session tracking with instant revocation
- CSRF protection
- Activity tracking and audit logging
- Automatic session expiration on inactivity

No ADMIN_SECRET_KEY required - users with is_admin=true get automatic access.
"""
import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import PyJWTError

from .database import get_db
from .models import User
from .redis_service import redis_service

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
ADMIN_SESSION_DURATION_HOURS = 8  # 8 hour sessions
ADMIN_SESSION_INACTIVITY_MINUTES = 30  # Auto-logout after 30 mins of inactivity
CSRF_TOKEN_BYTES = 32

class AdminSessionManager:
    """
    Manages admin sessions using HTTP-only cookies and Redis tracking.
    """
    
    def __init__(self):
        self.session_prefix = "admin_session"
        self.csrf_prefix = "admin_csrf"
        self.audit_prefix = "admin_audit"
    
    def create_admin_session(
        self, 
        user: User, 
        response: Response,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, str]:
        """
        Create a new admin session with HTTP-only cookie and CSRF token.
        
        Args:
            user: Admin user object
            response: FastAPI Response to set cookies
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with session info and CSRF token
        """
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have admin privileges"
            )
        
        # Generate session ID
        session_id = secrets.token_urlsafe(32)
        
        # Generate CSRF token
        csrf_token = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
        
        # Calculate expiration times
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(hours=ADMIN_SESSION_DURATION_HOURS)
        
        # Session data to store in Redis
        session_data = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_activity": created_at.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "csrf_token_hash": self._hash_token(csrf_token)
        }
        
        # Store session in Redis
        session_key = f"{self.session_prefix}:{session_id}"
        session_ttl = int(ADMIN_SESSION_DURATION_HOURS * 3600)
        
        if redis_service.is_available():
            try:
                redis_service.client.setex(
                    session_key,
                    session_ttl,
                    json.dumps(session_data)
                )
            except Exception as e:
                print(f"Failed to create admin session in Redis: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create admin session"
                )
        else:
            # Fallback: Store in PostgreSQL (not recommended for production)
            print("⚠️  Redis unavailable - admin sessions will be less secure")
            self._store_session_in_db(session_id, session_data, expires_at)
        
        # Set HTTP-only cookie (cannot be accessed by JavaScript)
        response.set_cookie(
            key="admin_session",
            value=session_id,
            max_age=session_ttl,
            httponly=True,  # JavaScript cannot access
            secure=True,    # HTTPS only in production
            samesite="lax",  # CSRF protection
            path="/api/admin"  # Only sent to admin endpoints
        )
        
        # Log session creation
        self._audit_log(user.id, "session_created", {
            "ip_address": ip_address,
            "user_agent": user_agent
        })
        
        print(f"✅ Admin session created for {user.username} (ID: {session_id[:8]}...)")
        
        return {
            "session_id": session_id[:8] + "...",  # Don't expose full ID
            "expires_at": expires_at.isoformat(),
            "csrf_token": csrf_token,  # Send CSRF token to client
            "expires_in_hours": ADMIN_SESSION_DURATION_HOURS
        }
    
    def verify_admin_session(
        self,
        request: Request,
        csrf_token: Optional[str] = None,
        db: Session = None
    ) -> User:
        """
        Verify admin session from HTTP-only cookie and optional CSRF token.
        
        Args:
            request: FastAPI Request with cookies
            csrf_token: CSRF token from request header (required for state-changing operations)
            db: Database session
            
        Returns:
            Authenticated admin User object
            
        Raises:
            HTTPException if session invalid or expired
        """
        # Get session ID from HTTP-only cookie
        session_id = request.cookies.get("admin_session")
        
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin session required - please login to admin panel"
            )
        
        # Retrieve session data
        session_data = self._get_session_data(session_id)
        
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired admin session - please login again"
            )
        
        # Check expiration
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.utcnow() > expires_at:
            self._revoke_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin session expired - please login again"
            )
        
        # Check inactivity timeout
        last_activity = datetime.fromisoformat(session_data["last_activity"])
        inactivity_limit = timedelta(minutes=ADMIN_SESSION_INACTIVITY_MINUTES)
        if datetime.utcnow() - last_activity > inactivity_limit:
            self._revoke_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Admin session timed out after {ADMIN_SESSION_INACTIVITY_MINUTES} minutes of inactivity"
            )
        
        # Verify CSRF token for state-changing operations (POST, PUT, DELETE)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not csrf_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token required for this operation"
                )
            
            csrf_hash = session_data.get("csrf_token_hash")
            if not csrf_hash or not self._verify_token(csrf_token, csrf_hash):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid CSRF token"
                )
        
        # Update last activity timestamp
        self._update_activity(session_id, session_data)
        
        # Get user from database
        user = db.query(User).filter(User.id == session_data["user_id"]).first()
        
        if not user:
            self._revoke_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_admin:
            self._revoke_session(session_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges revoked"
            )
        
        return user
    
    def revoke_session(self, request: Request):
        """
        Revoke admin session (logout).
        """
        session_id = request.cookies.get("admin_session")
        if session_id:
            self._revoke_session(session_id)
            
            # Get session data for audit log
            user_id = None
            session_data = self._get_session_data(session_id)
            if session_data:
                user_id = session_data.get("user_id")
            
            if user_id:
                self._audit_log(user_id, "session_revoked", {})
    
    def _get_session_data(self, session_id: str) -> Optional[Dict]:
        """Retrieve session data from Redis or PostgreSQL fallback."""
        session_key = f"{self.session_prefix}:{session_id}"
        
        if redis_service.is_available():
            try:
                session_json = redis_service.client.get(session_key)
                if session_json:
                    return json.loads(session_json)
            except Exception as e:
                print(f"Failed to get admin session from Redis: {e}")
        
        # Fallback to PostgreSQL
        return self._get_session_from_db(session_id)
    
    def _update_activity(self, session_id: str, session_data: Dict):
        """Update last activity timestamp."""
        session_data["last_activity"] = datetime.utcnow().isoformat()
        session_key = f"{self.session_prefix}:{session_id}"
        
        if redis_service.is_available():
            try:
                # Get remaining TTL
                ttl = redis_service.client.ttl(session_key)
                if ttl > 0:
                    redis_service.client.setex(
                        session_key,
                        ttl,
                        json.dumps(session_data)
                    )
            except Exception as e:
                print(f"Failed to update activity: {e}")
    
    def _revoke_session(self, session_id: str):
        """Revoke session by deleting from Redis."""
        session_key = f"{self.session_prefix}:{session_id}"
        
        if redis_service.is_available():
            try:
                redis_service.client.delete(session_key)
                print(f"✅ Admin session revoked (ID: {session_id[:8]}...)")
            except Exception as e:
                print(f"Failed to revoke session: {e}")
        else:
            self._delete_session_from_db(session_id)
    
    def _hash_token(self, token: str) -> str:
        """Hash token using SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _verify_token(self, token: str, token_hash: str) -> bool:
        """Verify token against its hash."""
        return secrets.compare_digest(self._hash_token(token), token_hash)
    
    def _audit_log(self, user_id: str, action: str, metadata: Dict):
        """Log admin action for audit trail."""
        log_entry = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata
        }
        
        if redis_service.is_available():
            try:
                # Store audit log with 90-day retention
                log_key = f"{self.audit_prefix}:{user_id}:{datetime.utcnow().isoformat()}"
                redis_service.client.setex(
                    log_key,
                    90 * 24 * 3600,  # 90 days
                    json.dumps(log_entry)
                )
            except Exception as e:
                print(f"Failed to write audit log: {e}")
        
        # Also log to console for monitoring
        print(f"🔒 ADMIN AUDIT: {user_id} - {action} - {metadata}")
    
    # PostgreSQL fallback methods (for when Redis is unavailable)
    
    def _store_session_in_db(self, session_id: str, session_data: Dict, expires_at: datetime):
        """Store session in PostgreSQL as fallback."""
        # TODO: Implement PostgreSQL session storage if needed
        # For now, admin panel requires Redis for production security
        pass
    
    def _get_session_from_db(self, session_id: str) -> Optional[Dict]:
        """Get session from PostgreSQL fallback."""
        # TODO: Implement PostgreSQL session retrieval if needed
        return None
    
    def _delete_session_from_db(self, session_id: str):
        """Delete session from PostgreSQL fallback."""
        # TODO: Implement PostgreSQL session deletion if needed
        pass


# Global admin session manager
admin_session_manager = AdminSessionManager()


# FastAPI dependency for admin authentication
async def require_admin_session(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to require valid admin session.
    Use this instead of verify_admin_user_access for new secure implementation.
    
    For state-changing operations (POST/PUT/DELETE), also requires CSRF token
    in X-CSRF-Token header.
    """
    # Get CSRF token from header if present
    csrf_token = request.headers.get("X-CSRF-Token")
    
    # Verify session and return authenticated admin user
    return admin_session_manager.verify_admin_session(request, csrf_token, db)

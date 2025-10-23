"""
Authentication utilities for FastAPI with Production Security
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .schemas import TokenData
from .rate_limiter import rate_limiter_service
from .audit_logger import log_admin_action

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "").strip() or None
if not JWT_SECRET:
    raise ValueError("SECURITY ERROR: JWT_SECRET environment variable is required. Set it to a cryptographically secure random value.")
if JWT_SECRET in ["your-jwt-secret-key", "dev-secret", "test-secret", "secret", "jwt-secret"]:
    raise ValueError("SECURITY ERROR: JWT_SECRET cannot use weak/default values. Generate a secure random key.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Admin Configuration  
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "").strip() or None
if not ADMIN_SECRET_KEY:
    raise ValueError("SECURITY ERROR: ADMIN_SECRET_KEY environment variable is required. Set it to a cryptographically secure random value.")
if ADMIN_SECRET_KEY in ["admin-dev-key-123", "admin", "admin123", "password", "secret"]:
    raise ValueError("SECURITY ERROR: ADMIN_SECRET_KEY cannot use weak/default values. Generate a secure random key.")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def create_admin_session_token(user_id: str, expires_minutes: int = 30):
    """Create a short-lived admin session token"""
    to_encode = {
        "userId": user_id,
        "adminSession": True,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes)
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_admin_session_token(token: str) -> str:
    """Verify admin session token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("userId")
        is_admin_session: bool = payload.get("adminSession", False)
        
        if not user_id or not is_admin_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin session token"
            )
        
        return user_id
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session expired or invalid"
        )

def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("userId")
        username: str = payload.get("username")
        is_admin: bool = payload.get("isAdmin", False)
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(user_id=user_id, username=username, is_admin=is_admin)
        return token_data
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from Bearer token or cookie"""
    
    # Try to get token from Authorization header first
    token = credentials.credentials if credentials else None
    
    # If no Authorization header, try to get from cookie
    if not token and request:
        token = request.cookies.get("auth_token")
    
    # If still no token, raise unauthorized
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT verification
    token_data = verify_token(token)
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None"""
    # Try to get token from Authorization header first
    token = credentials.credentials if credentials else None
    
    # If no Authorization header, try to get from cookie
    if not token and request:
        token = request.cookies.get("auth_token")
    
    # If still no token, return None
    if not token:
        return None
    
    try:
        token_data = verify_token(token)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user
    except HTTPException:
        return None

def verify_admin_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> bool:
    """Verify admin access using the admin secret key"""
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if the token matches the admin secret key
    if credentials.credentials != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials"
        )
    
    return True

def verify_admin_user_access(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> User:
    """SIMPLIFIED: Verify admin access using only ADMIN_SECRET_KEY - no JWT required!
    
    This simplified authentication only requires the ADMIN_SECRET_KEY in the X-Admin-Key header.
    No need to login first - perfect for single admin use.
    
    Security features still enabled:
    - Rate limiting to prevent brute force
    - IP lockout after failed attempts
    - Audit logging of all admin actions
    """
    
    # Get client IP for rate limiting
    ip_address = request.client.host if request.client else "unknown"
    
    # Check if IP is locked out (after too many failed attempts)
    if rate_limiter_service.is_locked_out(ip_address, db):
        remaining_time = rate_limiter_service.get_remaining_lockout_time(ip_address, db)
        print(f"🚫 SECURITY: Blocked admin access from locked out IP: {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed authentication attempts. Try again in {remaining_time // 60} minutes."
        )
    
    # Check for X-Admin-Key header (no JWT required - simplified single-admin authentication)
    admin_key = request.headers.get("X-Admin-Key")
    if not admin_key:
        rate_limiter_service.record_failed_attempt(ip_address, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required - provide X-Admin-Key header",
        )
    
    # Verify the admin key using constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(admin_key.strip(), ADMIN_SECRET_KEY):
        rate_limiter_service.record_failed_attempt(ip_address, db)
        print(f"🚫 SECURITY: Invalid admin key attempt from IP: {ip_address}")
        log_admin_action("admin", "access_denied", request, db, {"reason": "invalid_key"}, success=False)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    
    # Key is valid! Create/fetch single admin user
    admin_user = db.query(User).filter(User.username == "admin").first()
    if admin_user is None:
        from uuid import uuid4
        admin_user = User(
            id=str(uuid4()),
            username="admin",
            email="admin@sqlgym.local",
            first_name="Admin",
            last_name="User",
            is_admin=True,
            premium=True,
            problems_solved=0,
            auth_provider="admin_key"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    
    # Clear failed attempts on successful authentication
    rate_limiter_service.clear_failed_attempts(ip_address, db)
    
    # Log successful admin access
    log_admin_action(admin_user.id, "admin_access", request, db, {"method": "simple_key"}, success=True)
    
    return admin_user
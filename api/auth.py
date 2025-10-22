"""
Authentication utilities for FastAPI
"""
import os
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
    
    # TEMPORARY: Development token bypass - only in explicit dev mode
    # Format: dev-token::<unique-dev-id>
    if os.getenv("DEV_TOKEN_BYPASS") == "true" and token.startswith('dev-token::'):
        dev_user_id = token.split('::', 1)[1] if '::' in token else None
        if dev_user_id:
            # Find or create unique dev user for this browser/developer
            dev_user = db.query(User).filter(User.id == dev_user_id).first()
            if not dev_user:
                # Create new isolated dev user with no submissions
                dev_user = User(
                    id=dev_user_id,
                    username=f"dev_{dev_user_id[:8]}",
                    email=f"{dev_user_id}@example.com",
                    first_name="Dev",
                    last_name="User",
                    problems_solved=0,
                    premium=True,
                    is_admin=False,
                    auth_provider="dev"
                )
                db.add(dev_user)
                db.commit()
                db.refresh(dev_user)
            return dev_user
    
    # Normal JWT verification for production
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
        
        # TEMPORARY: Development token bypass - only in explicit dev mode
        # Format: dev-token::<unique-dev-id>
        if os.getenv("DEV_TOKEN_BYPASS") == "true" and token.startswith('dev-token::'):
            dev_user_id = token.split('::', 1)[1] if '::' in token else None
            if dev_user_id:
                # Find or create unique dev user for this browser/developer
                dev_user = db.query(User).filter(User.id == dev_user_id).first()
                if not dev_user:
                    # Create new isolated dev user with no submissions
                    dev_user = User(
                        id=dev_user_id,
                        username=f"dev_{dev_user_id[:8]}",
                        email=f"{dev_user_id}@example.com",
                        first_name="Dev",
                        last_name="User",
                        problems_solved=0,
                        premium=True,
                        is_admin=False,
                        auth_provider="dev"
                    )
                    db.add(dev_user)
                    db.commit()
                    db.refresh(dev_user)
                return dev_user
        
        token_data = verify_token(token)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        return user
    except HTTPException:
        return None

def verify_admin_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> bool:
    """Verify admin access using the admin secret key"""
    
    # TEMPORARY DEV BYPASS - Only enabled with explicit flag (disabled by default)
    if os.getenv("DEV_ADMIN_BYPASS") == "true":
        return True
    
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
    """Verify admin access - accepts either X-Admin-Session token (new) or X-Admin-Key + JWT (legacy)"""
    
    # TEMPORARY DEV BYPASS - Only enabled with explicit flag (disabled by default)
    if os.getenv("DEV_ADMIN_BYPASS") == "true":
        # Create/find a temp admin user for development
        admin_user = db.query(User).filter(User.username == "temp_admin").first()
        if admin_user is None:
            from uuid import uuid4
            admin_user = User(
                id=str(uuid4()),
                username="temp_admin",
                email="temp_admin@example.com",
                is_admin=True,
                premium=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        return admin_user
    
    # NEW: Check for admin session token first (simpler flow)
    admin_session_token = request.headers.get("X-Admin-Session")
    if admin_session_token:
        try:
            user_id = verify_admin_session_token(admin_session_token)
            user = db.query(User).filter(User.id == user_id).first()
            
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            if not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied - admin privileges revoked"
                )
            
            return user
        except HTTPException:
            raise
    
    # LEGACY: Fall back to X-Admin-Key + JWT verification for backward compatibility
    admin_key = request.headers.get("X-Admin-Key")
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required - provide X-Admin-Session token or X-Admin-Key header",
        )
    
    if admin_key.strip() != ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    
    # Verify user JWT token
    token = credentials.credentials if credentials else None
    
    # If no Authorization header, try to get from cookie
    if not token:
        token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required - please login first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify JWT token
    try:
        token_data = verify_token(token)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify user has is_admin=True
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied - user does not have admin privileges. Contact a developer to set is_admin=true for your account."
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authentication credentials"
        )
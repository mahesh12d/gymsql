"""
Authentication utilities for FastAPI
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .schemas import TokenData

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("SECURITY ERROR: JWT_SECRET environment variable is required. Set it to a cryptographically secure random value.")
if JWT_SECRET in ["your-jwt-secret-key", "dev-secret", "test-secret", "secret", "jwt-secret"]:
    raise ValueError("SECURITY ERROR: JWT_SECRET cannot use weak/default values. Generate a secure random key.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Admin Configuration  
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY")
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
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user"""
    token = credentials.credentials
    
    # TEMPORARY: Development token bypass - only in explicit dev mode
    if os.getenv("DEV_TOKEN_BYPASS") == "true" and token == 'dev-token-123':
        dev_user = db.query(User).filter(User.id == 'dev-user-1').first()
        if dev_user:
            return dev_user
        else:
            # Fallback to any admin user for development
            dev_user = db.query(User).filter(User.username == 'admin').first()
            if dev_user:
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

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        
        # TEMPORARY: Development token bypass - only in explicit dev mode
        if os.getenv("DEV_TOKEN_BYPASS") == "true" and token == 'dev-token-123':
            dev_user = db.query(User).filter(User.id == 'dev-user-1').first()
            if dev_user:
                return dev_user
            else:
                # Fallback to any admin user for development
                dev_user = db.query(User).filter(User.username == 'admin').first()
                if dev_user:
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional),
    db: Session = Depends(get_db)
) -> User:
    """Verify admin access using either admin secret key or admin user token"""
    
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
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # First, check if it's the admin secret key
    if credentials.credentials == ADMIN_SECRET_KEY:
        # For admin secret key, find or create an admin user
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if admin_user is None:
            # Create a default admin user if none exists
            from uuid import uuid4
            admin_user = User(
                id=str(uuid4()),
                username="admin",
                email="admin@example.com",
                is_admin=True,
                premium=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        return admin_user
    
    # Otherwise, verify it's a JWT token from an admin user
    try:
        token_data = verify_token(credentials.credentials)
        user = db.query(User).filter(User.id == token_data.user_id).first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is admin
        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user
        
    except HTTPException:
        # If JWT verification fails, re-raise the exception
        raise
    except Exception:
        # For any other error, return forbidden
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin credentials"
        )
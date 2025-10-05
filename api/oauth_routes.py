"""
OAuth routes for Google authentication
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from .oauth_config import oauth
from .auth import create_access_token
from .database import get_db
from .models import User
import os

router = APIRouter(prefix="/api/auth", tags=["oauth"])

# Logout endpoint to clear the auth cookie
@router.post('/logout')
async def logout(response: Response):
    """Clear the authentication cookie"""
    response.delete_cookie(key="auth_token")
    return {"success": True, "message": "Logged out successfully"}

# ========== GOOGLE OAuth ==========

@router.get('/google/login')
async def google_login(request: Request):
    """Redirect user to Google login page"""
    # Get the base URL - use Replit domain if available, otherwise use request base
    replit_domain = os.getenv('REPLIT_DEV_DOMAIN') or os.getenv('REPLIT_DOMAINS', '').split(',')[0]
    if replit_domain:
        base_url = f"https://{replit_domain}"
    else:
        base_url = str(request.base_url).rstrip('/')
        # Ensure HTTPS for Replit (HTTP is used internally but HTTPS externally)
        base_url = base_url.replace('http://', 'https://')
    
    redirect_uri = f"{base_url}/api/auth/google/callback"
    print(f"🔗 OAuth redirect URI: {redirect_uri}")  # Debug logging
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get('/google/callback')
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")
        
        # Extract user data
        email = user_info.get('email')
        google_id = user_info.get('sub')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')
        profile_image_url = user_info.get('picture')
        
        if not email or not google_id:
            raise HTTPException(status_code=400, detail="Email or Google ID not provided")
        
        # Check if user exists by google_id or email
        user = db.query(User).filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()
        
        if user:
            # Update existing user with Google info if not already set
            if not user.google_id:
                user.google_id = google_id
            if not user.profile_image_url and profile_image_url:
                user.profile_image_url = profile_image_url
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            user.auth_provider = "google"
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            # Generate username from email
            username = email.split('@')[0]
            # Check if username exists, append number if needed
            existing_username = db.query(User).filter(User.username == username).first()
            if existing_username:
                counter = 1
                while db.query(User).filter(User.username == f"{username}{counter}").first():
                    counter += 1
                username = f"{username}{counter}"
            
            user = User(
                username=username,
                email=email,
                google_id=google_id,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
                auth_provider="google",
                password_hash=None  # OAuth users don't have passwords
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token
        access_token = create_access_token(data={
            "userId": user.id,
            "username": user.username,
            "isAdmin": user.is_admin
        })
        
        # Redirect to frontend with secure HttpOnly cookie
        frontend_url = os.getenv('FRONTEND_URL', '/')
        response = RedirectResponse(url=f"{frontend_url}?auth=success")
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,
            secure=True,  # Only send over HTTPS
            samesite="lax",  # CSRF protection
            max_age=86400  # 24 hours (matches JWT expiration)
        )
        return response
        
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")


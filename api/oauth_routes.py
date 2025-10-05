"""
OAuth routes for Google and GitHub authentication
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from .oauth_config import oauth
from .auth import create_access_token
from .database import get_db
from .models import User
import os

router = APIRouter(prefix="/api/auth", tags=["oauth"])

# ========== GOOGLE OAuth ==========

@router.get('/google/login')
async def google_login(request: Request):
    """Redirect user to Google login page"""
    # Get the base URL dynamically
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/auth/google/callback"
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
        
        # Redirect to frontend with token
        frontend_url = os.getenv('FRONTEND_URL', '/')
        return RedirectResponse(
            url=f"{frontend_url}?token={access_token}&auth=success"
        )
        
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")


# ========== GITHUB OAuth ==========

@router.get('/github/login')
async def github_login(request: Request):
    """Redirect user to GitHub login page"""
    # Get the base URL dynamically
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get('/github/callback')
async def github_callback(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback"""
    try:
        token = await oauth.github.authorize_access_token(request)
        
        # GitHub requires separate API call for user info
        resp = await oauth.github.get('https://api.github.com/user', token=token)
        user_info = resp.json()
        
        # Get user email (GitHub returns array)
        email_resp = await oauth.github.get('https://api.github.com/user/emails', token=token)
        emails = email_resp.json()
        primary_email = next((email['email'] for email in emails if email['primary']), None)
        
        # If no primary email, use the first verified email
        if not primary_email:
            primary_email = next((email['email'] for email in emails if email['verified']), None)
        
        github_id = str(user_info.get('id'))
        username_from_github = user_info.get('login')
        name = user_info.get('name', '').split(' ', 1) if user_info.get('name') else ['', '']
        first_name = name[0] if len(name) > 0 else None
        last_name = name[1] if len(name) > 1 else None
        profile_image_url = user_info.get('avatar_url')
        
        if not github_id:
            raise HTTPException(status_code=400, detail="GitHub ID not provided")
        
        # Check if user exists by github_id or email
        user = None
        if primary_email:
            user = db.query(User).filter(
                (User.github_id == github_id) | (User.email == primary_email)
            ).first()
        else:
            user = db.query(User).filter(User.github_id == github_id).first()
        
        if user:
            # Update existing user with GitHub info if not already set
            if not user.github_id:
                user.github_id = github_id
            if not user.profile_image_url and profile_image_url:
                user.profile_image_url = profile_image_url
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            if not user.email and primary_email:
                user.email = primary_email
            user.auth_provider = "github"
            db.commit()
            db.refresh(user)
        else:
            # Create new user
            # Use GitHub username or generate from email
            username = username_from_github
            if not username and primary_email:
                username = primary_email.split('@')[0]
            elif not username:
                username = f"github_user_{github_id}"
            
            # Check if username exists, append number if needed
            existing_username = db.query(User).filter(User.username == username).first()
            if existing_username:
                counter = 1
                while db.query(User).filter(User.username == f"{username}{counter}").first():
                    counter += 1
                username = f"{username}{counter}"
            
            # Email is required in User model, use a placeholder if not available
            email = primary_email if primary_email else f"{github_id}@github.oauth.local"
            
            user = User(
                username=username,
                email=email,
                github_id=github_id,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
                auth_provider="github",
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
        
        # Redirect to frontend with token
        frontend_url = os.getenv('FRONTEND_URL', '/')
        return RedirectResponse(
            url=f"{frontend_url}?token={access_token}&auth=success"
        )
        
    except Exception as e:
        print(f"GitHub OAuth error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"GitHub authentication failed: {str(e)}")

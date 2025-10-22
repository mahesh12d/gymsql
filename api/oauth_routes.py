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
    response.delete_cookie(
        key="auth_token",
        path="/",
        domain=None,
        secure=os.getenv('ENVIRONMENT') == 'production',
        httponly=True,
        samesite="lax"
    )
    return {"success": True, "message": "Logged out successfully"}

# ========== GOOGLE OAuth ==========

@router.get('/google/login')
async def google_login(request: Request):
    """Redirect user to Google login page"""
    # Use environment variable for redirect URI (more reliable)
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')

    if not redirect_uri:
        # Fallback to dynamic generation
        replit_domain = os.getenv('REPLIT_DEV_DOMAIN') or os.getenv('REPLIT_DOMAINS', '').split(',')[0]
        if replit_domain:
            base_url = f"https://{replit_domain}"
        else:
            base_url = str(request.base_url).rstrip('/')
            # Use HTTPS in production
            if os.getenv('ENVIRONMENT') == 'production':
                base_url = base_url.replace('http://', 'https://')

        redirect_uri = f"{base_url}/api/auth/google/callback"

    print(f"🔗 OAuth redirect URI: {redirect_uri}")

    # Include state parameter for CSRF protection (handled by authlib)
    return await oauth.google.authorize_redirect(
        request, 
        redirect_uri,
        # Optional: request specific scopes
        # scope='openid email profile'
    )


@router.get('/google/callback')
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Check for error parameter (user denied authorization)
        if request.query_params.get('error'):
            error_description = request.query_params.get('error_description', 'Authorization denied')
            frontend_urls = os.getenv('FRONTEND_URLS', '')
            print(f"🔍 DEBUG (error) - FRONTEND_URLS: '{frontend_urls}'")
            frontend_url = frontend_urls.split(',')[0].strip() if frontend_urls else '/home'
            return RedirectResponse(url=f"{frontend_url}?auth=failed&error={error_description}")

        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

        # Extract user data
        email = user_info.get('email')
        google_id = user_info.get('sub')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        profile_image_url = user_info.get('picture')
        email_verified = user_info.get('email_verified', False)

        if not email or not google_id:
            raise HTTPException(status_code=400, detail="Email or Google ID not provided")

        # Optional: Only allow verified emails
        if not email_verified:
            raise HTTPException(status_code=400, detail="Email not verified by Google")

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

            # Optional: Store refresh token for later use
            if 'refresh_token' in token:
                user.google_refresh_token = token['refresh_token']

            db.commit()
            db.refresh(user)
        else:
            # Create new user
            # Generate username from email
            username = email.split('@')[0]

            # Check if username exists, append number if needed
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                google_id=google_id,
                first_name=first_name,
                last_name=last_name,
                profile_image_url=profile_image_url,
                auth_provider="google",
                password_hash=None,  # OAuth users don't have passwords
                # Optional: Store refresh token
                # google_refresh_token=token.get('refresh_token')
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
        # For cross-domain setups (e.g., Vercel + Cloud Run), include token in URL
        # Frontend will store it in localStorage
        frontend_urls = os.getenv('FRONTEND_URLS', '')
        print(f"🔍 DEBUG - FRONTEND_URLS env var: '{frontend_urls}'")
        frontend_url = frontend_urls.split(',')[0].strip() if frontend_urls else '/home'
        print(f"🔍 DEBUG - Redirecting to: {frontend_url}")
        
        # Determine if we're in production (use secure cookies)
        is_production = os.getenv('ENV') == 'production'
        
        # Include token in URL for cross-domain scenarios
        response = RedirectResponse(url=f"{frontend_url}?auth=success&token={access_token}")

        # Also set cookie for same-domain scenarios (with SameSite=None for cross-domain)
        response.set_cookie(
            key="auth_token",
            value=access_token,
            httponly=True,
            secure=True,  # Always use secure in production
            samesite="none" if is_production else "lax",  # None for cross-domain
            max_age=86400,  # 24 hours
            path="/"  # Available across entire site
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Google OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Redirect to frontend with error
        frontend_urls = os.getenv('FRONTEND_URLS', '')
        print(f"🔍 DEBUG (exception) - FRONTEND_URLS: '{frontend_urls}'")
        frontend_url = frontend_urls.split(',')[0].strip() if frontend_urls else '/home'
        return RedirectResponse(url=f"{frontend_url}?auth=failed&error=authentication_failed")
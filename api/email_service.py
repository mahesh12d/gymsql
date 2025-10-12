"""
Email verification service using Resend API
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
import resend
from sqlalchemy.orm import Session
from .models import User

# Initialize Resend with API key
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY environment variable is required for email verification")

resend.api_key = RESEND_API_KEY

# Email configuration
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5000")

# Get the appropriate base URL based on environment
def get_base_url() -> str:
    """Get the base URL for email verification links"""
    # Try Replit domain first
    replit_domain = os.getenv('REPLIT_DEV_DOMAIN') or os.getenv('REPLIT_DOMAINS', '').split(',')[0] if os.getenv('REPLIT_DOMAINS') else None
    if replit_domain:
        return f"https://{replit_domain}"
    
    # Use FRONTEND_URL if set
    if FRONTEND_URL and FRONTEND_URL != "http://localhost:5000":
        return FRONTEND_URL
    
    # Default to localhost
    return "http://localhost:5000"


def generate_verification_token() -> str:
    """Generate a secure random verification token"""
    return secrets.token_urlsafe(32)


def create_verification_token(user: User, db: Session) -> str:
    """Create and save a verification token for the user"""
    token = generate_verification_token()
    user.verification_token = token
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    db.refresh(user)
    return token


def send_verification_email(user: User, token: str) -> bool:
    """Send verification email to the user"""
    try:
        base_url = get_base_url()
        verification_link = f"{base_url}/verify-email?token={token}"
        
        params = {
            "from": FROM_EMAIL,
            "to": [user.email],
            "subject": "Verify your SQLGym account",
            "html": f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                        }}
                        .container {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 40px;
                            border-radius: 10px;
                            color: white;
                        }}
                        .content {{
                            background: white;
                            color: #333;
                            padding: 30px;
                            border-radius: 8px;
                            margin-top: 20px;
                        }}
                        .button {{
                            display: inline-block;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            padding: 14px 28px;
                            text-decoration: none;
                            border-radius: 6px;
                            margin: 20px 0;
                            font-weight: 600;
                        }}
                        .footer {{
                            margin-top: 30px;
                            font-size: 12px;
                            color: #666;
                            text-align: center;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🏋️ Welcome to SQLGym!</h1>
                        <div class="content">
                            <h2>Hi {user.username},</h2>
                            <p>Thank you for signing up for SQLGym! To complete your registration and start your SQL learning journey, please verify your email address.</p>
                            
                            <div style="text-align: center;">
                                <a href="{verification_link}" class="button">
                                    Verify Email Address
                                </a>
                            </div>
                            
                            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                                Or copy and paste this link into your browser:<br>
                                <a href="{verification_link}" style="color: #667eea; word-break: break-all;">{verification_link}</a>
                            </p>
                            
                            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                                This link will expire in 24 hours. If you didn't create an account with SQLGym, you can safely ignore this email.
                            </p>
                        </div>
                    </div>
                    <div class="footer">
                        <p>SQLGym - Level up your SQL skills 💪</p>
                    </div>
                </body>
                </html>
            """
        }
        
        response = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False


def verify_token(token: str, db: Session) -> Optional[User]:
    """Verify a token and return the user if valid"""
    user = db.query(User).filter(User.verification_token == token).first()
    
    if not user:
        return None
    
    # Check if token is expired
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        return None
    
    return user


def mark_email_verified(user: User, db: Session):
    """Mark user's email as verified and clear the verification token"""
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    db.refresh(user)

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


def generate_verification_code() -> str:
    """Generate a secure 6-digit verification code"""
    return ''.join(secrets.choice('0123456789') for _ in range(6))


def hash_verification_code(code: str) -> str:
    """Hash the verification code for secure storage"""
    from .auth import get_password_hash
    return get_password_hash(code)


def create_verification_code(user: User, db: Session) -> str:
    """Create and save a hashed verification code for the user"""
    code = generate_verification_code()
    hashed_code = hash_verification_code(code)
    user.verification_token = hashed_code
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    db.commit()
    db.refresh(user)
    return code  # Return the plain code to send via email


def send_verification_email(user: User, code: str) -> bool:
    """Send verification email with 6-digit code to the user"""
    try:
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
                        .code-box {{
                            background: #f5f5f5;
                            border: 2px solid #667eea;
                            border-radius: 8px;
                            padding: 20px;
                            margin: 30px 0;
                            text-align: center;
                        }}
                        .code {{
                            font-size: 36px;
                            font-weight: 700;
                            letter-spacing: 8px;
                            color: #667eea;
                            font-family: 'Courier New', monospace;
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
                            <p>Thank you for signing up for SQLGym! To complete your registration and start your SQL learning journey, please enter this verification code:</p>
                            
                            <div class="code-box">
                                <div class="code">{code}</div>
                            </div>
                            
                            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                                This code will expire in 24 hours. If you didn't create an account with SQLGym, you can safely ignore this email.
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


def verify_code(email: str, code: str, db: Session) -> Optional[User]:
    """Verify a 6-digit code and return the user if valid"""
    from .auth import verify_password
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.verification_token:
        return None
    
    # Check if token is expired
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        return None
    
    # Verify the code against the hashed version
    if not verify_password(code, user.verification_token):
        return None
    
    return user


def mark_email_verified(user: User, db: Session):
    """Mark user's email as verified and clear the verification token"""
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    db.refresh(user)

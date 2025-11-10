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
from .config import Config

# Initialize Resend with API key from configuration
if Config.RESEND_API_KEY:
  resend.api_key = Config.RESEND_API_KEY
else:
  print("⚠️  RESEND_API_KEY not configured - email features will be disabled")

# Email configuration from centralized config
FROM_EMAIL = Config.FROM_EMAIL


# Get the appropriate base URL based on environment
def get_base_url() -> str:
  """Get the base URL for email verification links"""
  # Use first frontend URL if available
  if Config.FRONTEND_URLS:
    return Config.FRONTEND_URLS[0]

  # Try Replit domain
  replit_domain = os.getenv('REPLIT_DEV_DOMAIN') or os.getenv(
      'REPLIT_DOMAINS',
      '').split(',')[0] if os.getenv('REPLIT_DOMAINS') else None
  if replit_domain:
    return f"https://{replit_domain}"

  # Default to localhost for local development
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
  if not Config.RESEND_API_KEY:
    print("⚠️  Email sending skipped - RESEND_API_KEY not configured")
    return False

  try:
    params = {
        "from":
        FROM_EMAIL,
        "to": [user.email],
        "subject":
        "Verify your SQLGym account",
        "html":
        f"""
                <!DOCTYPE html>
                <html>
                <head>
                  <meta charset="UTF-8">
                  <title>SQLGym Verification Code</title>
                  <style>
                    body {
                      font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                      background-color: #f4f6fa;
                      line-height: 1.6;
                      color: #333;
                      margin: 0;
                      padding: 0;
                    }
                    .wrapper {
                      max-width: 600px;
                      margin: 40px auto;
                      padding: 20px;
                    }
                    .header {
                      text-align: center;
                      background: linear-gradient(135deg, #ff7b00 0%, #ffb347 100%);
                      padding: 35px 20px;
                      border-radius: 12px 12px 0 0;
                      color: #fff;
                    }
                    .header h1 {
                      font-size: 28px;
                      margin: 0;
                      font-weight: 700;
                    }
                    .content {
                      background: #fff;
                      padding: 40px 30px;
                      border-radius: 0 0 12px 12px;
                      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                    }
                    .content h2 {
                      color: #222;
                      margin-bottom: 10px;
                    }
                    .content p {
                      color: #555;
                      font-size: 15px;
                      margin-top: 8px;
                    }
                    .code-box {
                      background: #fafafa;
                      border: 2px solid #ff7b00;
                      border-radius: 8px;
                      padding: 25px;
                      text-align: center;
                      margin: 30px 0;
                    }
                    .code {
                      font-size: 36px;
                      font-weight: 700;
                      letter-spacing: 8px;
                      color: #ff7b00;
                      font-family: 'Courier New', monospace;
                    }
                    .footer {
                      text-align: center;
                      font-size: 13px;
                      color: #777;
                      margin-top: 25px;
                    }
                    .footer a {
                      color: #ff7b00;
                      text-decoration: none;
                      font-weight: 500;
                    }
                  </style>
                </head>
                <body>
                  <div class="wrapper">
                    <div class="header">
                      <h1>🏋️ SQLGym Verification</h1>
                      <p style="font-size:14px;opacity:0.9;">Level up your SQL skills with every rep 💪</p>
                    </div>

                    <div class="content">
                      <h2>Hi {user.username},</h2>
                      <p>Thanks for joining <strong>SQLGym</strong>! To complete your registration, please enter the verification code below:</p>

                      <div class="code-box">
                        <div class="code">{code}</div>
                      </div>

                      <p style="font-size:14px;">
                        This code will expire in <strong>24 hours</strong>. If you didn’t create an account, you can safely ignore this message.
                      </p>
                    </div>

                    <div class="footer">
                      <p>Need help? <a href="mailto:support@sqlgym.com">Contact Support</a></p>
                      <p>&copy; 2025 GYMSQL. All rights reserved.</p>
                    </div>
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
  if user.verification_token_expires and user.verification_token_expires < datetime.utcnow(
  ):
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

"""
OAuth configuration for Google and GitHub authentication
"""
from authlib.integrations.starlette_client import OAuth
from .config import Config as AppConfig

# Initialize OAuth registry
oauth = OAuth()

# Register Google OAuth (if configured)
if AppConfig.GOOGLE_CLIENT_ID and AppConfig.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=AppConfig.GOOGLE_CLIENT_ID,
        client_secret=AppConfig.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    print("✅ Google OAuth configured")
else:
    print("⚠️  Google OAuth not configured - Google login will be disabled")

# Register GitHub OAuth (if configured)
if AppConfig.GITHUB_CLIENT_ID and AppConfig.GITHUB_CLIENT_SECRET:
    oauth.register(
        name='github',
        client_id=AppConfig.GITHUB_CLIENT_ID,
        client_secret=AppConfig.GITHUB_CLIENT_SECRET,
        authorize_url='https://github.com/login/oauth/authorize',
        authorize_params=None,
        access_token_url='https://github.com/login/oauth/access_token',
        access_token_params=None,
        client_kwargs={'scope': 'user:email'},
    )
    print("✅ GitHub OAuth configured")
else:
    print("⚠️  GitHub OAuth not configured - GitHub login will be disabled")

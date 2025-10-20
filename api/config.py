"""
Centralized Configuration Management for Docker Deployment
=========================================================
All configuration values are read directly from environment variables.
Secrets should be injected via Docker/Cloud Run environment variables.
"""
import os
from typing import List, Optional
from enum import Enum


class Environment(str, Enum):
    """Deployment environment types"""
    DEV = "dev"
    UAT = "uat"
    PROD = "prod"
    LOCAL = "local"


class Config:
    """Base configuration with environment-aware settings"""
    
    # ==================== ENVIRONMENT DETECTION ====================
    @staticmethod
    def get_environment() -> Environment:
        """Detect current deployment environment from ENV variable"""
        env = os.getenv("ENV", "local").lower()
        if env in ["dev", "development"]:
            return Environment.DEV
        elif env in ["uat", "staging"]:
            return Environment.UAT
        elif env in ["prod", "production"]:
            return Environment.PROD
        return Environment.LOCAL
    
    ENVIRONMENT = get_environment()
    
    # ==================== DATABASE CONFIGURATION ====================
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Database connection pool settings (environment-specific)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))
    
    # ==================== REDIS CONFIGURATION ====================
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
    REDIS_HEALTH_CHECK_INTERVAL: int = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    
    # ==================== AWS S3 CONFIGURATION ====================
    # AWS credentials (automatically used by boto3)
    # Strip whitespace to handle Google Cloud Secret Manager formatting
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID", "").strip() or None
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip() or None
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1").strip()
    
    # S3 bucket configuration (environment-specific)
    S3_ALLOWED_BUCKETS: List[str] = [
        bucket.strip().lower() 
        for bucket in os.getenv(
            "S3_ALLOWED_BUCKETS", 
            ""
        ).split(",") 
        if bucket.strip()
    ]
    
    # S3 file size and row limits
    S3_MAX_FILE_SIZE_MB: int = int(os.getenv("S3_MAX_FILE_SIZE_MB", "5"))
    S3_MAX_ROWS: int = int(os.getenv("S3_MAX_ROWS", "1000"))
    S3_MAX_CACHE_ENTRIES: int = int(os.getenv("S3_MAX_CACHE_ENTRIES", "1000"))
    
    # Dataset-specific limits
    S3_DATASET_MAX_FILE_SIZE_MB: int = int(os.getenv("S3_DATASET_MAX_FILE_SIZE_MB", "100"))
    S3_DATASET_MAX_ROWS: int = int(os.getenv("S3_DATASET_MAX_ROWS", "1000000"))
    
    # ==================== AUTHENTICATION & SECURITY ====================
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is required")
    
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "720"))  # 30 days default
    
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY")
    if not ADMIN_SECRET_KEY:
        raise ValueError("ADMIN_SECRET_KEY environment variable is required")
    
    # ==================== OAUTH CONFIGURATION ====================
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    
    # ==================== EMAIL CONFIGURATION ====================
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY")
    FROM_EMAIL: str = os.getenv("FROM_EMAIL", "noreply@sqlgym.com")
    
    # ==================== FRONTEND & CORS CONFIGURATION ====================
    # Frontend URLs (comma-separated list for multiple domains)
    FRONTEND_URLS: List[str] = [
        url.strip() 
        for url in os.getenv("FRONTEND_URLS", "").split(",") 
        if url.strip()
    ]
    
    # Allowed CORS origins (environment-specific)
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get environment-specific CORS origins"""
        origins = []
        
        # Add frontend URLs from environment
        if Config.FRONTEND_URLS:
            origins.extend(Config.FRONTEND_URLS)
        
        # Add localhost for local development
        if Config.ENVIRONMENT == Environment.LOCAL:
            origins.extend([
                "http://localhost:5000",
                "http://localhost:3000",
                "http://127.0.0.1:5000",
                "http://127.0.0.1:3000"
            ])
        
        # Add Vercel deployment URL if present
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            origins.append(f"https://{vercel_url}")
        
        # Add Replit deployment URLs if present
        repl_id = os.getenv("REPL_ID")
        repl_owner = os.getenv("REPL_OWNER", "user")
        if repl_id:
            origins.extend([
                f"https://{repl_id}--{repl_owner}.replit.app",
                f"https://{repl_id}.{repl_owner}.replit.dev"
            ])
        
        # Add Replit domain if present
        replit_domain = os.getenv("REPLIT_DEV_DOMAIN") or (
            os.getenv("REPLIT_DOMAINS", "").split(",")[0] 
            if os.getenv("REPLIT_DOMAINS") else None
        )
        if replit_domain:
            origins.append(f"https://{replit_domain}")
        
        return list(set(origins))  # Remove duplicates
    
    # ==================== AI & MACHINE LEARNING ====================
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    # AI hint rate limiting
    AI_HINT_LIMIT_PER_HOUR: int = int(os.getenv("AI_HINT_LIMIT_PER_HOUR", "5"))
    AI_HINT_LIMIT_PER_PROBLEM: int = int(os.getenv("AI_HINT_LIMIT_PER_PROBLEM", "5"))
    
    # ==================== SERVER CONFIGURATION ====================
    PORT: int = int(os.getenv("PORT", "5000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Workers and concurrency
    WORKERS: int = int(os.getenv("WORKERS", "1"))
    
    # ==================== CLOUD RUN CONFIGURATION ====================
    # Google Cloud Run specific settings
    GCP_PROJECT_ID: Optional[str] = os.getenv("GCP_PROJECT_ID")
    GCP_REGION: str = os.getenv("GCP_REGION", "us-central1")
    
    # Cloud Run service configuration (environment-specific)
    CLOUD_RUN_MEMORY: str = os.getenv("CLOUD_RUN_MEMORY", "1Gi")
    CLOUD_RUN_CPU: str = os.getenv("CLOUD_RUN_CPU", "1")
    CLOUD_RUN_TIMEOUT: int = int(os.getenv("CLOUD_RUN_TIMEOUT", "300"))
    CLOUD_RUN_MAX_INSTANCES: int = int(os.getenv("CLOUD_RUN_MAX_INSTANCES", "10"))
    CLOUD_RUN_MIN_INSTANCES: int = int(os.getenv("CLOUD_RUN_MIN_INSTANCES", "0"))
    CLOUD_RUN_CONCURRENCY: int = int(os.getenv("CLOUD_RUN_CONCURRENCY", "80"))
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_SUBMISSIONS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_SUBMISSIONS_PER_MINUTE", "10"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    # ==================== DATA RETENTION ====================
    DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "180"))  # 6 months
    
    # ==================== LOGGING & MONITORING ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_SQL_LOGGING: bool = os.getenv("ENABLE_SQL_LOGGING", "false").lower() == "true"
    
    # ==================== VALIDATION ====================
    @classmethod
    def validate_config(cls) -> None:
        """Validate critical configuration settings"""
        errors = []
        
        # Required settings
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        if not cls.JWT_SECRET:
            errors.append("JWT_SECRET is required")
        if not cls.ADMIN_SECRET_KEY:
            errors.append("ADMIN_SECRET_KEY is required")
        
        # AWS S3 validation (if S3 buckets are configured)
        if cls.S3_ALLOWED_BUCKETS and not (cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY):
            errors.append("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY required when S3_ALLOWED_BUCKETS is configured")
        
        # Email validation (if email features are used)
        if not cls.RESEND_API_KEY:
            print("⚠️  RESEND_API_KEY not set - email verification will be disabled")
        
        # OAuth validation (optional)
        if not (cls.GOOGLE_CLIENT_ID and cls.GOOGLE_CLIENT_SECRET):
            print("⚠️  Google OAuth not configured - Google login will be disabled")
        if not (cls.GITHUB_CLIENT_ID and cls.GITHUB_CLIENT_SECRET):
            print("⚠️  GitHub OAuth not configured - GitHub login will be disabled")
        
        # AI features validation (optional)
        if not cls.GEMINI_API_KEY:
            print("⚠️  GEMINI_API_KEY not set - AI hints will be disabled")
        
        if errors:
            raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
        
        print(f"✅ Configuration validated successfully for {cls.ENVIRONMENT.value} environment")
    
    @classmethod
    def print_config_summary(cls) -> None:
        """Print configuration summary (without secrets)"""
        print("\n" + "=" * 60)
        print(f"SQLGym Configuration Summary - {cls.ENVIRONMENT.value.upper()} Environment")
        print("=" * 60)
        print(f"Database: {'✅ Connected' if cls.DATABASE_URL else '❌ Not configured'}")
        print(f"Redis: {'✅ Configured' if cls.REDIS_URL else '⚠️  Not configured (fallback to PostgreSQL)'}")
        print(f"S3 Buckets: {len(cls.S3_ALLOWED_BUCKETS)} configured")
        print(f"AWS Region: {cls.AWS_REGION}")
        print(f"GCP Region: {cls.GCP_REGION}")
        print(f"Frontend URLs: {len(cls.FRONTEND_URLS)} configured")
        print(f"CORS Origins: {len(cls.get_cors_origins())} allowed")
        print(f"Email Service: {'✅ Enabled' if cls.RESEND_API_KEY else '❌ Disabled'}")
        print(f"Google OAuth: {'✅ Enabled' if cls.GOOGLE_CLIENT_ID else '❌ Disabled'}")
        print(f"GitHub OAuth: {'✅ Enabled' if cls.GITHUB_CLIENT_ID else '❌ Disabled'}")
        print(f"AI Hints: {'✅ Enabled' if cls.GEMINI_API_KEY else '❌ Disabled'}")
        print(f"Port: {cls.PORT}")
        print(f"Rate Limiting: {'✅ Enabled' if cls.RATE_LIMIT_ENABLED else '❌ Disabled'}")
        print("=" * 60 + "\n")


# Validate configuration on import
try:
    Config.validate_config()
    Config.print_config_summary()
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    raise

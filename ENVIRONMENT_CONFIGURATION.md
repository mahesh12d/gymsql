# SQLGym Environment Configuration Guide

## Overview

SQLGym now supports a three-stage deployment pipeline with environment-based configuration:
- **Development (dev)**: Local development and testing
- **UAT/Staging (uat)**: User acceptance testing and staging
- **Production (prod)**: Production deployment

All configuration is managed through environment variables, eliminating hardcoded values and improving security.

## Quick Start

### 1. Choose Your Environment Template

Copy the appropriate template for your environment:

```bash
# For Development
cp .env.dev.template .env.dev

# For UAT/Staging
cp .env.uat.template .env.uat

# For Production
cp .env.prod.template .env.prod
```

### 2. Configure Environment Variables

Edit your `.env.[environment]` file and fill in the actual values:

```bash
# Edit development environment
nano .env.dev

# Edit UAT environment
nano .env.uat

# Edit production environment
nano .env.prod
```

**IMPORTANT**: Make sure the `ENV` variable is set inside your .env file:
- `.env.dev` should have `ENV=dev`
- `.env.uat` should have `ENV=uat`
- `.env.prod` should have `ENV=prod`

The application will automatically detect and load the correct environment file.

### 3. File Loading Priority

The configuration system loads environment files **additively** in the following order (later files override earlier ones):

1. **`.env`** (if exists) - base configuration, lowest priority
2. **Environment-specific file** based on `ENV` variable:
   - If `ENV=dev` → loads `.env.dev`
   - If `ENV=uat` → loads `.env.uat`
   - If `ENV=prod` → loads `.env.prod`
   - If `ENV` not set → auto-detects first existing file (`.env.dev`, `.env.uat`, or `.env.prod`)
3. **`.env.local`** (if exists) - local overrides, **highest priority**

**Example workflows:**

**Developer workflow:**
```bash
# Copy template
cp .env.dev.template .env.dev
# Edit .env.dev with your values
# Application automatically loads .env.dev
npm run dev
```

**Override specific values:**
```bash
# Use .env.dev as base
cp .env.dev.template .env.dev

# Override only DATABASE_URL for local testing
echo "DATABASE_URL=postgresql://localhost:5432/test" > .env.local

# Application loads .env.dev THEN .env.local (override wins)
npm run dev
```

This additive approach means you can use `.env.local` to override specific values from `.env.dev` without recreating the entire configuration.

## Required Environment Variables

### Critical (Must be set)

| Variable | Description | Example |
|----------|-------------|---------|
| `ENV` | Deployment environment | `dev`, `uat`, or `prod` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` |
| `JWT_SECRET` | Secret key for JWT tokens | Long random string |
| `ADMIN_SECRET_KEY` | Secret key for admin access | Long random string |

### AWS S3 Configuration (Required if using S3 features)

| Variable | Description | Example |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_ALLOWED_BUCKETS` | Comma-separated list of allowed buckets | `bucket1,bucket2,bucket3` |

### Optional Features

| Variable | Description | Default | Required For |
|----------|-------------|---------|--------------|
| `REDIS_URL` | Redis connection string | None | Caching, rate limiting |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | None | Google login |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | None | Google login |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | None | GitHub login |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | None | GitHub login |
| `RESEND_API_KEY` | Resend API key | None | Email verification |
| `GEMINI_API_KEY` | Google Gemini API key | None | AI hints |

### Frontend & CORS

| Variable | Description | Example |
|----------|-------------|---------|
| `FRONTEND_URLS` | Comma-separated list of allowed frontend URLs | `https://app.com,https://www.app.com` |

## Environment-Specific Configuration

### Development Environment

```bash
ENV=dev
DATABASE_URL=postgresql://user:password@localhost:5432/sqlgym_dev
S3_ALLOWED_BUCKETS=sql-learning-datasets-dev,sql-learning-answers-dev
FRONTEND_URLS=http://localhost:5000,http://localhost:3000

# Database Pool Settings (Dev)
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5

# Cloud Run Settings (Dev)
CLOUD_RUN_MEMORY=512Mi
CLOUD_RUN_MAX_INSTANCES=3

# Logging
LOG_LEVEL=DEBUG
ENABLE_SQL_LOGGING=true
```

### UAT/Staging Environment

```bash
ENV=uat
DATABASE_URL=postgresql://user:password@uat-db:5432/sqlgym_uat
S3_ALLOWED_BUCKETS=sql-learning-datasets-uat,sql-learning-answers-uat
FRONTEND_URLS=https://uat.sqlgym.com

# Database Pool Settings (UAT)
DB_POOL_SIZE=15
DB_MAX_OVERFLOW=8

# Cloud Run Settings (UAT)
CLOUD_RUN_MEMORY=1Gi
CLOUD_RUN_MAX_INSTANCES=5

# Logging
LOG_LEVEL=INFO
ENABLE_SQL_LOGGING=false
```

### Production Environment

```bash
ENV=prod
DATABASE_URL=postgresql://user:password@prod-db:5432/sqlgym_prod
S3_ALLOWED_BUCKETS=sql-learning-datasets,sql-learning-answers
FRONTEND_URLS=https://sqlgym.com,https://www.sqlgym.com

# Database Pool Settings (Prod)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Cloud Run Settings (Prod)
CLOUD_RUN_MEMORY=2Gi
CLOUD_RUN_CPU=2
CLOUD_RUN_MAX_INSTANCES=20
CLOUD_RUN_MIN_INSTANCES=1

# Logging
LOG_LEVEL=WARNING
ENABLE_SQL_LOGGING=false
```

## Google Cloud Deployment

### Deploy to Development

```bash
gcloud builds submit --config=cloudbuild.dev.yaml
```

### Deploy to UAT

```bash
gcloud builds submit --config=cloudbuild.uat.yaml
```

### Deploy to Production

```bash
gcloud builds submit --config=cloudbuild.prod.yaml
```

### Setting Environment Variables in Cloud Run

After deploying, set environment variables using the Google Cloud Console or CLI:

```bash
# Example: Set database URL for dev environment
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --set-env-vars="DATABASE_URL=postgresql://..." \
  --set-env-vars="JWT_SECRET=..." \
  --set-env-vars="ADMIN_SECRET_KEY=..."

# For multiple variables, create an env.yaml file
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --env-vars-file=env.dev.yaml
```

Example `env.dev.yaml`:
```yaml
DATABASE_URL: "postgresql://..."
JWT_SECRET: "..."
ADMIN_SECRET_KEY: "..."
AWS_ACCESS_KEY_ID: "..."
AWS_SECRET_ACCESS_KEY: "..."
S3_ALLOWED_BUCKETS: "bucket1,bucket2"
```

## Docker Deployment

### Build for Specific Environment

```bash
# Development
docker build -f Dockerfile.dev -t sqlgym:dev .

# UAT
docker build -f Dockerfile.uat -t sqlgym:uat .

# Production
docker build -f Dockerfile.prod -t sqlgym:prod .
```

### Run with Environment File

```bash
# Development
docker run -p 5000:5000 --env-file .env.dev sqlgym:dev

# UAT
docker run -p 8080:8080 --env-file .env.uat sqlgym:uat

# Production
docker run -p 8080:8080 --env-file .env.prod sqlgym:prod
```

## Security Best Practices

### 1. Never Commit Actual Environment Files

```bash
# ✅ DO commit templates
.env.dev.template
.env.uat.template
.env.prod.template

# ❌ NEVER commit actual files (already in .gitignore)
.env.dev
.env.uat
.env.prod
```

### 2. Use Strong Secrets

Generate strong random secrets for production:

```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Generate admin secret key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 3. Environment-Specific Buckets

Use different S3 buckets for each environment:
- Dev: `sql-learning-datasets-dev`
- UAT: `sql-learning-datasets-uat`
- Prod: `sql-learning-datasets`

### 4. Separate Database Instances

Always use separate database instances for each environment to prevent data loss.

## Configuration Validation

The application validates configuration on startup. If critical variables are missing, it will fail with a clear error message:

```
❌ Configuration Error: Configuration validation failed:
  - DATABASE_URL is required
  - JWT_SECRET is required
  - ADMIN_SECRET_KEY is required
```

## Configuration Summary

On startup, the application prints a configuration summary:

```
============================================================
SQLGym Configuration Summary - PROD Environment
============================================================
Database: ✅ Connected
Redis: ✅ Configured
S3 Buckets: 4 configured
AWS Region: us-east-1
GCP Region: us-central1
Frontend URLs: 2 configured
CORS Origins: 5 allowed
Email Service: ✅ Enabled
Google OAuth: ✅ Enabled
GitHub OAuth: ✅ Enabled
AI Hints: ✅ Enabled
Port: 8080
Rate Limiting: ✅ Enabled
============================================================
```

## Troubleshooting

### Configuration Not Loading

1. Check that `ENV` environment variable is set:
   ```bash
   echo $ENV
   ```

2. Verify environment file exists:
   ```bash
   ls -la .env.dev .env.uat .env.prod
   ```

3. Check for syntax errors in environment file:
   ```bash
   cat .env.dev | grep -v '^#' | grep -v '^$'
   ```

### AWS S3 Connection Issues

1. Verify AWS credentials are set:
   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   ```

2. Check bucket allowlist:
   ```bash
   echo $S3_ALLOWED_BUCKETS
   ```

3. Verify bucket access:
   ```bash
   aws s3 ls s3://your-bucket-name --region us-east-1
   ```

### Database Connection Issues

1. Test database connection:
   ```bash
   psql "$DATABASE_URL"
   ```

2. Check connection pool settings if experiencing timeouts:
   - Increase `DB_POOL_SIZE`
   - Increase `DB_POOL_TIMEOUT`

## Migration from Hardcoded Values

If migrating from a previous version with hardcoded values:

1. **Identify all hardcoded values** in your deployment
2. **Create environment file** from template
3. **Fill in actual values** from your current deployment
4. **Test in development** environment first
5. **Deploy to UAT** for validation
6. **Deploy to production** after UAT approval

## Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [Resend API Documentation](https://resend.com/docs)
- [Google Gemini API Documentation](https://ai.google.dev/docs)

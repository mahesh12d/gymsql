# SQLGym Docker Deployment Guide

## Overview

SQLGym uses a single Docker image for all environments. All configuration is managed through environment variables for enhanced security and simplicity.

## Prerequisites

- Docker installed
- Google Cloud SDK (for Cloud Run deployment)
- Required environment variables configured

## Required Environment Variables

### Core Configuration
- `DATABASE_URL` - PostgreSQL connection string (required)
- `JWT_SECRET` - Secret key for JWT tokens (required)
- `ADMIN_SECRET_KEY` - Secret key for admin authentication (required)
- `ENV` - Environment name (local/dev/uat/prod)

### AWS S3 Configuration
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (default: us-east-1)
- `S3_ALLOWED_BUCKETS` - Comma-separated list of allowed S3 buckets

### Redis Configuration (Optional)
- `REDIS_URL` - Redis connection URL
- Falls back to PostgreSQL if not configured

### Email Configuration (Optional)
- `RESEND_API_KEY` - Resend API key for email verification
- `FROM_EMAIL` - Sender email address

### OAuth Configuration (Optional)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `GITHUB_CLIENT_ID` - GitHub OAuth client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth client secret

### AI Features (Optional)
- `GEMINI_API_KEY` - Google Gemini API key for AI hints

### Frontend Configuration
- `FRONTEND_URLS` - Comma-separated list of allowed frontend URLs for CORS

## Local Development

### Using Docker

```bash
# Build the Docker image
docker build -t sqlgym:latest .

# Run with environment variables
docker run -p 8080:8080 \
  -e DATABASE_URL="your-database-url" \
  -e JWT_SECRET="your-jwt-secret" \
  -e ADMIN_SECRET_KEY="your-admin-secret" \
  -e ENV="local" \
  sqlgym:latest
```

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
      - ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY}
      - ENV=local
      - REDIS_URL=${REDIS_URL}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_ALLOWED_BUCKETS=${S3_ALLOWED_BUCKETS}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FRONTEND_URLS=http://localhost:5000
```

Then run:
```bash
docker-compose up
```

## Google Cloud Run Deployment

### Using Cloud Build (Recommended)

1. **Configure environment variables in Cloud Run:**

```bash
# Set environment variables
gcloud run services update sqlgym \
  --region=us-central1 \
  --set-env-vars="ENV=prod,DATABASE_URL=your-db-url,JWT_SECRET=your-jwt-secret,ADMIN_SECRET_KEY=your-admin-secret"

# Set secrets (more secure for sensitive data)
gcloud run services update sqlgym \
  --region=us-central1 \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET=jwt-secret:latest,ADMIN_SECRET_KEY=admin-secret:latest"
```

2. **Deploy using Cloud Build:**

```bash
# Trigger Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Or with custom parameters
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_MEMORY=2Gi,_MAX_INSTANCES=20
```

### Manual Deployment

```bash
# Build and push image
docker build -t gcr.io/YOUR_PROJECT_ID/sqlgym:latest .
docker push gcr.io/YOUR_PROJECT_ID/sqlgym:latest

# Deploy to Cloud Run
gcloud run deploy sqlgym \
  --image=gcr.io/YOUR_PROJECT_ID/sqlgym:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --max-instances=10 \
  --set-env-vars="ENV=prod" \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET=jwt-secret:latest"
```

## Environment-Specific Configuration

### Development
```bash
ENV=dev
DB_POOL_SIZE=10
RATE_LIMIT_ENABLED=false
LOG_LEVEL=DEBUG
```

### UAT/Staging
```bash
ENV=uat
DB_POOL_SIZE=20
RATE_LIMIT_ENABLED=true
LOG_LEVEL=INFO
```

### Production
```bash
ENV=prod
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20
RATE_LIMIT_ENABLED=true
LOG_LEVEL=WARNING
CLOUD_RUN_MAX_INSTANCES=50
CLOUD_RUN_MIN_INSTANCES=1
```

## Security Best Practices

1. **Never commit secrets to Git**
   - All `.env` files are gitignored
   - Use Cloud Run secrets or environment variables

2. **Use Cloud Secret Manager (Recommended)**
   ```bash
   # Create secrets
   echo -n "your-database-url" | gcloud secrets create database-url --data-file=-
   echo -n "your-jwt-secret" | gcloud secrets create jwt-secret --data-file=-
   
   # Grant Cloud Run access
   gcloud secrets add-iam-policy-binding database-url \
     --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
     --role=roles/secretmanager.secretAccessor
   ```

3. **Rotate secrets regularly**
   - Update secrets in Secret Manager
   - Redeploy the service to pick up new versions

## Dockerfile Configuration

The main `Dockerfile` includes:
- Python 3.11 slim base image
- Node.js 20 for frontend build
- Multi-stage build for smaller image size
- Frontend built during image creation
- Backend served via Uvicorn

## Cloud Build Configuration

The `cloudbuild.yaml` supports:
- Automatic builds from source
- Image tagging with commit SHA
- Configurable Cloud Run parameters via substitutions
- Cloud Logging integration

## Monitoring and Logs

```bash
# View Cloud Run logs
gcloud run services logs read sqlgym --region=us-central1 --limit=50

# Stream logs in real-time
gcloud run services logs tail sqlgym --region=us-central1

# View build logs
gcloud builds list --limit=10
gcloud builds log BUILD_ID
```

## Troubleshooting

### Configuration validation errors
- Check that all required environment variables are set
- Verify database connection string format
- Ensure secrets are accessible to Cloud Run service account

### Build failures
- Verify Dockerfile syntax
- Check that all dependencies are in requirements.txt
- Ensure Node.js build succeeds

### Runtime errors
- Check Cloud Run logs for startup errors
- Verify environment variables are set correctly
- Confirm database connectivity

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

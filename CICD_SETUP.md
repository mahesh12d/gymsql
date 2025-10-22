# Cloud Build CI/CD Setup Guide

## Overview

This guide sets up a two-stage CI/CD pipeline for SQLGym using Google Cloud Build with automatic deployments to Cloud Run based on branch names:

- **main branch** → Staging environment (`sqlgym-staging`)
- **prod branch** → Production environment (`sqlgym-production`)
  Fsec
  Both environments use Docker containers pushed to Artifact Registry and deployed to Cloud Run with environment-specific configurations.

---

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **APIs Enabled:**
   - Cloud Build API
   - Cloud Run API
   - Artifact Registry API
   - Secret Manager API
3. **Neon Postgres** databases (one for staging, one for production)
4. **Redis** instances (one for staging, one for production)
5. **GitHub Repository** connected to Cloud Build

---

## Step 1: Configure Cloud Build Service Account Permissions

Cloud Build needs permissions to push images to Artifact Registry and deploy to Cloud Run.

```bash
# Set your project ID and get project number
export PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Cloud Build permissions to push to Artifact Registry
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Grant Cloud Build permissions to deploy to Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"

# Grant Cloud Build permissions to act as Cloud Run runtime service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Grant Cloud Build permissions to access Secret Manager (for build-time access if needed)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Optional: Create dedicated service accounts for each environment (recommended for production)**

```bash
# Create staging service account
gcloud iam service-accounts create sqlgym-staging \
  --display-name="SQLGym Staging Service Account"

# Create production service account
gcloud iam service-accounts create sqlgym-production \
  --display-name="SQLGym Production Service Account"

# Grant staging service account access to staging secrets
for SECRET in staging-database-url staging-redis-url staging-jwt-secret staging-admin-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:sqlgym-staging@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done

# Grant production service account access to production secrets
for SECRET in prod-database-url prod-redis-url prod-jwt-secret prod-admin-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:sqlgym-production@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Step 2: Create Artifact Registry Repository

```bash
# Set your project ID
export PROJECT_ID="your-project-id"

# Create Artifact Registry repository
gcloud artifacts repositories create sqlgym \
  --repository-format=docker \
  --location=us-central1 \
  --description="SQLGym Docker images" \
  --project=$PROJECT_ID
```

---

## Step 3: Create Secrets in Secret Manager

### Staging Secrets

```bash
# Database URL (Neon Postgres for staging)
echo -n "postgresql://user:password@neon-staging-host/dbname?sslmode=require" | \
  gcloud secrets create staging-database-url --data-file=-

# Redis URL for staging
echo -n "redis://staging-redis-host:6379/0" | \
  gcloud secrets create staging-redis-url --data-file=-

# JWT Secret for staging
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create staging-jwt-secret --data-file=-

# Admin Secret for staging
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create staging-admin-secret --data-file=-
```

### Production Secrets

```bash
# Database URL (Neon Postgres for production)
echo -n "postgresql://user:password@neon-production-host/dbname?sslmode=require" | \
  gcloud secrets create prod-database-url --data-file=-

# Redis URL for production
echo -n "redis://production-redis-host:6379/0" | \
  gcloud secrets create prod-redis-url --data-file=-

# JWT Secret for production
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create prod-jwt-secret --data-file=-

# Admin Secret for production
echo -n "$(openssl rand -base64 32)" | \
  gcloud secrets create prod-admin-secret --data-file=-
```

### Optional Secrets (if using OAuth, email, or AI features)

```bash
# Google OAuth (if needed)
echo -n "your-google-client-id" | gcloud secrets create google-client-id --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create google-client-secret --data-file=-

# GitHub OAuth (if needed)
echo -n "your-github-client-id" | gcloud secrets create github-client-id --data-file=-
echo -n "your-github-client-secret" | gcloud secrets create github-client-secret --data-file=-

# Email service (if needed)
echo -n "your-resend-api-key" | gcloud secrets create resend-api-key --data-file=-

# AI hints (if needed)
echo -n "your-gemini-api-key" | gcloud secrets create gemini-api-key --data-file=-

# AWS S3 (if needed)
echo -n "your-aws-access-key" | gcloud secrets create aws-access-key-id --data-file=-
echo -n "your-aws-secret-key" | gcloud secrets create aws-secret-access-key --data-file=-
```

---

## Step 4: Grant Secret Access to Cloud Run

```bash
# Get the project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Cloud Run service account access to secrets
for SECRET in staging-database-url staging-redis-url staging-jwt-secret staging-admin-secret \
              prod-database-url prod-redis-url prod-jwt-secret prod-admin-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Step 5: Create Cloud Build Triggers

### Trigger 1: Staging (main branch)

```bash
gcloud builds triggers create github \
  --name="deploy-staging" \
  --repo-name="your-repo-name" \
  --repo-owner="your-github-username" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.staging.yaml" \
  --description="Deploy to staging on main branch push"
```

### Trigger 2: Production (prod branch)

```bash
gcloud builds triggers create github \
  --name="deploy-production" \
  --repo-name="your-repo-name" \
  --repo-owner="your-github-username" \
  --branch-pattern="^prod$" \
  --build-config="cloudbuild.prod.yaml" \
  --description="Deploy to production on prod branch push"
```

### Alternative: Create Triggers via Console

1. Go to **Cloud Build** → **Triggers** in Google Cloud Console
2. Click **Create Trigger**

**For Staging:**

- Name: `deploy-staging`
- Event: Push to a branch
- Repository: Your GitHub repo
- Branch: `^main$`
- Cloud Build configuration file: `cloudbuild.staging.yaml`

**For Production:**

- Name: `deploy-production`
- Event: Push to a branch
- Repository: Your GitHub repo
- Branch: `^prod$`
- Cloud Build configuration file: `cloudbuild.prod.yaml`

---

## Step 6: Update Optional Environment Variables

If you need to add more environment variables (non-secret), update the cloudbuild files:

### Edit `cloudbuild.staging.yaml` or `cloudbuild.prod.yaml`:

```yaml
- "--set-env-vars=ENV=staging,FRONTEND_URLS=https://staging.example.com"
- "--update-secrets=DATABASE_URL=staging-database-url:latest,..."
```

Or update via command line after deployment:

```bash
# Staging
gcloud run services update sqlgym-staging \
  --region=us-central1 \
  --set-env-vars="FRONTEND_URLS=https://staging.example.com,AWS_REGION=us-east-1"

# Production
gcloud run services update sqlgym-production \
  --region=us-central1 \
  --set-env-vars="FRONTEND_URLS=https://example.com,AWS_REGION=us-east-1"
```

---

## Step 7: Deploy

### Initial Deployment

Manually trigger the first build:

```bash
# Deploy staging
gcloud builds submit --config=cloudbuild.staging.yaml

# Deploy production
gcloud builds submit --config=cloudbuild.prod.yaml
```

### Automatic Deployments

Once triggers are configured:

1. **Push to `main` branch** → Automatically deploys to staging
2. **Push to `prod` branch** → Automatically deploys to production

---

## Environment Configuration Reference

### Staging Environment

- **Service Name:** `sqlgym-staging`
- **Branch:** `main`
- **Memory:** 1Gi
- **CPU:** 1
- **Max Instances:** 5
- **Min Instances:** 0
- **Secrets:**
  - `staging-database-url`
  - `staging-redis-url`
  - `staging-jwt-secret`
  - `staging-admin-secret`

### Production Environment

- **Service Name:** `sqlgym-production`
- **Branch:** `prod`
- **Memory:** 2Gi
- **CPU:** 2
- **Max Instances:** 20
- **Min Instances:** 1
- **Secrets:**
  - `prod-database-url`
  - `prod-redis-url`
  - `prod-jwt-secret`
  - `prod-admin-secret`

---

## Monitoring and Logs

### View Build Logs

```bash
# List recent builds
gcloud builds list --limit=10

# View specific build logs
gcloud builds log BUILD_ID
```

### View Cloud Run Logs

```bash
# Staging logs
gcloud run services logs read sqlgym-staging --region=us-central1 --limit=50

# Production logs
gcloud run services logs read sqlgym-production --region=us-central1 --limit=50
```

### Stream Logs in Real-Time

```bash
# Staging
gcloud run services logs tail sqlgym-staging --region=us-central1

# Production
gcloud run services logs tail sqlgym-production --region=us-central1
```

---

## Workflow

### Typical Development Workflow

1. **Feature Development:**

   ```bash
   git checkout -b feature/new-feature
   # Make changes
   git commit -m "Add new feature"
   git push origin feature/new-feature
   # Create PR to main
   ```

2. **Staging Deployment:**

   ```bash
   # After PR is merged to main
   # Cloud Build automatically builds and deploys to staging
   ```

3. **Production Release:**
   ```bash
   # After testing in staging
   git checkout prod
   git merge main
   git push origin prod
   # Cloud Build automatically builds and deploys to production
   ```

---

## Rollback Strategy

### Rollback to Previous Revision

```bash
# List revisions
gcloud run revisions list --service=sqlgym-production --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic sqlgym-production \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

### Emergency Rollback (Same Code, Different Env)

```bash
# Redeploy previous commit
git revert HEAD
git push origin prod
```

---

## Troubleshooting

### Build Fails

1. Check Cloud Build logs: `gcloud builds log BUILD_ID`
2. Verify Dockerfile builds locally: `docker build -t test .`
3. Check Cloud Build service account permissions

### Deployment Fails

1. Check secrets are created: `gcloud secrets list`
2. Verify IAM permissions: `gcloud secrets get-iam-policy SECRET_NAME`
3. Check Cloud Run logs for startup errors

### Application Errors

1. Check environment variables: `gcloud run services describe sqlgym-staging`
2. Verify database connectivity from Cloud Run
3. Check Secret Manager for correct values

---

## Security Best Practices

1. ✅ **Use Secret Manager** for all sensitive data
2. ✅ **Separate secrets** for staging and production
3. ✅ **Rotate secrets** regularly
4. ✅ **Use least-privilege IAM** roles
5. ✅ **Enable Cloud Audit Logs** for Secret Manager
6. ✅ **Use VPC Connector** for private database access (if needed)
7. ✅ **Set up monitoring** and alerting

---

## Cost Optimization

- **Staging:** Min instances = 0 (scales to zero when idle)
- **Production:** Min instances = 1 (always available, faster response)
- **Adjust resources** based on actual usage
- **Use Cloud Run's** per-request billing model
- **Monitor costs** in Cloud Console

---

## Additional Resources

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

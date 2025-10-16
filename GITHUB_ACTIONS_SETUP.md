# GitHub Actions CI/CD Setup

This document explains how to set up the automated CI/CD pipeline using GitHub Actions for SQLGym's three-stage deployment.

## 🎯 Overview

The GitHub Actions pipeline automatically deploys your application when you push code to specific branches:

| Branch | Environment | Backend Service | Vercel Environment |
|--------|-------------|-----------------|-------------------|
| `develop` | Development | `sqlgym-backend-dev` | Preview |
| `staging` | UAT/Staging | `sqlgym-backend-uat` | Preview |
| `main` | Production | `sqlgym-backend-prod` | Production |

## 🔄 Deployment Flow

```
Push to Branch
    ↓
GitHub Actions Triggered
    ↓
Build & Deploy Backend to Cloud Run
    ↓
Backend URL Retrieved
    ↓
Build & Deploy Frontend to Vercel (with backend URL)
    ↓
Deployment URLs Posted as Commit Comment
```

## 📋 Prerequisites

Before setting up GitHub Actions, you need:

1. **GitHub Repository** with your code
2. **Google Cloud Project** with Cloud Run enabled
3. **Vercel Account** with your frontend project
4. Admin access to your GitHub repository (to add secrets)

## 🔐 Required GitHub Secrets

You need to add the following secrets to your GitHub repository:

### How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### Secret List

#### 1. `GCP_SERVICE_ACCOUNT_KEY`

**What it is:** JSON key for a Google Cloud service account that can deploy to Cloud Run.

**How to get it:**

```bash
# 1. Create a service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# 2. Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 3. Create and download the key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. Copy the entire contents of key.json and paste as the secret value
cat key.json
```

**Important:** Delete `key.json` after adding to GitHub Secrets for security.

#### 2. `GCP_PROJECT_ID`

**What it is:** Your Google Cloud Project ID.

**How to get it:**

```bash
gcloud config get-value project
```

Or find it in the [Google Cloud Console](https://console.cloud.google.com).

#### 3. `VERCEL_TOKEN`

**What it is:** Authentication token for deploying to Vercel.

**How to get it:**

1. Go to [Vercel Account Settings](https://vercel.com/account/tokens)
2. Click **Create Token**
3. Name it "GitHub Actions"
4. Copy the token value

#### 4. `VERCEL_ORG_ID`

**What it is:** Your Vercel organization/team ID.

**How to get it:**

```bash
# Install Vercel CLI if you haven't
npm i -g vercel

# Login to Vercel
vercel login

# Link your project (run in your project directory)
vercel link

# The .vercel/project.json file will contain orgId
cat .vercel/project.json
```

Copy the `orgId` value from the JSON output.

#### 5. `VERCEL_PROJECT_ID`

**What it is:** Your Vercel project ID.

**How to get it:**

Same as above - it's in the `.vercel/project.json` file as `projectId`.

```bash
cat .vercel/project.json
```

## ⚙️ Environment Variables in Cloud Run

The GitHub Actions workflows will deploy to Cloud Run, but you still need to set the environment variables for your application runtime.

### Set Environment Variables

For each environment, set the required variables:

```bash
# Development
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --update-env-vars="DATABASE_URL=postgresql://...,JWT_SECRET=...,ADMIN_SECRET_KEY=...,AWS_ACCESS_KEY_ID=...,AWS_SECRET_ACCESS_KEY=...,S3_ALLOWED_BUCKETS=..."

# UAT/Staging
gcloud run services update sqlgym-backend-uat \
  --region=us-central1 \
  --update-env-vars="DATABASE_URL=postgresql://...,JWT_SECRET=...,ADMIN_SECRET_KEY=...,AWS_ACCESS_KEY_ID=...,AWS_SECRET_ACCESS_KEY=...,S3_ALLOWED_BUCKETS=..."

# Production
gcloud run services update sqlgym-backend-prod \
  --region=us-central1 \
  --update-env-vars="DATABASE_URL=postgresql://...,JWT_SECRET=...,ADMIN_SECRET_KEY=...,AWS_ACCESS_KEY_ID=...,AWS_SECRET_ACCESS_KEY=...,S3_ALLOWED_BUCKETS=..."
```

**Or use environment files:**

Create `env.dev.yaml`, `env.uat.yaml`, `env.prod.yaml`:

```yaml
DATABASE_URL: "postgresql://..."
JWT_SECRET: "your-secret-here"
ADMIN_SECRET_KEY: "your-admin-secret"
AWS_ACCESS_KEY_ID: "your-aws-key"
AWS_SECRET_ACCESS_KEY: "your-aws-secret"
S3_ALLOWED_BUCKETS: "bucket1,bucket2"
REDIS_URL: "redis://..."
GOOGLE_CLIENT_ID: "..."
GOOGLE_CLIENT_SECRET: "..."
FRONTEND_URLS: "https://your-frontend.vercel.app"
```

Then deploy:

```bash
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --env-vars-file=env.dev.yaml
```

## 🎨 Environment Variables in Vercel

Set frontend environment variables in Vercel Dashboard:

1. Go to your Vercel project
2. Click **Settings** → **Environment Variables**
3. Add variables for each environment:

| Variable | Development | Preview | Production |
|----------|-------------|---------|------------|
| `VITE_API_URL` | Your dev backend URL | Your UAT backend URL | Your prod backend URL |

**Note:** The GitHub Actions workflow automatically passes `VITE_API_URL` during build, but you can also set it in Vercel for manual deployments.

## 🚀 How to Use

### Development Workflow

```bash
# Work on develop branch
git checkout develop

# Make changes
git add .
git commit -m "Add new feature"

# Push to trigger deployment
git push origin develop
```

GitHub Actions will automatically:
1. Build and deploy backend to `sqlgym-backend-dev`
2. Build and deploy frontend to Vercel (preview)
3. Comment on your commit with deployment URLs

### UAT/Staging Workflow

```bash
# Merge develop into staging
git checkout staging
git merge develop

# Push to trigger UAT deployment
git push origin staging
```

### Production Workflow

```bash
# Merge staging into main
git checkout main
git merge staging

# Push to trigger production deployment
git push origin main
```

**⚠️ Important:** Always follow the flow: `develop` → `staging` → `main`

## 📊 Monitoring Deployments

### View Workflow Status

1. Go to your GitHub repository
2. Click **Actions** tab
3. See all workflow runs, logs, and status

### View Deployment URLs

After each deployment, GitHub Actions posts a comment on the commit with:
- Backend URL (Cloud Run)
- Frontend URL (Vercel)

### Check Cloud Run Logs

```bash
gcloud run services logs read sqlgym-backend-dev --region=us-central1
gcloud run services logs read sqlgym-backend-uat --region=us-central1
gcloud run services logs read sqlgym-backend-prod --region=us-central1
```

### Check Vercel Logs

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click your project
3. Click **Deployments**
4. Click a deployment to see logs

## 🔧 Troubleshooting

### Deployment Fails with "Permission Denied"

**Solution:** Ensure your service account has the correct IAM roles:
- `roles/run.admin`
- `roles/storage.admin`
- `roles/iam.serviceAccountUser`

### Vercel Deployment Fails

**Solution:** 
1. Verify `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` are correct
2. Ensure your Vercel token hasn't expired
3. Check that your Vercel project is linked correctly

### Environment Variables Not Working

**Solution:**
1. Verify variables are set in Cloud Run: `gcloud run services describe sqlgym-backend-dev --region=us-central1`
2. Check Vercel environment variables in dashboard
3. Redeploy after setting variables

### Backend URL Not Passed to Frontend

**Solution:** The workflow retrieves the backend URL after deployment and passes it to Vercel. If this fails:
1. Check the GitHub Actions logs for the "Get Cloud Run URL" step
2. Verify the Cloud Run service was deployed successfully
3. Ensure the service name matches in the workflow file

## 🎯 Summary

Once set up, your deployment process is completely automated:

1. **Push to `develop`** → Deploys to Development
2. **Push to `staging`** → Deploys to UAT
3. **Push to `main`** → Deploys to Production

No manual commands needed! Just push code and GitHub Actions handles everything.

## 📝 Comparison: GitHub Actions vs Manual Cloud Build

| Aspect | Manual Cloud Build | GitHub Actions |
|--------|-------------------|----------------|
| Deployment | Run `gcloud builds submit` manually | Automatic on git push |
| Setup Needed | gcloud CLI on your machine | GitHub Secrets (one-time) |
| CI/CD | Manual | Fully automated |
| Visibility | Terminal output only | GitHub UI with history |
| Team Collaboration | Everyone needs gcloud CLI | Works for all team members |
| Approval Gates | None | Can add approval steps |
| Notifications | None | GitHub notifications + commit comments |

## 🔒 Security Best Practices

1. **Never commit secrets** to your repository
2. **Rotate service account keys** periodically
3. **Use least-privilege IAM roles** for service accounts
4. **Enable branch protection** on `main` and `staging` branches
5. **Review deployment logs** regularly
6. **Use different secrets** for each environment (dev/uat/prod)

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vercel CLI Documentation](https://vercel.com/docs/cli)
- [Environment Configuration Guide](./ENVIRONMENT_CONFIGURATION.md)

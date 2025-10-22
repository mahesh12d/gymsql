# 🚀 Quick Start: GitHub Actions CI/CD

## What's Already Set Up ✅

I've configured everything that can be done automatically:

1. ✅ **GitHub Actions Workflows** - 3 workflow files created
   - `.github/workflows/deploy-dev.yml` (main branch → dev environment)
   - `.github/workflows/deploy-uat.yml` (staging branch → uat environment)
   - `.github/workflows/deploy-prod.yml` (production branch → prod environment)

2. ✅ **Environment Templates** - Already exist
   - `.env.dev.template`
   - `.env.uat.template`
   - `.env.prod.template`

3. ✅ **Documentation** - Complete setup guides created
   - `GITHUB_ACTIONS_SETUP.md` - Detailed setup instructions
   - `SETUP_CHECKLIST.md` - Step-by-step checklist
   - `ENVIRONMENT_CONFIGURATION.md` - Environment configuration guide

4. ✅ **Git Configuration** - `.gitignore` properly configured

## What You Need to Do 🔧

### Quick Version (15 minutes)

**1. You're already on the right branch!**
- `main` branch → deploys to **development** (you're here now!)
- Create `staging` and `production` branches only when you need them

**2. Add 5 GitHub Secrets** to https://github.com/mahesh12d/gymsql/settings/secrets/actions:
- `GCP_SERVICE_ACCOUNT_KEY` - Get from Google Cloud (see below)
- `GCP_PROJECT_ID` - Your GCP project ID
- `VERCEL_TOKEN` - Get from https://vercel.com/account/tokens
- `VERCEL_ORG_ID` - Get from Vercel CLI: `vercel link` then `cat .vercel/project.json`
- `VERCEL_PROJECT_ID` - Same as above

**3. Set environment variables in Cloud Run & Vercel** (see full guide)

### Get Google Cloud Service Account Key

Run this to create the service account and get the key:

```bash
# Set your project ID
PROJECT_ID=$(gcloud config get-value project)

# Create service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com

# Show key (copy entire JSON output)
cat key.json

# Delete the file after copying
rm key.json
```

Copy the entire JSON content as `GCP_SERVICE_ACCOUNT_KEY` in GitHub Secrets.

## How It Works 🔄

Once set up, deployment is automatic:

```bash
# Deploy to Development (you're already on main!)
git commit -am "Your changes"
git push origin main  # ← Automatic dev deployment!

# Deploy to UAT (when ready)
git checkout staging  # or: git checkout -b staging main (first time)
git merge main
git push origin staging  # ← Automatic UAT deployment!

# Deploy to Production (when UAT passes)
git checkout production  # or: git checkout -b production staging (first time)
git merge staging
git push origin production  # ← Automatic prod deployment!
```

GitHub Actions will:
1. Build and deploy backend to Cloud Run
2. Build and deploy frontend to Vercel
3. Post deployment URLs as commit comments

## 📋 Full Instructions

See `SETUP_CHECKLIST.md` for the complete step-by-step guide with all commands and troubleshooting.

## Where Environment Variables Go

| Location | What Goes There | Used By |
|----------|----------------|---------|
| **GitHub Secrets** | Deployment credentials (GCP key, Vercel token, etc.) | GitHub Actions workflow |
| **Cloud Run** | Backend config (DATABASE_URL, JWT_SECRET, etc.) | Your backend app |
| **Vercel** | Frontend config (VITE_API_URL) | Your frontend app |

## Next Steps

1. Follow the commands above to set up GitHub Secrets
2. See `SETUP_CHECKLIST.md` for complete setup
3. Test with a push to `develop` branch
4. Monitor at https://github.com/mahesh12d/gymsql/actions

That's it! Once configured, all deployments are automatic. 🎉

# GitHub Actions CI/CD Setup Checklist

This checklist will guide you through setting up the automated CI/CD pipeline. Complete each step in order.

## ✅ What's Already Done

- [x] GitHub Actions workflow files created (`.github/workflows/`)
- [x] Environment templates created (`.env.dev.template`, `.env.uat.template`, `.env.prod.template`)
- [x] Git branches created locally (`develop`, `staging`, `main`)
- [x] `.gitignore` configured to exclude sensitive files
- [x] Documentation created (`GITHUB_ACTIONS_SETUP.md`)

## 📋 What You Need to Do

### Step 1: Push Branches to GitHub (5 minutes)

```bash
# Push all branches to GitHub
git push origin develop
git push origin staging
git push origin main
```

**Why:** GitHub Actions triggers on pushes to these branches.

---

### Step 2: Create Google Cloud Service Account (10 minutes)

```bash
# 1. Create service account
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer"

# 2. Get your project ID
PROJECT_ID=$(gcloud config get-value project)
echo "Your project ID: $PROJECT_ID"

# 3. Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# 4. Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-deployer@$PROJECT_ID.iam.gserviceaccount.com

# 5. Display the key (copy this for GitHub Secrets)
cat github-actions-key.json

# 6. IMPORTANT: Delete the key file after copying
rm github-actions-key.json
```

**Save these values:**
- ✏️ Service account JSON (entire content from step 5)
- ✏️ Project ID (from step 2)

---

### Step 3: Get Vercel Credentials (5 minutes)

#### Get Vercel Token:
1. Go to https://vercel.com/account/tokens
2. Click "Create Token"
3. Name it "GitHub Actions"
4. Copy the token

#### Get Vercel Organization and Project IDs:
```bash
# Install Vercel CLI if needed
npm install -g vercel

# Login to Vercel
vercel login

# Link your project (run in project directory)
vercel link

# Get the IDs
cat .vercel/project.json
```

**Save these values:**
- ✏️ Vercel Token
- ✏️ Organization ID (`orgId` from project.json)
- ✏️ Project ID (`projectId` from project.json)

---

### Step 4: Add GitHub Secrets (5 minutes)

1. Go to your GitHub repository: https://github.com/mahesh12d/gymsql
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:

| Secret Name | Value | Where to Get It |
|------------|-------|-----------------|
| `GCP_SERVICE_ACCOUNT_KEY` | Service account JSON | Step 2 (entire JSON content) |
| `GCP_PROJECT_ID` | Your GCP project ID | Step 2 |
| `VERCEL_TOKEN` | Vercel deployment token | Step 3 |
| `VERCEL_ORG_ID` | Vercel organization ID | Step 3 (from .vercel/project.json) |
| `VERCEL_PROJECT_ID` | Vercel project ID | Step 3 (from .vercel/project.json) |

---

### Step 5: Set Cloud Run Environment Variables (10 minutes)

Create environment files for each stage:

**Create `env.dev.yaml`:**
```yaml
DATABASE_URL: "postgresql://user:password@host:5432/sqlgym_dev"
JWT_SECRET: "your-dev-jwt-secret-here"
ADMIN_SECRET_KEY: "your-dev-admin-secret-here"
AWS_ACCESS_KEY_ID: "your-aws-key"
AWS_SECRET_ACCESS_KEY: "your-aws-secret"
AWS_REGION: "us-east-1"
S3_ALLOWED_BUCKETS: "dev-bucket-1,dev-bucket-2"
REDIS_URL: "redis://your-redis-dev-url"
GOOGLE_CLIENT_ID: "your-google-client-id"
GOOGLE_CLIENT_SECRET: "your-google-client-secret"
GITHUB_CLIENT_ID: "your-github-client-id"
GITHUB_CLIENT_SECRET: "your-github-client-secret"
GEMINI_API_KEY: "your-gemini-api-key"
FRONTEND_URLS: "https://your-dev-frontend.vercel.app"
```

**Create `env.uat.yaml` and `env.prod.yaml`** with their respective values.

Then deploy the environment variables:

```bash
# Development
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --env-vars-file=env.dev.yaml

# UAT
gcloud run services update sqlgym-backend-uat \
  --region=us-central1 \
  --env-vars-file=env.uat.yaml

# Production
gcloud run services update sqlgym-backend-prod \
  --region=us-central1 \
  --env-vars-file=env.prod.yaml
```

---

### Step 6: Set Vercel Environment Variables (5 minutes)

1. Go to https://vercel.com/dashboard
2. Select your project
3. Click **Settings** → **Environment Variables**
4. Add `VITE_API_URL` for each environment:
   - **Development**: Your dev Cloud Run URL
   - **Preview**: Your UAT Cloud Run URL
   - **Production**: Your prod Cloud Run URL

---

### Step 7: Test the Pipeline (5 minutes)

```bash
# Test development deployment
git checkout develop
echo "# Test" >> README.md
git add README.md
git commit -m "Test GitHub Actions deployment"
git push origin develop
```

**What happens:**
1. GitHub Actions automatically triggers
2. Backend deploys to Cloud Run (dev)
3. Frontend deploys to Vercel (preview)
4. Deployment URLs posted as commit comment

**Check status:**
1. Go to https://github.com/mahesh12d/gymsql/actions
2. See the "Deploy to Development" workflow running
3. Check the commit comment for deployment URLs

---

## 🎉 Success Criteria

You'll know it's working when:
- ✅ Pushing to `develop` triggers dev deployment
- ✅ Pushing to `staging` triggers UAT deployment
- ✅ Pushing to `main` triggers production deployment
- ✅ Deployment URLs appear as commit comments
- ✅ Applications are accessible at the URLs

---

## 🆘 Troubleshooting

### GitHub Actions fails with "Permission denied"
**Solution:** Check that service account has all required IAM roles (step 2)

### Vercel deployment fails
**Solution:** Verify `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID` are correct

### Backend URL not passed to frontend
**Solution:** Check GitHub Actions logs for "Get Cloud Run URL" step

### Environment variables not working
**Solution:** Verify they're set in Cloud Run and Vercel dashboards

---

## 📚 Reference Documents

- **Full setup guide:** `GITHUB_ACTIONS_SETUP.md`
- **Environment config:** `ENVIRONMENT_CONFIGURATION.md`
- **Project overview:** `replit.md`

---

## ⏱️ Estimated Total Time: 45 minutes

Most of this is one-time setup. After completion, all deployments are automatic!

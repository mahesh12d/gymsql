# ✅ Cloud Run Deployment - Fixed

## The Issue

You were getting:
```
failed to build: for Python, provide a main.py or app.py file or set an entrypoint with "GOOGLE_ENTRYPOINT" env var or by creating a "Procfile" file
```

This happened because Google Cloud Run detected your `requirements.txt` and tried to use the Python **buildpack** instead of your **Dockerfile**.

## The Fix

I've created a **Procfile** that tells the buildpack how to start your app. Now you have **two deployment options**:

---

## 🎯 Option 1: Buildpack Deployment (Backend Only)

**What it does:** Deploys ONLY the Python FastAPI backend using the buildpack.

**When to use:** If you're deploying the frontend separately (Vercel, Netlify, Cloudflare Pages, etc.)

**How to deploy:**

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Deploy
gcloud run deploy sqlgym-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300
```

**What happens:**
- ✅ Uses the `Procfile` to start the backend
- ✅ Runs: `gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker`
- ❌ Does NOT build/serve the frontend

---

## 🐳 Option 2: Docker Deployment (Full Stack)

**What it does:** Builds the React frontend AND serves it with the Python backend in one container.

**When to use:** For a complete all-in-one deployment.

**How to deploy:**

### Method A: Using the deployment script

```bash
# Set your project ID
export GCLOUD_PROJECT_ID="your-project-id"

# Run the deployment script
./deploy-cloudrun.sh
```

### Method B: Manual command

```bash
# Build Docker image locally first
docker build -t sqlgym .

# Test locally (optional)
docker run -p 8080:8080 -e PORT=8080 sqlgym

# Deploy to Cloud Run with Docker
gcloud run deploy sqlgym \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --port 8080
```

**What happens:**
- ✅ Builds the React frontend (`npm run build`)
- ✅ Starts the FastAPI backend with Gunicorn
- ✅ Backend serves the built frontend files
- ✅ Everything runs in one container

---

## 🔐 Setting Environment Variables

After deployment, set your secrets:

```bash
# Method 1: Direct environment variables (less secure)
gcloud run services update sqlgym --region us-central1 \
  --set-env-vars "\
DATABASE_URL=postgresql://...,\
JWT_SECRET=your-jwt-secret,\
ADMIN_SECRET_KEY=your-admin-key,\
RESEND_API_KEY=your-resend-key,\
GEMINI_API_KEY=your-gemini-key"

# Method 2: Using Secret Manager (more secure, recommended)
# Create secrets
echo -n "postgresql://..." | gcloud secrets create DATABASE_URL --data-file=-
echo -n "your-jwt-secret" | gcloud secrets create JWT_SECRET --data-file=-
echo -n "your-admin-key" | gcloud secrets create ADMIN_SECRET_KEY --data-file=-

# Grant access to Cloud Run
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets...

# Update service to use secrets
gcloud run services update sqlgym --region us-central1 \
  --update-secrets="\
DATABASE_URL=DATABASE_URL:latest,\
JWT_SECRET=JWT_SECRET:latest,\
ADMIN_SECRET_KEY=ADMIN_SECRET_KEY:latest,\
RESEND_API_KEY=RESEND_API_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## 🎉 What's Been Fixed

1. ✅ **Created `Procfile`** - Tells buildpack how to start the app
2. ✅ **Created `deploy-cloudrun.sh`** - Easy deployment script
3. ✅ **Your Dockerfile is ready** - Already configured for full-stack deployment

---

## 📋 Recommended Approach

For **development/testing**: Use Option 1 (Buildpack, backend only) + deploy frontend to Vercel

For **production**: Use Option 2 (Docker, full stack) for simplicity

---

## 🆘 If You Still Get Errors

### Error: "Dockerfile not found"
Make sure you're in the project root directory where the Dockerfile exists.

### Error: "Build failed"
Check that all required files exist:
- `Dockerfile` ✓
- `requirements.txt` ✓
- `package.json` ✓
- `api/` directory ✓
- `client/` directory ✓

### Error: "Cannot connect to database"
Make sure you've set the `DATABASE_URL` environment variable after deployment.

---

## 🔍 Quick Test

After deployment, test your endpoints:

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe sqlgym --region us-central1 --format="value(status.url)")

# Test the API
curl $SERVICE_URL/

# Should return:
# {"message":"SQLGym API","version":"1.0.0","status":"running","service":"FastAPI Backend"}
```

---

## 💡 Pro Tips

1. **Use Cloud Build for CI/CD**: The `cloudbuild.yaml` and `cloudbuild.prod.yaml` files are already set up for automated deployments

2. **Enable CORS**: Make sure your `FRONTEND_URLS` environment variable includes your frontend domain

3. **Monitor costs**: Cloud Run bills by request. Set max instances to control costs

4. **Use Cloud Run secrets**: More secure than environment variables for sensitive data

---

Need help? Check the detailed guides:
- `CLOUD_RUN_DEPLOYMENT.md` - Complete deployment guide
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Production checklist
- `PRODUCTION_SECURITY_GUIDE.md` - Security best practices

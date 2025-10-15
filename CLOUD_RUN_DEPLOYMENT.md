# Google Cloud Run Deployment Guide for SQLGym

Complete guide for deploying SQLGym backend on Google Cloud Run with frontend on Vercel/Cloudflare.

---

## 🚀 Prerequisites

1. **Google Cloud Account**
   - Sign up at [cloud.google.com](https://cloud.google.com)
   - Free tier: $300 credit for 90 days

2. **Install Google Cloud CLI**
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Windows
   # Download from https://cloud.google.com/sdk/docs/install
   
   # Linux
   curl https://sdk.cloud.google.com | bash
   ```

3. **Authenticate**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

---

## 📦 Method 1: Quick Deploy (Recommended for First Time)

### Step 1: Prepare Your Project

1. **Ensure all files are ready**
   - ✅ `Dockerfile.cloudrun`
   - ✅ `requirements.txt`
   - ✅ `api/` directory with backend code

### Step 2: Deploy from Local Machine

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Deploy to Cloud Run (builds and deploys in one command)
gcloud run deploy sqlgym-backend \
  --source . \
  --dockerfile Dockerfile.cloudrun \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 10 \
  --min-instances 0
```

**This will:**
- Build your Docker image
- Push to Google Container Registry
- Deploy to Cloud Run
- Give you a URL like: `https://sqlgym-backend-xxxxx-uc.a.run.app`

### Step 3: Set Environment Variables

```bash
# Set environment variables
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --set-env-vars "\
DATABASE_URL=your_database_url,\
FRONTEND_URL=https://your-app.vercel.app,\
RESEND_API_KEY=your_resend_key,\
FROM_EMAIL=noreply@yourdomain.com,\
GEMINI_API_KEY=your_gemini_key,\
SECRET_KEY=your_secret_key,\
ADMIN_SECRET_KEY=your_admin_secret"
```

Or use Secret Manager (more secure):

```bash
# Create secrets
echo -n "your_database_url" | gcloud secrets create DATABASE_URL --data-file=-
echo -n "your_resend_key" | gcloud secrets create RESEND_API_KEY --data-file=-

# Grant access to Cloud Run service
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update service to use secrets
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,RESEND_API_KEY=RESEND_API_KEY:latest"
```

---

## 🔄 Method 2: CI/CD with GitHub (Recommended for Production)

### Step 1: Connect GitHub Repository

1. **Go to Cloud Console**
   - Navigate to [Cloud Build → Triggers](https://console.cloud.google.com/cloud-build/triggers)
   - Click "Connect Repository"
   - Select GitHub and authorize
   - Choose your SQLGym repository

### Step 2: Create Build Trigger

1. **Configure Trigger**
   - Name: `sqlgym-backend-deploy`
   - Event: Push to branch
   - Branch: `^main$` or `^master$`
   - Configuration: Cloud Build configuration file
   - Location: `/cloudbuild.yaml`

2. **Click "Create"**

### Step 3: Push to Deploy

```bash
git add .
git commit -m "Deploy to Cloud Run"
git push origin main
```

Every push to `main` will automatically:
- Build Docker image
- Push to Container Registry
- Deploy to Cloud Run

---

## 🗄️ Database Setup

### Option 1: Cloud SQL (Recommended)

```bash
# Create PostgreSQL instance
gcloud sql instances create sqlgym-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create sqlgym \
  --instance=sqlgym-db

# Create user
gcloud sql users create sqlgym \
  --instance=sqlgym-db \
  --password=YOUR_SECURE_PASSWORD

# Get connection name
gcloud sql instances describe sqlgym-db --format='value(connectionName)'
```

**Connect Cloud Run to Cloud SQL:**

```bash
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --add-cloudsql-instances=PROJECT_ID:us-central1:sqlgym-db \
  --set-env-vars="DATABASE_URL=postgresql://sqlgym:PASSWORD@/sqlgym?host=/cloudsql/PROJECT_ID:us-central1:sqlgym-db"
```

### Option 2: External Database (Render, Neon, etc.)

Just set the `DATABASE_URL` environment variable:

```bash
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --set-env-vars="DATABASE_URL=postgresql://user:pass@host:port/db"
```

---

## 🔧 Production Configuration

### Memory & CPU Tuning

```bash
# For production workloads
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 80 \
  --max-instances 100 \
  --min-instances 1  # Keeps 1 instance warm (reduces cold starts)
```

### Custom Domain

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service sqlgym-backend \
  --region us-central1 \
  --domain api.yourdomain.com
```

Then add DNS records as instructed.

---

## 🔐 Security Best Practices

### 1. Use Secret Manager

Store sensitive data in Secret Manager instead of environment variables:

```bash
# Create secrets
gcloud secrets create DATABASE_URL --replication-policy="automatic"
echo -n "your_database_url" | gcloud secrets versions add DATABASE_URL --data-file=-

# Use in Cloud Run
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest"
```

### 2. Restrict Access

```bash
# Remove public access (require authentication)
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --no-allow-unauthenticated

# Allow specific service accounts
gcloud run services add-iam-policy-binding sqlgym-backend \
  --region us-central1 \
  --member="serviceAccount:frontend@PROJECT.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### 3. Enable Binary Authorization

Ensures only approved container images are deployed.

---

## 📊 Monitoring & Logging

### View Logs

```bash
# Real-time logs
gcloud run services logs tail sqlgym-backend \
  --region us-central1

# Or visit Cloud Console
# Logging → Logs Explorer
```

### Set Up Alerts

1. Go to **Monitoring → Alerting**
2. Create alert for:
   - Error rate > 5%
   - Response time > 2s
   - Memory usage > 80%

---

## 💰 Cost Optimization

### Pricing Breakdown

Cloud Run pricing (as of 2025):
- **Free tier**: 2 million requests/month, 360,000 GB-seconds
- **Requests**: $0.40 per million requests
- **Memory**: $0.0000025 per GB-second
- **CPU**: $0.00001 per vCPU-second

### Tips to Reduce Costs

1. **Set max-instances**: Prevent runaway costs
2. **Use min-instances=0**: Pay only when serving requests
3. **Optimize memory**: Start with 512Mi, increase if needed
4. **Use caching**: Reduce database calls with Redis

```bash
# Cost-optimized configuration
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5
```

---

## 🧪 Testing Your Deployment

### Health Check

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe sqlgym-backend \
  --region us-central1 \
  --format 'value(status.url)')

# Test endpoints
curl $SERVICE_URL/
curl $SERVICE_URL/api/problems
curl $SERVICE_URL/docs  # Swagger UI
```

### Load Testing

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Test with 1000 requests, 10 concurrent
ab -n 1000 -c 10 $SERVICE_URL/
```

---

## 🔄 Update & Rollback

### Deploy New Version

```bash
# Deploy from source
gcloud run deploy sqlgym-backend \
  --source . \
  --dockerfile Dockerfile.cloudrun \
  --region us-central1
```

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service sqlgym-backend --region us-central1

# Rollback to specific revision
gcloud run services update-traffic sqlgym-backend \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

---

## 🌐 Connect Frontend

### Update Frontend Environment Variable

**Vercel:**
```bash
vercel env add VITE_API_URL production
# Enter: https://sqlgym-backend-xxxxx-uc.a.run.app
```

**Cloudflare:**
Add in Pages settings:
```
VITE_API_URL=https://sqlgym-backend-xxxxx-uc.a.run.app
```

### Update Backend CORS

```bash
gcloud run services update sqlgym-backend \
  --region us-central1 \
  --set-env-vars="FRONTEND_URL=https://your-app.vercel.app"
```

---

## 🐛 Troubleshooting

### Container failed to start

**Problem**: "Container failed to start. Failed to start and then listen on the port defined by the PORT environment variable."

**Solution**: Ensure your app listens on `0.0.0.0` and port from `$PORT` env var.

### Out of Memory

**Problem**: Container restarts due to OOM

**Solution**: Increase memory:
```bash
gcloud run services update sqlgym-backend --memory 2Gi --region us-central1
```

### Slow Cold Starts

**Problem**: First request after inactivity is slow

**Solutions**:
- Set `--min-instances 1` (costs more)
- Enable startup CPU boost: `--cpu-boost`
- Optimize Docker image size

### Database Connection Issues

**Problem**: Can't connect to Cloud SQL

**Solution**: Ensure Cloud SQL connector is added:
```bash
gcloud run services update sqlgym-backend \
  --add-cloudsql-instances=PROJECT:REGION:INSTANCE
```

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [Cloud Run Pricing Calculator](https://cloud.google.com/products/calculator)
- [SQLGym Backend Code](api/)

---

## ✅ Quick Checklist

- [ ] Google Cloud account created
- [ ] gcloud CLI installed and authenticated
- [ ] Backend deployed to Cloud Run
- [ ] Environment variables configured
- [ ] Database connected (Cloud SQL or external)
- [ ] Frontend deployed to Vercel/Cloudflare
- [ ] Frontend URL added to backend CORS
- [ ] Backend URL added to frontend env
- [ ] Email service configured (Resend)
- [ ] Testing completed
- [ ] Monitoring & alerts set up

---

**Need help?** Check the [full deployment guide](DEPLOYMENT_GUIDE.md) or refer to Google Cloud Run documentation.

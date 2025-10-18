# Deploy Frontend to Vercel (Backend on Cloud Run)

This guide explains how to deploy your React/Vite frontend to Vercel while keeping the Python backend on Google Cloud Run.

## Architecture
- **Frontend**: React + Vite → Vercel
- **Backend**: FastAPI + Python → Google Cloud Run

---

## Step 1: Deploy Backend to Cloud Run First

Make sure your backend is deployed and you have the Cloud Run URL:
```bash
gcloud builds submit --config cloudbuild.yaml
```

After deployment, note your backend URL:
```
https://sqlgym-<hash>-uc.a.run.app
```

---

## Step 2: Deploy Frontend to Vercel

### Option A: Using Vercel Dashboard (Recommended)

1. **Go to [vercel.com](https://vercel.com) and sign in**

2. **Click "Add New Project"**

3. **Import your GitHub repository**

4. **Configure the project:**
   - **Framework Preset**: Vite
   - **Root Directory**: Leave as `.` (root)
   - **Build Command**: `cd client && npm install && npm run build`
   - **Output Directory**: `dist/public`
   - **Install Command**: `npm install`

5. **Add Environment Variables** (IMPORTANT):
   - Click "Environment Variables"
   - Add: `VITE_API_URL` = `https://your-backend-url.run.app`
   - Example: `VITE_API_URL` = `https://sqlgym-abc123-uc.a.run.app`
   - Make sure to include `/api` at the end if needed: `https://sqlgym-abc123-uc.a.run.app/api`

6. **Click "Deploy"**

### Option B: Using Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy (from project root)
vercel

# Set environment variable
vercel env add VITE_API_URL

# Deploy to production
vercel --prod
```

---

## Step 3: Configure CORS on Backend

Your backend needs to allow requests from your Vercel frontend.

### Update Backend CORS Settings

Find your CORS configuration in your FastAPI app (likely in `api/main.py`) and update it:

```python
from fastapi.middleware.cors import CORSMiddleware

# Add your Vercel domain
origins = [
    "http://localhost:5000",
    "http://localhost:5173",
    "https://your-frontend.vercel.app",  # Add your Vercel URL
    "https://*.vercel.app",  # Allow all Vercel preview deployments
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

After updating, redeploy your backend:
```bash
gcloud builds submit --config cloudbuild.yaml
```

---

## Step 4: Test Your Deployment

1. Visit your Vercel URL: `https://your-frontend.vercel.app`
2. Open browser DevTools → Network tab
3. Try logging in or making API calls
4. Verify requests go to your Cloud Run backend

---

## Environment Variables Reference

### Frontend (Vercel)
- `VITE_API_URL`: Your Cloud Run backend URL (e.g., `https://sqlgym-abc.run.app`)

### Backend (Cloud Run)
Set these in Cloud Run console or cloudbuild.yaml:
- `DATABASE_URL`: Your database connection string
- `SECRET_KEY`: Your JWT secret key
- Any other API keys needed

---

## Troubleshooting

### CORS Errors
**Symptom**: "Access to fetch has been blocked by CORS policy"

**Solution**: 
- Verify CORS origins include your Vercel domain
- Make sure `allow_credentials=True` is set
- Redeploy backend after CORS changes

### API Requests Failing
**Symptom**: API calls return 404 or fail silently

**Solution**:
- Check that `VITE_API_URL` is set correctly in Vercel dashboard
- Verify the URL doesn't have trailing slashes: `https://backend.run.app` not `https://backend.run.app/`
- Check if you need `/api` prefix: Some setups need `https://backend.run.app/api`

### Build Failures
**Symptom**: Vercel build fails

**Solution**:
- Verify `vercel.json` build command is correct
- Check that all dependencies are in `package.json`
- Review build logs in Vercel dashboard

---

## Local Development

For local development, the setup remains the same:

```bash
# Terminal 1: Start backend
python3.11 -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend (uses Vite proxy)
npm run dev
```

The Vite proxy (configured in `vite.config.ts`) automatically routes `/api` requests to `localhost:8000` during development.

---

## Custom Domain (Optional)

After deploying to Vercel, you can add a custom domain:

1. Go to your project in Vercel Dashboard
2. Settings → Domains
3. Add your custom domain
4. Update DNS records as instructed
5. Update CORS in backend to include your custom domain

---

## Automatic Deployments

Vercel automatically deploys:
- **Production**: Every push to `main` branch
- **Preview**: Every pull request

Each preview deployment gets a unique URL for testing.

---

## Summary

✅ Backend on Cloud Run: `https://sqlgym-xxx.run.app`  
✅ Frontend on Vercel: `https://your-app.vercel.app`  
✅ CORS configured to allow Vercel domain  
✅ Environment variables set in Vercel dashboard  
✅ Automatic deployments on git push  

Your app is now deployed with a modern serverless architecture!

# SQLGym Deployment Guide

## Split Deployment Architecture

This guide covers deploying SQLGym with:
- **Frontend**: Vercel or Cloudflare Pages
- **Backend**: Render

---

## 📋 Prerequisites

- GitHub/GitLab account
- Vercel or Cloudflare account (free tier available)
- Render account (free tier available)
- Domain name (optional, for custom domains)

---

## 🚀 Backend Deployment (Render)

### Step 1: Prepare Backend Configuration

The project already has the necessary files. Ensure these are in your repository:
- `requirements.txt` - Python dependencies
- `api/` - Backend code

### Step 2: Create Render Web Service

1. **Go to [Render Dashboard](https://dashboard.render.com)**
   - Sign in or create account

2. **Create New Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub/GitLab repository
   - Select your SQLGym repository

3. **Configure Service**
   ```
   Name: sqlgym-backend (or your choice)
   Environment: Python 3
   Region: Choose closest to your users
   Branch: main
   
   Build Command: pip install -r requirements.txt
   Start Command: cd api && uvicorn main:app --host 0.0.0.0 --port $PORT
   
   Plan: Free (or select paid for better performance)
   ```

4. **Environment Variables** (Add in Render dashboard)
   ```bash
   # Database
   DATABASE_URL=<your_postgres_url>
   
   # Frontend URLs (add after frontend deployment)
   FRONTEND_URL=https://your-app.vercel.app
   
   # Resend Email
   RESEND_API_KEY=<your_resend_key>
   FROM_EMAIL=noreply@yourdomain.com
   
   # Redis (if using external Redis)
   REDIS_URL=<your_redis_url>
   
   # AWS S3
   AWS_ACCESS_KEY_ID=<your_aws_key>
   AWS_SECRET_ACCESS_KEY=<your_aws_secret>
   AWS_BUCKET_NAME=<your_bucket_name>
   AWS_REGION=<your_region>
   
   # Google Gemini AI
   GEMINI_API_KEY=<your_gemini_key>
   
   # OAuth (Optional)
   GOOGLE_CLIENT_ID=<your_google_client_id>
   GOOGLE_CLIENT_SECRET=<your_google_client_secret>
   GITHUB_CLIENT_ID=<your_github_client_id>
   GITHUB_CLIENT_SECRET=<your_github_client_secret>
   
   # Security
   SECRET_KEY=<generate_random_secret>
   ADMIN_SECRET_KEY=<generate_random_secret>
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Wait for build to complete
   - Note your backend URL: `https://sqlgym-backend.onrender.com`

### Step 3: Database Setup on Render

1. **Create PostgreSQL Database**
   - In Render dashboard → "New" → "PostgreSQL"
   - Name: `sqlgym-db`
   - Plan: Free (or paid)
   - Note the **Internal Database URL**

2. **Add to Environment Variables**
   - Copy the Internal Database URL
   - Add to web service as `DATABASE_URL`

---

## 🌐 Frontend Deployment

### Option A: Vercel

#### Step 1: Prepare Frontend

1. **Update API URL in Frontend**
   - The frontend will use environment variable `VITE_API_URL`

2. **Verify `vercel.json` exists**
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": "dist/public",
     "installCommand": "npm install",
     "rewrites": [
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```

#### Step 2: Deploy to Vercel

1. **Via Vercel Dashboard**
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Vercel auto-detects Vite configuration

2. **Configure Build Settings**
   ```
   Framework Preset: Vite
   Build Command: npm run build
   Output Directory: dist/public
   Install Command: npm install
   Root Directory: ./
   ```

3. **Environment Variables**
   ```bash
   VITE_API_URL=https://sqlgym-backend.onrender.com
   ```

4. **Deploy**
   - Click "Deploy"
   - Note your URL: `https://your-app.vercel.app`

5. **Update Backend CORS**
   - Go back to Render
   - Add to environment variables:
     ```
     FRONTEND_URL=https://your-app.vercel.app
     ```

#### Alternative: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel

# Set environment variable
vercel env add VITE_API_URL production
# Enter: https://sqlgym-backend.onrender.com

# Deploy to production
vercel --prod
```

---

### Option B: Cloudflare Pages

#### Step 1: Deploy via Dashboard

1. **Go to [Cloudflare Dashboard](https://dash.cloudflare.com)**
   - Navigate to "Workers & Pages"
   - Click "Create application" → "Pages" → "Connect to Git"

2. **Connect Repository**
   - Authorize GitHub/GitLab
   - Select SQLGym repository

3. **Build Configuration**
   ```
   Production branch: main
   Build command: npm run build
   Build output directory: dist/public
   Root directory: /
   ```

4. **Environment Variables**
   ```bash
   VITE_API_URL=https://sqlgym-backend.onrender.com
   ```

5. **Deploy**
   - Click "Save and Deploy"
   - Note your URL: `https://your-app.pages.dev`

6. **Update Backend CORS**
   - Go to Render backend
   - Add to environment variables:
     ```
     FRONTEND_URL=https://your-app.pages.dev
     ```

#### Step 2: Fix SPA Routing

Create `public/_redirects` file (for 404 handling):
```
/*    /index.html   200
```

Or use Cloudflare Pages Functions for more control.

---

## 🔒 Security Configuration

### Update Backend CORS for Production

The backend already supports dynamic CORS. To add Cloudflare support, update environment variables in Render:

```bash
# For Vercel
FRONTEND_URL=https://your-app.vercel.app

# For Cloudflare
FRONTEND_URL=https://your-app.pages.dev

# For both (comma-separated)
FRONTEND_URL=https://your-app.vercel.app,https://your-app.pages.dev
```

### OAuth Redirect URIs

Update OAuth provider settings:

**Google OAuth Console:**
- Authorized redirect URIs:
  - `https://your-app.vercel.app/auth/google/callback`
  - `https://your-app.pages.dev/auth/google/callback`

**GitHub OAuth App:**
- Authorization callback URL:
  - `https://your-app.vercel.app/auth/github/callback`

---

## 📧 Email Configuration (Resend)

1. **Verify Your Domain in Resend**
   - Go to [resend.com](https://resend.com)
   - Add your domain (e.g., `onrender.com`)
   - Add DNS records (SPF, DKIM)

2. **Set Environment Variables in Render**
   ```bash
   FROM_EMAIL=noreply@yourdomain.com
   RESEND_API_KEY=<your_resend_api_key>
   ```

3. **Test Email Verification**
   - Register new user on frontend
   - Check email delivery

---

## 🧪 Testing Your Deployment

### Backend Health Check
```bash
curl https://sqlgym-backend.onrender.com/
```

### Frontend Check
1. Visit `https://your-app.vercel.app` or `https://your-app.pages.dev`
2. Try registration/login
3. Test problem solving
4. Check browser console for CORS errors

### API Documentation
- Swagger UI: `https://sqlgym-backend.onrender.com/docs`
- ReDoc: `https://sqlgym-backend.onrender.com/redoc`

---

## 🐛 Common Issues

### CORS Errors
**Problem**: "Access-Control-Allow-Origin" error
**Solution**: 
1. Ensure `FRONTEND_URL` is set in Render
2. Check protocol (https://) is included
3. Restart backend service after env variable changes

### Backend Spins Down (Free Tier)
**Problem**: Slow first request (Render free tier)
**Solution**: 
- Upgrade to paid plan, or
- Use a cron job to ping backend every 10 minutes

### Email Not Sending
**Problem**: Verification emails not arriving
**Solution**:
1. Verify domain in Resend
2. Check `FROM_EMAIL` format
3. Check spam folder
4. Verify `RESEND_API_KEY` is correct

### Build Failures
**Problem**: Frontend build fails
**Solution**:
- Check `VITE_API_URL` is set
- Ensure all dependencies in `package.json`
- Check build logs for specific errors

---

## 📊 Monitoring

### Render
- View logs in Render dashboard
- Set up notifications for errors
- Monitor resource usage

### Vercel/Cloudflare
- View deployment logs
- Analytics dashboard
- Real User Monitoring (RUM)

---

## 🔄 CI/CD

Both platforms support auto-deployment:
- **Render**: Auto-deploys on push to `main` branch
- **Vercel**: Auto-deploys on push to `main` branch
- **Cloudflare**: Auto-deploys on push to `main` branch

Preview deployments:
- **Vercel**: Creates preview URL for each PR
- **Cloudflare**: Creates preview URL for each PR

---

## 💰 Cost Estimate (Free Tier)

| Service | Free Tier | Limitations |
|---------|-----------|-------------|
| **Render (Backend)** | ✅ Free | Spins down after 15 min inactivity, 750 hrs/mo |
| **Render (PostgreSQL)** | ✅ Free | Expires after 90 days, 1GB storage |
| **Vercel (Frontend)** | ✅ Free | 100GB bandwidth/mo, unlimited sites |
| **Cloudflare Pages** | ✅ Free | Unlimited bandwidth, 500 builds/mo |
| **Resend (Email)** | ✅ Free | 3,000 emails/mo, 100 emails/day |

---

## 🎯 Next Steps

1. ✅ Deploy backend to Render
2. ✅ Deploy frontend to Vercel or Cloudflare
3. ✅ Configure environment variables
4. ✅ Test email verification
5. ✅ Set up custom domain (optional)
6. ✅ Configure OAuth providers
7. ✅ Monitor and optimize

---

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Vercel Docs](https://vercel.com/docs)
- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages)
- [FastAPI CORS Guide](https://fastapi.tiangolo.com/tutorial/cors/)
- [Resend Docs](https://resend.com/docs)

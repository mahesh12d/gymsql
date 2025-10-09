# Railway Deployment Guide for SQLGym

This guide explains how to deploy SQLGym to Railway.app.

## Prerequisites

- A Railway account (https://railway.app)
- GitHub repository connected to Railway
- PostgreSQL and Redis databases (Railway provides these as addons)

## Deployment Steps

### 1. Create a New Project on Railway

1. Go to https://railway.app and create a new project
2. Connect your GitHub repository
3. Railway will automatically detect the `Dockerfile` and `railway.toml`

### 2. Add Database Services

Add these services to your Railway project:

#### PostgreSQL Database
1. Click "New Service" → "Database" → "Add PostgreSQL"
2. Railway will automatically set the `DATABASE_URL` environment variable

#### Redis Cache
1. Click "New Service" → "Database" → "Add Redis"
2. Railway will automatically set the `REDIS_URL` environment variable

### 3. Set Environment Variables

In your Railway project settings, add these environment variables:

#### Required Variables
```bash
JWT_SECRET=<generate-a-random-secret-32-chars>
ADMIN_SECRET_KEY=<generate-a-random-secret-32-chars>
PORT=5000
```

#### Optional OAuth Variables
```bash
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-secret>
GITHUB_CLIENT_ID=<your-github-oauth-client-id>
GITHUB_CLIENT_SECRET=<your-github-oauth-secret>
```

### 4. Deploy

Railway will automatically:
1. Install Node.js and Python dependencies
2. Build the frontend with `npm run build`
3. Start the backend API and Redis worker

The deployment process follows this command:
```bash
pip install --no-cache-dir -r requirements.txt && npm run build
```

### 5. Verify Deployment

- Check the deployment logs for any errors
- Access your app at the Railway-provided URL
- Test the API health endpoint: `https://your-app.railway.app/api/health`

## Architecture

The unified Dockerfile:
- Uses Python 3.11 with Node.js 20
- Installs both Python and npm dependencies
- Builds the React frontend during deployment
- Runs both the FastAPI backend and Redis worker in the same container

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Auto-set by Railway |
| `REDIS_URL` | Redis connection string | Auto-set by Railway |
| `JWT_SECRET` | Secret key for JWT tokens | Yes |
| `ADMIN_SECRET_KEY` | Secret key for admin access | Yes |
| `PORT` | Port to run the application | Auto-set (default 5000) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Optional |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | Optional |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | Optional |

## Troubleshooting

### Build Fails with "npm: command not found"
- Make sure the Dockerfile correctly installs Node.js
- Check Railway build logs for errors

### "Frontend not built" Error
- Ensure `npm run build` completes successfully
- Check that `dist/public/index.html` exists after build
- Verify all frontend dependencies are in package.json

### Database Connection Issues
- Verify `DATABASE_URL` is set correctly
- Check that PostgreSQL service is running
- Review connection string format

### Redis Worker Not Running
- Check deployment logs for Redis worker startup
- Verify `REDIS_URL` is set correctly
- Worker starts automatically with the main process

## Monitoring

- View logs: Railway Dashboard → Your Service → Deployments → Logs
- Check metrics: Railway Dashboard → Your Service → Metrics
- Health check: Configure in `railway.toml` (already set to `/api/health`)

## Scaling

Railway can automatically scale your application based on traffic. The current setup uses:
- **Deployment Type**: VM (always running)
- **Health Check**: `/api/health` endpoint
- **Both backend and worker run in the same container** for simplicity

For high-traffic scenarios, consider:
- Splitting Redis worker into a separate Railway service
- Using Railway's autoscaling features
- Implementing connection pooling (already configured)

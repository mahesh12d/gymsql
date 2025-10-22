# Production Security Guide - Single Admin Setup

This guide walks you through deploying SQLGym Platform to Google Cloud Run with production-ready security for a single administrator.

## Security Architecture (Option A: Simple & Secure)

Since you're the only admin, this implementation provides excellent security without unnecessary complexity:

### ✅ Security Features Implemented

1. **Rate Limiting** - Prevents brute force attacks (5 attempts/hour on admin login)
2. **Audit Logging** - All admin actions logged with timestamps, IP, and metadata
3. **IP Lockout** - Automatic 1-hour lockout after 5 failed attempts
4. **Security Headers** - CSP, HSTS, X-Frame-Options, etc.
5. **Optional IP Whitelisting** - Restrict admin panel to your IP address
6. **ADMIN_SECRET_KEY** - Strong cryptographic key (64+ characters)

---

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed (for local testing)
4. **Admin Account** - Your user account must have `is_admin=true` in database

---

## Step 1: Generate Strong Admin Secret Key

Generate a cryptographically secure admin key (64 characters recommended):

```bash
# On Linux/Mac
openssl rand -hex 32

# Or use Python
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Example output:**
```
vK8Lm2Pq9RtYuI0oP3aS6dF8gH1jK4lZ7xC9vB2nM5qW0eR3tY6uI8oP1aS4dF7g
```

🔒 **Store this securely** - You'll need it for both deployment and admin panel access!

---

## Step 2: Set Up Google Secret Manager

Store your secrets in Google Secret Manager for secure deployment:

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Create secrets for your project
PROJECT_ID="your-project-id"

# 1. Create ADMIN_SECRET_KEY
echo -n "vK8Lm2Pq9RtYuI0oP3aS6dF8gH1jK4lZ7xC9vB2nM5qW0eR3tY6uI8oP1aS4dF7g" | \
  gcloud secrets create ADMIN_SECRET_KEY --data-file=- --project=$PROJECT_ID

# 2. Create JWT_SECRET (for user authentication)
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create JWT_SECRET --data-file=- --project=$PROJECT_ID

# 3. Create DATABASE_URL (your PostgreSQL connection string)
echo -n "postgresql://user:password@host:5432/sqlgym" | \
  gcloud secrets create DATABASE_URL --data-file=- --project=$PROJECT_ID

# 4. Create REDIS_URL (for session tracking - optional but recommended)
echo -n "redis://your-redis-host:6379" | \
  gcloud secrets create REDIS_URL --data-file=- --project=$PROJECT_ID
```

### Grant Cloud Run Access to Secrets

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Secret Manager access to Cloud Run service account
gcloud secrets add-iam-policy-binding ADMIN_SECRET_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID

# Repeat for all secrets
for SECRET in JWT_SECRET DATABASE_URL REDIS_URL; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
done
```

---

## Step 3: Update Cloud Build Configuration

Edit `cloudbuild.prod.yaml` to use Secret Manager:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/sqlgym-prod:$COMMIT_SHA', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/sqlgym-prod:$COMMIT_SHA']
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'sqlgym-prod'
      - '--image=gcr.io/$PROJECT_ID/sqlgym-prod:$COMMIT_SHA'
      - '--platform=managed'
      - '--region=us-central1'
      - '--allow-unauthenticated'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--max-instances=10'
      - '--set-env-vars=ENVIRONMENT=production'
      # Security: Load secrets from Secret Manager
      - '--set-secrets=ADMIN_SECRET_KEY=ADMIN_SECRET_KEY:latest,JWT_SECRET=JWT_SECRET:latest,DATABASE_URL=DATABASE_URL:latest,REDIS_URL=REDIS_URL:latest'

options:
  logging: CLOUD_LOGGING_ONLY
```

---

## Step 4: (Optional) Enable IP Whitelisting

To restrict admin panel access to only your IP address:

```bash
# Get your current public IP
curl -s https://api.ipify.org

# Example: 203.0.113.45

# Add to Cloud Run deployment
gcloud run services update sqlgym-prod \
  --set-env-vars=ADMIN_ALLOWED_IPS="203.0.113.45" \
  --region=us-central1
```

**For multiple IPs (e.g., home + office):**
```bash
gcloud run services update sqlgym-prod \
  --set-env-vars=ADMIN_ALLOWED_IPS="203.0.113.45,198.51.100.23" \
  --region=us-central1
```

**To disable IP whitelisting** (not recommended for production):
```bash
gcloud run services update sqlgym-prod \
  --remove-env-vars=ADMIN_ALLOWED_IPS \
  --region=us-central1
```

---

## Step 5: Deploy to Production

```bash
# Deploy using Cloud Build
gcloud builds submit --config=cloudbuild.prod.yaml

# Monitor deployment
gcloud run services describe sqlgym-prod --region=us-central1

# Get your production URL
gcloud run services describe sqlgym-prod --region=us-central1 --format='value(status.url)'
```

---

## Step 6: Make Yourself Admin

Connect to your production database and set your account as admin:

```bash
# Option 1: Using Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432 &

# Connect to database
psql "postgresql://user:password@localhost:5432/sqlgym"

# Set your account as admin
UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';

# Verify
SELECT id, email, username, is_admin FROM users WHERE email = 'your-email@example.com';
```

**Or use the provided script:**

```bash
# SSH into Cloud Run instance (requires gcloud alpha components)
gcloud alpha run services proxy sqlgym-prod --region=us-central1

# In another terminal, run the admin script
python scripts/make_admin.py --email your-email@example.com
```

---

## Step 7: Access Admin Panel

1. **Login to your SQLGym account** at `https://your-app.run.app`

2. **Navigate to Admin Panel:** `https://your-app.run.app/admin-panel`

3. **Enter your ADMIN_SECRET_KEY** (the one you generated in Step 1)

4. **Create problems and manage solutions!**

---

## Security Best Practices

### ✅ DO

1. **Use Google Secret Manager** - Never hardcode secrets in environment variables
2. **Rotate ADMIN_SECRET_KEY** every 90 days
3. **Enable IP Whitelisting** if you have a static IP
4. **Monitor audit logs** regularly for suspicious activity
5. **Use strong passwords** for your admin account
6. **Enable 2FA** on your Google Cloud account
7. **Set up Cloud Logging alerts** for failed admin login attempts

### ❌ DON'T

1. **Share ADMIN_SECRET_KEY** with anyone
2. **Store secrets in Git repositories** or plain text files
3. **Use weak admin keys** (< 32 characters)
4. **Disable rate limiting** in production
5. **Access admin panel from public WiFi** without VPN
6. **Ignore failed login alerts**

---

## Monitoring & Alerts

### View Admin Audit Logs

Audit logs are automatically stored in Redis (90-day retention):

```bash
# Check logs via Redis CLI (if Redis is accessible)
redis-cli -h your-redis-host -p 6379

# List all admin audit logs
KEYS admin_audit:*

# View specific user's actions
LRANGE user_audit:your-user-id 0 99
```

### Set Up Cloud Logging Alerts

Create alerts for security events:

```bash
# Alert on 5+ failed admin login attempts in 5 minutes
gcloud logging metrics create admin_failed_logins \
  --description="Failed admin login attempts" \
  --log-filter='resource.type="cloud_run_revision"
    AND textPayload=~"SECURITY: Invalid admin key"'

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Admin Login Failures" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s \
  --condition-display-name="5 failed attempts in 5 min"
```

---

## Troubleshooting

### Problem: "Admin authentication required"

**Solution:** Ensure you're using the correct ADMIN_SECRET_KEY

```bash
# Verify secret in Secret Manager
gcloud secrets versions access latest --secret=ADMIN_SECRET_KEY
```

### Problem: "Access denied - user does not have admin privileges"

**Solution:** Set `is_admin=true` for your user account (see Step 6)

### Problem: "Too many failed authentication attempts"

**Solution:** Wait 1 hour or clear Redis lockout manually:

```bash
# Connect to Redis
redis-cli -h your-redis-host

# Clear lockout for your IP
DEL admin_lockout:YOUR_IP_ADDRESS
DEL admin_failed:YOUR_IP_ADDRESS
```

### Problem: IP whitelist blocking legitimate access

**Solution:** Add your new IP or disable whitelisting:

```bash
# Update allowed IPs
gcloud run services update sqlgym-prod \
  --update-env-vars=ADMIN_ALLOWED_IPS="NEW_IP,OLD_IP" \
  --region=us-central1
```

---

## Rotating Admin Secret Key

Rotate your admin key every 90 days for maximum security:

```bash
# 1. Generate new key
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

# 2. Update Secret Manager
echo -n "$NEW_KEY" | gcloud secrets versions add ADMIN_SECRET_KEY --data-file=-

# 3. Restart Cloud Run to pick up new secret
gcloud run services update sqlgym-prod --region=us-central1

# 4. Update your password manager with new key
echo "New ADMIN_SECRET_KEY: $NEW_KEY"
```

---

## Security Checklist

Before going live, verify all security measures:

- [ ] ADMIN_SECRET_KEY is 64+ characters and stored in Secret Manager
- [ ] JWT_SECRET is unique and stored in Secret Manager
- [ ] Database credentials are in Secret Manager (not environment variables)
- [ ] Redis URL is in Secret Manager
- [ ] IP whitelisting is enabled (if you have static IP)
- [ ] Your user account has `is_admin=true` in database
- [ ] Cloud Logging alerts are configured
- [ ] Rate limiting is active (test with invalid key)
- [ ] HTTPS is enforced (Cloud Run default)
- [ ] 2FA is enabled on Google Cloud account

---

## Support

If you encounter issues:

1. Check Cloud Run logs: `gcloud run services logs read sqlgym-prod --region=us-central1`
2. Review audit logs in Redis
3. Verify secrets are properly set in Secret Manager
4. Check IP whitelist configuration
5. Test rate limiting with intentional failed attempts

For security concerns, review the audit logs and rate limiter Redis keys.

---

## Next Steps

- **Set up automated backups** for your PostgreSQL database
- **Configure CDN** (Cloud CDN) for static assets
- **Enable Cloud Armor** for DDoS protection
- **Set up uptime monitoring** (Cloud Monitoring)
- **Create staging environment** for testing changes

Your SQLGym Platform is now secured for production use! 🎉

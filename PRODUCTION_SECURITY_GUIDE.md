# Production Security Guide - Single Admin Setup

This guide walks you through deploying SQLGym Platform to Google Cloud Run with production-ready security for a single administrator.

## Security Architecture (PostgreSQL-Only, No Redis Required)

Since you're the only admin, this implementation provides excellent security without unnecessary complexity. **All security features use PostgreSQL only** - no Redis required for admin security!

### ✅ Security Features Implemented

1. **PostgreSQL-Based Rate Limiting** - Prevents brute force attacks (5 attempts/hour on admin login)
2. **PostgreSQL Audit Logging** - All admin actions logged with timestamps, IP, and metadata (90-day retention)
3. **PostgreSQL IP Lockout** - Automatic 1-hour lockout after 5 failed attempts
4. **Timing-Attack Protection** - Constant-time comparison for admin key verification
5. **Security Headers** - CSP, HSTS, X-Frame-Options, etc.
6. **Optional IP Whitelisting** - Restrict admin panel to your IP address
7. **ADMIN_SECRET_KEY** - Strong cryptographic key (64+ characters)

### 💰 Cost Savings

By using PostgreSQL for all security features instead of Redis:
- **No Redis hosting costs** (saves $10-30/month)
- **Simpler deployment** (one database instead of two)
- **Built-in persistence** (audit logs survive restarts)

---

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed (for local testing)
4. **PostgreSQL Database** (Cloud SQL or any managed PostgreSQL)
5. **Admin Account** - Your user account must have `is_admin=true` in database

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
# This database will store ALL security features (rate limits, audit logs, IP lockouts)
echo -n "postgresql://user:password@host:5432/sqlgym" | \
  gcloud secrets create DATABASE_URL --data-file=- --project=$PROJECT_ID
```

**Note:** You do NOT need REDIS_URL for admin security features! (You may still need Redis for other app features like caching, but not for admin security)

### Grant Cloud Run Access to Secrets

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Secret Manager access to Cloud Run service account
for SECRET in ADMIN_SECRET_KEY JWT_SECRET DATABASE_URL; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
done
```

---

## Step 3: Database Schema Migration

The security features require three additional database tables:

```bash
# Run database migrations (automatically creates tables)
npm run db:push

# Or manually create tables:
psql "$DATABASE_URL" <<EOF
CREATE TABLE IF NOT EXISTS admin_rate_limit_attempts (
    id VARCHAR PRIMARY KEY,
    ip_address VARCHAR(50) NOT NULL,
    attempt_count INTEGER DEFAULT 1,
    window_start TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_ip_lockouts (
    id VARCHAR PRIMARY KEY,
    ip_address VARCHAR(50) UNIQUE NOT NULL,
    locked_until TIMESTAMP NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    action VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50) NOT NULL,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    success BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_admin_rate_limit_ip ON admin_rate_limit_attempts(ip_address);
CREATE INDEX idx_admin_lockout_ip ON admin_ip_lockouts(ip_address);
CREATE INDEX idx_admin_lockout_expires ON admin_ip_lockouts(locked_until);
CREATE INDEX idx_admin_audit_user_id ON admin_audit_logs(user_id);
CREATE INDEX idx_admin_audit_action ON admin_audit_logs(action);
CREATE INDEX idx_admin_audit_created_at ON admin_audit_logs(created_at);
CREATE INDEX idx_admin_audit_ip_address ON admin_audit_logs(ip_address);
EOF
```

---

## Step 4: Update Cloud Build Configuration

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
      # Security: Load secrets from Secret Manager (NO REDIS_URL needed for admin security!)
      - '--set-secrets=ADMIN_SECRET_KEY=ADMIN_SECRET_KEY:latest,JWT_SECRET=JWT_SECRET:latest,DATABASE_URL=DATABASE_URL:latest'

options:
  logging: CLOUD_LOGGING_ONLY
```

---

## Step 5: (Optional) Enable IP Whitelisting

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

## Step 6: Deploy to Production

```bash
# Deploy using Cloud Build
gcloud builds submit --config=cloudbuild.prod.yaml

# Monitor deployment
gcloud run services describe sqlgym-prod --region=us-central1

# Get your production URL
gcloud run services describe sqlgym-prod --region=us-central1 --format='value(status.url)'
```

---

## Step 7: Make Yourself Admin

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

## Step 8: Access Admin Panel

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
4. **Monitor audit logs** regularly for suspicious activity (stored in PostgreSQL)
5. **Use strong passwords** for your admin account
6. **Enable 2FA** on your Google Cloud account
7. **Set up Cloud Logging alerts** for failed admin login attempts
8. **Regular database backups** - Audit logs are in PostgreSQL
9. **Clean up old audit logs** - Keep 90 days retention for compliance

### ❌ DON'T

1. **Share ADMIN_SECRET_KEY** with anyone
2. **Store secrets in Git repositories** or plain text files
3. **Use weak admin keys** (< 32 characters)
4. **Disable rate limiting** in production
5. **Access admin panel from public WiFi** without VPN
6. **Ignore failed login alerts**
7. **Delete security tables** (admin_rate_limit_attempts, admin_ip_lockouts, admin_audit_logs)

---

## Monitoring & Alerts

### View Admin Audit Logs (PostgreSQL)

All audit logs are stored in PostgreSQL with 90-day retention:

```sql
-- Connect to your database
psql "$DATABASE_URL"

-- View recent admin actions
SELECT 
    created_at,
    user_id,
    action,
    ip_address,
    success,
    metadata
FROM admin_audit_logs
ORDER BY created_at DESC
LIMIT 100;

-- View failed authentication attempts
SELECT 
    created_at,
    ip_address,
    metadata->>'error' as error_message
FROM admin_audit_logs
WHERE success = false
    AND action = 'admin_auth_attempt'
ORDER BY created_at DESC;

-- Check IP lockouts
SELECT 
    ip_address,
    locked_until,
    reason,
    created_at
FROM admin_ip_lockouts
WHERE locked_until > NOW()
ORDER BY created_at DESC;

-- View rate limit attempts by IP
SELECT 
    ip_address,
    attempt_count,
    window_start,
    updated_at
FROM admin_rate_limit_attempts
WHERE window_start > NOW() - INTERVAL '1 hour'
ORDER BY attempt_count DESC;
```

### Automatic Cleanup

The system automatically cleans up old records:

```sql
-- Expired rate limit windows (auto-deleted)
-- Expired IP lockouts (auto-deleted) 
-- Audit logs older than 90 days (kept for compliance)
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

**Solution:** Set `is_admin=true` for your user account (see Step 7)

### Problem: "Too many failed authentication attempts"

**Solution:** Wait 1 hour or clear PostgreSQL lockout manually:

```sql
-- Connect to database
psql "$DATABASE_URL"

-- Clear lockout for your IP
DELETE FROM admin_ip_lockouts WHERE ip_address = 'YOUR_IP_ADDRESS';
DELETE FROM admin_rate_limit_attempts WHERE ip_address = 'YOUR_IP_ADDRESS';
```

### Problem: IP whitelist blocking legitimate access

**Solution:** Add your new IP or disable whitelisting:

```bash
# Update allowed IPs
gcloud run services update sqlgym-prod \
  --update-env-vars=ADMIN_ALLOWED_IPS="NEW_IP,OLD_IP" \
  --region=us-central1
```

### Problem: Database tables missing

**Solution:** Run migrations to create security tables:

```bash
npm run db:push
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

## Data Retention & Compliance

### Audit Log Retention

- **Default retention:** 90 days (configurable)
- **Storage:** PostgreSQL database
- **Auto-cleanup:** Runs on each auth attempt to remove old logs

### Manual Cleanup

```sql
-- Delete audit logs older than 90 days
DELETE FROM admin_audit_logs 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Check retention status
SELECT 
    COUNT(*) as total_logs,
    MIN(created_at) as oldest_log,
    MAX(created_at) as newest_log
FROM admin_audit_logs;
```

---

## Security Checklist

Before going live, verify all security measures:

- [ ] ADMIN_SECRET_KEY is 64+ characters and stored in Secret Manager
- [ ] JWT_SECRET is unique and stored in Secret Manager
- [ ] Database credentials are in Secret Manager (not environment variables)
- [ ] Security tables created (admin_rate_limit_attempts, admin_ip_lockouts, admin_audit_logs)
- [ ] IP whitelisting is enabled (if you have static IP)
- [ ] Your user account has `is_admin=true` in database
- [ ] Cloud Logging alerts are configured
- [ ] Rate limiting is active (test with invalid key)
- [ ] HTTPS is enforced (Cloud Run default)
- [ ] 2FA is enabled on Google Cloud account
- [ ] Database backups are enabled (includes audit logs)
- [ ] Timing-attack protection is active (constant-time comparison)

---

## Performance Considerations

### PostgreSQL Indexes

The security tables use optimized indexes for fast lookups:

```sql
-- Rate limiting: Fast IP lookups
CREATE INDEX idx_admin_rate_limit_ip ON admin_rate_limit_attempts(ip_address);

-- IP lockouts: Fast IP and expiration checks
CREATE INDEX idx_admin_lockout_ip ON admin_ip_lockouts(ip_address);
CREATE INDEX idx_admin_lockout_expires ON admin_ip_lockouts(locked_until);

-- Audit logs: Fast filtering by user, action, time, IP
CREATE INDEX idx_admin_audit_user_id ON admin_audit_logs(user_id);
CREATE INDEX idx_admin_audit_action ON admin_audit_logs(action);
CREATE INDEX idx_admin_audit_created_at ON admin_audit_logs(created_at);
CREATE INDEX idx_admin_audit_ip_address ON admin_audit_logs(ip_address);
```

### Expected Query Performance

- **Rate limit check:** < 10ms
- **IP lockout check:** < 10ms
- **Audit log insertion:** < 20ms
- **Audit log query (100 records):** < 50ms

---

## Support

If you encounter issues:

1. Check Cloud Run logs: `gcloud run services logs read sqlgym-prod --region=us-central1`
2. Review audit logs in PostgreSQL (see SQL queries above)
3. Verify secrets are properly set in Secret Manager
4. Check IP whitelist configuration
5. Test rate limiting with intentional failed attempts
6. Verify security tables exist in database

For security concerns, review the PostgreSQL audit logs and rate limiter tables.

---

## Architecture Benefits

### Why PostgreSQL Instead of Redis?

1. **Cost Savings:** No separate Redis instance needed ($10-30/month savings)
2. **Persistence:** Audit logs survive database restarts
3. **ACID Compliance:** Transaction safety for security records
4. **Backup Included:** Audit logs backed up with main database
5. **Simpler Deployment:** One database instead of two
6. **Better Queries:** SQL for complex audit log analysis
7. **No Cache Eviction:** Logs never accidentally deleted

### Trade-offs

- **Slightly slower** than Redis (10-20ms vs 1-2ms), but still fast enough for admin operations
- **Database load** increased minimally (< 1% for typical admin usage)

---

## Next Steps

- **Set up automated backups** for your PostgreSQL database (includes audit logs)
- **Configure CDN** (Cloud CDN) for static assets
- **Enable Cloud Armor** for DDoS protection
- **Set up uptime monitoring** (Cloud Monitoring)
- **Create staging environment** for testing changes
- **Schedule audit log reviews** (weekly recommended)

Your SQLGym Platform is now secured for production use with PostgreSQL-only security! 🎉

# Production Deployment Security Checklist for SQLGym

## ✅ Pre-Deployment Security Checklist

Use this checklist before deploying to production to ensure your admin panel is secure.

---

## 🔐 **1. Environment Variables & Secrets**

### Required Environment Variables

- [ ] `ADMIN_SECRET_KEY` - **CRITICAL**: Must be 64+ characters
  - Generate with: `openssl rand -hex 32` or `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
  - Store in Google Secret Manager (never in code or plain text files)
  - Example: `vK8Lm2Pq9RtYuI0oP3aS6dF8gH1jK4lZ7xC9vB2nM5qW0eR3tY6uI8oP1aS4dF7g`

- [ ] `JWT_SECRET` - **CRITICAL**: Must be cryptographically secure
  - Generate with: `openssl rand -hex 32`
  - Store in Google Secret Manager
  
- [ ] `DATABASE_URL` - PostgreSQL connection string
  - Store in Google Secret Manager
  - Includes admin security tables (rate limiting, audit logs, IP lockouts)

### Verify NO Development Bypasses

- [ ] Confirm `DEV_ADMIN_BYPASS` is **NOT SET** in production
- [ ] Confirm `DEV_TOKEN_BYPASS` is **NOT SET** in production
- [ ] Review all environment variables to ensure no dev/test values

**SECURITY WARNING:** If `DEV_ADMIN_BYPASS=true` is set in production, **anyone can access the admin panel without authentication!**

---

## 🛡️ **2. Admin Panel Security Features**

### Verify Security Features Are Active

- [ ] **Rate Limiting**: 5 failed attempts per hour
  - Test by entering wrong key 5 times
  - Verify you get locked out
  
- [ ] **IP Lockout**: 1-hour automatic lockout after 5 failed attempts
  - Test lockout duration
  - Verify lockout clears after successful auth
  
- [ ] **Audit Logging**: All admin actions logged
  - Check PostgreSQL `admin_audit_logs` table exists
  - Verify logs have 90-day retention
  
- [ ] **Timing-Attack Protection**: Constant-time key comparison
  - Implementation uses `secrets.compare_digest()`
  - Already implemented in `api/auth.py:253`

---

## 📊 **3. Database Security**

### Required Database Tables

Verify these tables exist in your PostgreSQL database:

- [ ] `admin_failed_attempt` - Tracks failed login attempts
- [ ] `admin_lockout` - Stores IP lockout information  
- [ ] `admin_audit_log` - Audit trail of all admin actions
- [ ] `users` table with `is_admin` column

**Create tables with:**
```bash
npm run db:push
```

**Or manually verify:**
```sql
\dt admin_*
```

### Set Admin User

- [ ] Verify your user account has `is_admin=true`:
  ```sql
  UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';
  ```

---

## 🌐 **4. Network & Access Security**

### HTTPS & Domain

- [ ] Application is served over HTTPS only
  - Cloud Run enforces HTTPS by default ✅
  - Verify SSL certificate is valid

### Optional: IP Whitelisting

- [ ] Consider enabling IP whitelisting if you have a static IP:
  ```bash
  # Get your IP
  curl -s https://api.ipify.org
  
  # Set in Cloud Run
  gcloud run services update sqlgym-prod \
    --set-env-vars=ADMIN_ALLOWED_IPS="YOUR_IP_ADDRESS" \
    --region=us-central1
  ```

**Note:** Only enable if you have a static IP address

---

## 🔍 **5. Admin Key Security (Single Admin Setup)**

### For Your Use Case (1 Admin = Developer)

Your setup uses `ADMIN_SECRET_KEY` for authentication, which is **production-ready** for a single admin IF:

✅ **SECURE:**
- Key is 64+ characters long
- Stored in Google Secret Manager (not hardcoded)
- Transmitted over HTTPS only
- Rate limiting prevents brute force
- Audit logging tracks all access
- IP lockout after failed attempts

❌ **NOT SECURE:**
- Key less than 32 characters
- Key stored in code or plain text
- Development bypasses enabled (`DEV_ADMIN_BYPASS`)
- No rate limiting
- No HTTPS

### Verification Steps

1. **Test Admin Authentication:**
   ```bash
   # Test with correct key (should work)
   curl -H "X-Admin-Key: YOUR_ADMIN_SECRET_KEY" \
     https://your-app.run.app/api/admin/schema-info
   
   # Test with wrong key (should fail)
   curl -H "X-Admin-Key: wrong-key" \
     https://your-app.run.app/api/admin/schema-info
   
   # Test without key (should fail)
   curl https://your-app.run.app/api/admin/schema-info
   ```

2. **Test Rate Limiting:**
   - Enter wrong key 5 times
   - Verify 6th attempt is blocked with 429 status
   - Wait 1 hour OR clear lockout manually:
     ```sql
     DELETE FROM admin_lockout WHERE ip_address = 'YOUR_IP';
     DELETE FROM admin_failed_attempt WHERE identifier = 'YOUR_IP';
     ```

3. **Test Audit Logging:**
   ```sql
   -- View recent admin actions
   SELECT * FROM admin_audit_log 
   ORDER BY created_at DESC 
   LIMIT 20;
   ```

---

## 🚀 **6. Deployment Configuration**

### Google Cloud Run Setup

- [ ] Secrets are loaded from Secret Manager:
  ```yaml
  --set-secrets=ADMIN_SECRET_KEY=ADMIN_SECRET_KEY:latest,JWT_SECRET=JWT_SECRET:latest,DATABASE_URL=DATABASE_URL:latest
  ```

- [ ] Environment variables are set correctly:
  ```yaml
  --set-env-vars=ENVIRONMENT=production
  ```

- [ ] NO development flags in production:
  - ❌ No `DEV_ADMIN_BYPASS`
  - ❌ No `DEV_TOKEN_BYPASS`
  - ❌ No `DEBUG=true`

---

## 📝 **7. Monitoring & Maintenance**

### Set Up Monitoring

- [ ] **Cloud Logging** - Monitor admin access attempts:
  ```bash
  gcloud logging read 'resource.type="cloud_run_revision" AND textPayload=~"ADMIN"' --limit 50
  ```

- [ ] **Failed Login Alerts** - Alert on 5+ failed attempts:
  ```bash
  gcloud logging metrics create admin_failed_logins \
    --description="Failed admin login attempts" \
    --log-filter='textPayload=~"Invalid admin key"'
  ```

- [ ] **Audit Log Review** - Schedule weekly reviews:
  ```sql
  -- Failed authentication attempts
  SELECT * FROM admin_audit_log 
  WHERE success = false 
  AND action LIKE '%admin%'
  ORDER BY created_at DESC;
  ```

### Regular Maintenance

- [ ] **Rotate ADMIN_SECRET_KEY every 90 days**
  ```bash
  # Generate new key
  NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  
  # Update Secret Manager
  echo -n "$NEW_KEY" | gcloud secrets versions add ADMIN_SECRET_KEY --data-file=-
  
  # Restart Cloud Run
  gcloud run services update sqlgym-prod --region=us-central1
  ```

- [ ] **Review audit logs monthly** for suspicious activity
- [ ] **Clean old audit logs** (auto-cleanup after 90 days)
- [ ] **Verify database backups** include security tables

---

## 🔒 **8. Additional Security Hardening**

### Recommended Enhancements

- [ ] **Enable Cloud Armor** for DDoS protection
- [ ] **Set up VPN** for admin access if accessing from public WiFi
- [ ] **Enable 2FA** on your Google Cloud account
- [ ] **Regular security audits** - Review access logs quarterly
- [ ] **Implement CORS properly** - Restrict admin API to your domain
- [ ] **Add CSP headers** - Already implemented via security middleware

---

## ✅ **Final Pre-Launch Verification**

Before going live, verify:

1. **Secrets**
   - [ ] All secrets in Google Secret Manager
   - [ ] No secrets in code or environment variable files
   - [ ] ADMIN_SECRET_KEY is 64+ characters

2. **Database**
   - [ ] Security tables exist and indexed
   - [ ] Your user has `is_admin=true`
   - [ ] Database backups enabled

3. **Authentication**
   - [ ] Admin key authentication works
   - [ ] Rate limiting active
   - [ ] IP lockout working
   - [ ] Audit logging functional

4. **Network**
   - [ ] HTTPS enforced
   - [ ] Firewall rules configured
   - [ ] Optional: IP whitelisting enabled

5. **Monitoring**
   - [ ] Cloud Logging configured
   - [ ] Alerts set up for failed logins
   - [ ] Audit log review process established

---

## 🎯 **Is This Secure Enough for Production?**

### **YES ✅** - Your single-admin setup is production-ready IF:

1. ✅ ADMIN_SECRET_KEY is strong (64+ characters)
2. ✅ Stored in Google Secret Manager
3. ✅ Transmitted over HTTPS only
4. ✅ Rate limiting enabled (5 attempts/hour)
5. ✅ IP lockout enabled (1 hour after 5 failed attempts)
6. ✅ Audit logging enabled (90-day retention)
7. ✅ NO development bypasses (`DEV_ADMIN_BYPASS` removed)
8. ✅ Optional: IP whitelisting for your static IP

### **Comparison to Other Auth Methods**

| Feature | Your Setup (ADMIN_SECRET_KEY) | Traditional Multi-User Admin |
|---------|-------------------------------|------------------------------|
| **Brute Force Protection** | ✅ Rate limiting + IP lockout | ✅ Same |
| **Audit Trail** | ✅ Full logging | ✅ Same |
| **HTTPS Encryption** | ✅ Yes | ✅ Same |
| **Timing Attack Protection** | ✅ Constant-time comparison | ✅ Same |
| **Key Rotation** | ✅ Manual (90 days recommended) | ✅ Automatic |
| **Multiple Admins** | ❌ Single admin only | ✅ Multiple users |
| **2FA Support** | ❌ Not applicable | ✅ Can add |
| **Complexity** | ✅ Very simple | ⚠️ More complex |
| **Best For** | ✅ Single developer admin | ✅ Team environments |

### **Conclusion**

For your use case (1 admin = you as developer), this implementation is **production-ready and secure**. The simplicity is actually an advantage - fewer moving parts means fewer security vulnerabilities.

---

## 🆘 **Emergency Procedures**

### If ADMIN_SECRET_KEY is Compromised

1. **Immediately rotate the key:**
   ```bash
   # Generate new key
   NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
   echo -n "$NEW_KEY" | gcloud secrets versions add ADMIN_SECRET_KEY --data-file=-
   
   # Restart service
   gcloud run services update sqlgym-prod --region=us-central1
   ```

2. **Review audit logs for unauthorized access:**
   ```sql
   SELECT * FROM admin_audit_log 
   WHERE created_at > NOW() - INTERVAL '7 days'
   ORDER BY created_at DESC;
   ```

3. **Check for suspicious activity:**
   ```sql
   -- Failed attempts
   SELECT ip_address, COUNT(*) as attempts
   FROM admin_audit_log
   WHERE success = false AND action LIKE '%admin%'
   GROUP BY ip_address
   ORDER BY attempts DESC;
   ```

### If Locked Out

```sql
-- Clear your IP lockout
DELETE FROM admin_lockout WHERE ip_address = 'YOUR_IP';
DELETE FROM admin_failed_attempt WHERE identifier = 'YOUR_IP';
```

---

## 📚 **Additional Resources**

- [Production Security Guide](./PRODUCTION_SECURITY_GUIDE.md) - Full deployment guide
- [Cloud Run Deployment Guide](./CLOUD_RUN_DEPLOYMENT.md) - Google Cloud setup
- [Docker Deployment Guide](./DOCKER_DEPLOYMENT.md) - Container deployment

---

**Last Updated:** 2025-10-23  
**Version:** 1.0 (Post Development Bypass Removal)

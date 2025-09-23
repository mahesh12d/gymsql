# 🔐 SECURITY DEPLOYMENT GUIDE

## CRITICAL: Environment Variables Required

This application now requires secure environment variables to prevent the hardcoded admin key vulnerability.

### Required Environment Variables

1. **JWT_SECRET** - For JWT token signing
2. **ADMIN_SECRET_KEY** - For admin authentication

### Generate Secure Keys

```bash
# Generate JWT_SECRET
export JWT_SECRET="$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")"

# Generate ADMIN_SECRET_KEY  
export ADMIN_SECRET_KEY="$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")"
```

### For Production Deployment

**NEVER use default or hardcoded values!** 

Set these in your environment:
- Replit: Add to Secrets in the sidebar
- Other platforms: Set as environment variables in your deployment config

### Security Fix Summary

✅ **Fixed**: Hardcoded admin key `"admin-dev-key-123"` removed
✅ **Fixed**: Hardcoded JWT secret `"your-jwt-secret-key"` removed  
✅ **Fixed**: Development token bypass `"dev-token-123"` removed
✅ **Fixed**: Environment variable validation added
✅ **Fixed**: Application fails fast if secrets are missing

### What This Prevents

- Unauthorized admin access to schema information
- Access to PostgreSQL system tables via admin endpoints
- SQL injection through privileged endpoints
- Unauthorized database metadata exposure

## ⚠️ Breaking Change Notice

**This is a breaking change!** Applications will not start without proper environment variables set.

This is intentional for security - it prevents accidental deployment with default credentials.
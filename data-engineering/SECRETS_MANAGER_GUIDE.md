# AWS Secrets Manager Integration Guide

## 🔐 Production-Ready Security with AWS Secrets Manager

This pipeline now uses **AWS Secrets Manager** for storing database credentials, following AWS security best practices. This provides:

- ✅ **Encrypted storage** of sensitive credentials
- ✅ **Automatic rotation** support for passwords
- ✅ **Fine-grained IAM access control**
- ✅ **Audit logging** via CloudTrail
- ✅ **No plaintext secrets** in environment variables or code

---

## 📋 Prerequisites

1. AWS CLI installed and configured
2. Appropriate IAM permissions:
   - `secretsmanager:CreateSecret`
   - `secretsmanager:UpdateSecret`
   - `secretsmanager:GetSecretValue`
3. Neon Postgres database credentials ready

---

## 🚀 Quick Setup (3 Steps)

### Step 1: Create the Secret in AWS

**Option A: Using Python Script (Recommended)**
```bash
cd data-engineering
python scripts/create_db_secret.py production --region us-east-1
```

**Option B: Using Bash Script**
```bash
cd data-engineering
./scripts/create_db_secret.sh production us-east-1
```

**Option C: Using AWS CLI Directly**
```bash
aws secretsmanager create-secret \
  --name production/sqlgym/database \
  --description "Database credentials for SQLGym production" \
  --secret-string '{
    "host": "your-neon-host.neon.tech",
    "port": "5432",
    "database": "sqlgym",
    "username": "your-username",
    "password": "your-password"
  }' \
  --region us-east-1
```

**Expected Output:**
```json
{
    "ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:production/sqlgym/database-AbCdEf",
    "Name": "production/sqlgym/database",
    "VersionId": "..."
}
```

**📝 Save the ARN** - You'll need it for deployment!

---

### Step 2: Deploy Lambda with Secret ARN

Update your deployment command to use the secret ARN:

```bash
make deploy ENVIRONMENT=production \
  DATABASE_SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789012:secret:production/sqlgym/database-AbCdEf" \
  S3_BUCKET_NAME="sqlgym-data-lake-production"
```

Or use SAM CLI directly:

```bash
sam deploy \
  --template-file template.yaml \
  --stack-name sqlgym-pipeline-production \
  --parameter-overrides \
    Environment=production \
    DatabaseSecretArn="arn:aws:secretsmanager:us-east-1:123456789012:secret:production/sqlgym/database-AbCdEf" \
    S3BucketName="sqlgym-data-lake-production" \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

---

### Step 3: Test the Deployment

```bash
# Invoke the Lambda function
make invoke

# Check logs for successful secret retrieval
make logs
```

You should see in the logs:
```
Retrieving secret from AWS Secrets Manager: arn:aws:secretsmanager:...
Successfully retrieved and cached secret: arn:aws:secretsmanager:...
Database config loaded from secret: arn:aws:secretsmanager:...
```

---

## 🔄 Updating Database Credentials

### Method 1: Using the Python Script
```bash
python scripts/create_db_secret.py production --region us-east-1
# Enter new credentials when prompted
```

### Method 2: Using AWS CLI
```bash
aws secretsmanager update-secret \
  --secret-id production/sqlgym/database \
  --secret-string '{
    "host": "new-host.neon.tech",
    "port": "5432",
    "database": "sqlgym",
    "username": "new-username",
    "password": "new-password"
  }' \
  --region us-east-1
```

### Method 3: Using AWS Console
1. Go to AWS Secrets Manager console
2. Find `production/sqlgym/database`
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update the JSON and save

**⚠️ Note:** Lambda containers cache secrets. After updating, either:
- Wait for container recycling (automatic after ~15-30 minutes of inactivity)
- Manually redeploy the Lambda function
- Update an environment variable to force redeployment

---

## 🏗️ Secret Structure

The secret **must** be stored as a JSON object with these keys:

```json
{
  "host": "your-neon-host.neon.tech",
  "port": "5432",
  "database": "sqlgym",
  "username": "your-db-username",
  "password": "your-db-password"
}
```

**Required Fields:**
- `host` - Neon Postgres endpoint
- `database` - Database name
- `username` - Database username
- `password` - Database password

**Optional Fields:**
- `port` - Database port (defaults to 5432 if not provided)

---

## 🔒 Security Best Practices

### 1. **Use Separate Secrets per Environment**
```bash
# Development
production/sqlgym/database

# Staging
staging/sqlgym/database

# Production
production/sqlgym/database
```

### 2. **Enable Automatic Rotation**
```bash
aws secretsmanager rotate-secret \
  --secret-id production/sqlgym/database \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotation \
  --rotation-rules AutomaticallyAfterDays=30
```

### 3. **Restrict IAM Permissions**

The Lambda IAM role only has permission to:
- Get secret values (`secretsmanager:GetSecretValue`)
- Describe secrets (`secretsmanager:DescribeSecret`)
- Decrypt with KMS (`kms:Decrypt` via Secrets Manager service)

To further restrict, update the IAM policy to specific secret ARNs only.

### 4. **Enable CloudTrail Logging**
```bash
# Monitor who accessed the secret
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=production/sqlgym/database \
  --max-items 50
```

### 5. **Use Resource Policies** (Optional)
```bash
aws secretsmanager put-resource-policy \
  --secret-id production/sqlgym/database \
  --resource-policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Deny",
      "Principal": "*",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": ["0.0.0.0/0"]
        }
      }
    }]
  }'
```

---

## 🧪 Testing Secret Retrieval

### Test 1: Retrieve Secret via AWS CLI
```bash
aws secretsmanager get-secret-value \
  --secret-id production/sqlgym/database \
  --region us-east-1 \
  --query 'SecretString' \
  --output text | jq
```

### Test 2: Test Lambda Function Locally
```bash
# Set environment variable
export DB_SECRET_NAME="production/sqlgym/database"
export AWS_REGION="us-east-1"

# Run local test
python scripts/test_local.py --test connection
```

### Test 3: Invoke Lambda and Check Logs
```bash
# Invoke Lambda
aws lambda invoke \
  --function-name production-sqlgym-postgres-to-s3 \
  --payload '{"sync_type": "incremental", "tables": ["users"]}' \
  --region us-east-1 \
  response.json

# Check logs
aws logs tail /aws/lambda/production-sqlgym-postgres-to-s3 --follow
```

---

## 💰 Cost Estimation

**AWS Secrets Manager Pricing:**
- **Storage:** $0.40 per secret per month
- **API Calls:** $0.05 per 10,000 requests

**For this pipeline:**
- 1 secret = **$0.40/month**
- ~720 Lambda invocations/month (hourly schedule) = **$0.004/month**
- **Total Secrets Manager cost: ~$0.41/month**

**Comparison:**
- ✅ Secrets Manager: $0.41/month + enterprise-grade security
- ❌ Environment variables: Free + plaintext credentials (not production-ready)

---

## 🆘 Troubleshooting

### Error: "ResourceNotFoundException"
**Cause:** Secret doesn't exist or wrong region
```bash
# List all secrets in region
aws secretsmanager list-secrets --region us-east-1
```

### Error: "AccessDeniedException"
**Cause:** Lambda IAM role lacks permissions
```bash
# Check Lambda execution role
aws lambda get-function --function-name production-sqlgym-postgres-to-s3 \
  --query 'Configuration.Role' --output text

# Check role policies
aws iam list-attached-role-policies --role-name <role-name>
```

### Error: "DecryptionFailure"
**Cause:** KMS key permissions issue
```bash
# Check secret encryption key
aws secretsmanager describe-secret \
  --secret-id production/sqlgym/database \
  --query 'KmsKeyId' --output text
```

### Secret Not Updating in Lambda
**Cause:** Container caching
**Solution:**
1. Wait 15-30 minutes for container recycling
2. Force update by changing any environment variable
3. Redeploy Lambda function

### Connection Still Failing
**Check secret format:**
```bash
# Validate JSON structure
aws secretsmanager get-secret-value \
  --secret-id production/sqlgym/database \
  --query 'SecretString' --output text | jq .
```

Expected keys: `host`, `port`, `database`, `username`, `password`

---

## 📚 Additional Resources

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Secrets Manager Pricing](https://aws.amazon.com/secrets-manager/pricing/)
- [Secret Rotation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

---

## ✅ Migration Checklist

For teams migrating from `.env` to Secrets Manager:

- [ ] Create secret in AWS Secrets Manager
- [ ] Save secret ARN securely
- [ ] Update deployment scripts with secret ARN
- [ ] Deploy updated Lambda function
- [ ] Test secret retrieval in logs
- [ ] Remove old `.env` files from version control
- [ ] Update team documentation
- [ ] Configure secret rotation (optional)
- [ ] Set up CloudTrail monitoring
- [ ] Verify cost tracking in AWS Cost Explorer

---

**🎉 Congratulations!** Your pipeline now follows AWS security best practices with encrypted credential storage.

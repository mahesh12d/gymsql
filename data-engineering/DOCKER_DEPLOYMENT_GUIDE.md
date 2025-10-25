# 🐳 Deploy Lambda Using Docker (No Library Issues!)

Docker containers eliminate ALL dependency problems. This guide uses minimal CLI commands.

---

## **Prerequisites**

- Docker Desktop installed on your computer
- AWS CLI configured (`aws configure`)
- Download the `data-engineering` folder from Replit

---

## **Step 1: Download Code from Replit**

1. In Replit, right-click the `data-engineering` folder
2. Click "Download"
3. Extract the ZIP on your local computer
4. Open Terminal/PowerShell and navigate to it:
   ```bash
   cd ~/Downloads/data-engineering
   ```

---

## **Step 2: Build the Docker Image**

This packages everything (code + all dependencies) into one container:

**On Mac/Linux:**
```bash
docker build --platform linux/amd64 -t sqlgym-lambda:latest .
```

**On Windows PowerShell:**
```powershell
docker build --platform linux/amd64 -t sqlgym-lambda:latest .
```

⏱️ This takes 2-3 minutes. You'll see it installing psycopg2, pandas, pyarrow, etc.

---

## **Step 3: Create ECR Repository (AWS Console)**

ECR (Elastic Container Registry) is where you store your Docker image in AWS.

1. Go to **Amazon ECR Console**: https://console.aws.amazon.com/ecr/
2. Click **"Get Started"** or **"Create repository"**
3. **Repository name**: `sqlgym-lambda`
4. **Tag immutability**: Disabled
5. **Scan on push**: Enabled (recommended)
6. Click **"Create repository"**
7. **📋 COPY THE URI** - looks like:
   ```
   577004484777.dkr.ecr.us-east-1.amazonaws.com/sqlgym-lambda
   ```

---

## **Step 4: Push Image to ECR (Command Line)**

You need to use CLI for this part (Docker push requires it):

### **A. Authenticate Docker to ECR**

**Mac/Linux:**
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  577004484777.dkr.ecr.us-east-1.amazonaws.com
```

**Windows PowerShell:**
```powershell
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 577004484777.dkr.ecr.us-east-1.amazonaws.com
```

You should see: `Login Succeeded`

### **B. Tag Your Image**

Replace `577004484777` with your AWS account ID:

```bash
docker tag sqlgym-lambda:latest \
  577004484777.dkr.ecr.us-east-1.amazonaws.com/sqlgym-lambda:latest
```

### **C. Push to ECR**

```bash
docker push 577004484777.dkr.ecr.us-east-1.amazonaws.com/sqlgym-lambda:latest
```

⏱️ This takes 3-5 minutes (uploading ~500MB).

---

## **Step 5: Create Database Secret (AWS Console)**

1. Go to **Secrets Manager**: https://console.aws.amazon.com/secretsmanager/
2. Click **"Store a new secret"**
3. **Secret type**: Other type of secret
4. Add these key-value pairs:
   ```
   host      = your-neon-host.neon.tech
   port      = 5432
   database  = sqlgym
   username  = your_db_username
   password  = your_db_password
   ```
5. Click **"Next"**
6. **Secret name**: `production/sqlgym/database`
7. Click **"Next"** → **"Next"** → **"Store"**
8. **📋 SAVE THE ARN**

---

## **Step 6: Create S3 Bucket (AWS Console)**

1. Go to **S3**: https://s3.console.aws.amazon.com/s3/
2. Click **"Create bucket"**
3. **Name**: `sqlgym-data-577004484777` (must be unique)
4. **Region**: `us-east-1`
5. **Versioning**: Enable
6. Click **"Create bucket"**

---

## **Step 7: Create IAM Role (AWS Console)**

1. Go to **IAM Roles**: https://console.aws.amazon.com/iam/home#/roles
2. Click **"Create role"**
3. **Trusted entity**: AWS service → Lambda
4. Click **"Next"**
5. Attach these policies:
   - ✅ `AmazonS3FullAccess`
   - ✅ `SecretsManagerReadWrite`
   - ✅ `CloudWatchLogsFullAccess`
6. Click **"Next"**
7. **Role name**: `SQLGymLambdaRole`
8. Click **"Create role"**

---

## **Step 8: Create Lambda Function from Docker Image (AWS Console)**

1. Go to **Lambda Console**: https://console.aws.amazon.com/lambda/
2. Click **"Create function"**
3. Select **"Container image"** (not "Author from scratch"!)
4. **Function name**: `sqlgym-data-sync`
5. **Container image URI**:
   - Click **"Browse images"**
   - Select repository: `sqlgym-lambda`
   - Select image tag: `latest`
   - Click **"Select image"**
6. **Architecture**: x86_64
7. **Execution role**:
   - Select **"Use an existing role"**
   - Choose: `SQLGymLambdaRole`
8. Click **"Create function"**

---

## **Step 9: Configure Environment Variables**

1. In your Lambda function, click **"Configuration"** tab
2. Click **"Environment variables"** → **"Edit"**
3. Add these:
   ```
   DB_SECRET_NAME = production/sqlgym/database
   S3_BUCKET = sqlgym-data-577004484777
   AWS_REGION = us-east-1
   ```
4. Click **"Save"**

---

## **Step 10: Increase Timeout & Memory**

1. Still in **"Configuration"** tab
2. Click **"General configuration"** → **"Edit"**
3. Set:
   - **Memory**: 3008 MB
   - **Timeout**: 15 min 0 sec
   - **Storage**: 512 MB
4. Click **"Save"**

---

## **Step 11: Test It!**

1. Go to **"Test"** tab
2. Click **"Create new test event"**
3. **Event name**: `test-sync`
4. Paste this JSON:
   ```json
   {
     "force_full_sync": false,
     "tables": []
   }
   ```
5. Click **"Save"**
6. Click **"Test"**

✅ You should see: **Execution result: succeeded**

Check the logs to see tables being synced!

---

## **Step 12: Verify Data in S3**

1. Go to your S3 bucket
2. You should see folders like:
   - `users/2025/10/25/`
   - `problems/2025/10/25/`
3. Click into folders to see `.parquet` files

---

## **Step 13: (Optional) Schedule Hourly Syncs**

1. Go to **EventBridge**: https://console.aws.amazon.com/events/
2. Click **"Create rule"**
3. **Name**: `sqlgym-hourly-sync`
4. **Rule type**: Schedule
5. **Schedule**: Rate-based → `1` hours
6. Click **"Next"**
7. **Target**: Lambda function → `sqlgym-data-sync`
8. Click **"Next"** → **"Next"** → **"Create rule"**

---

## **✅ Benefits of Docker Deployment**

- ✅ **No library issues** - All dependencies bundled correctly
- ✅ **No Lambda layers needed** - Everything in one container
- ✅ **Easier debugging** - Can test locally with Docker
- ✅ **Version control** - Tag images with versions
- ✅ **Reproducible** - Same environment every time

---

## **Updating the Function (After Code Changes)**

1. **Rebuild the image**:
   ```bash
   docker build --platform linux/amd64 -t sqlgym-lambda:latest .
   ```

2. **Re-tag and push**:
   ```bash
   docker tag sqlgym-lambda:latest \
     577004484777.dkr.ecr.us-east-1.amazonaws.com/sqlgym-lambda:latest
   
   docker push 577004484777.dkr.ecr.us-east-1.amazonaws.com/sqlgym-lambda:latest
   ```

3. **Update Lambda (AWS Console)**:
   - Go to your function
   - Click **"Image"** tab
   - Click **"Deploy new image"**
   - Select the updated image
   - Click **"Save"**

---

## **Cost Estimate**

- ECR storage: $0.10/GB/month (~$0.05/month for this image)
- Lambda: $2-5/month (execution time)
- S3: $2-3/month (storage)
- **Total: ~$5-9/month**

---

**You're done! No more library issues!** 🎉

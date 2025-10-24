#!/bin/bash

set -e

ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="sqlgym-postgres-to-s3-${ENVIRONMENT}"

echo "========================================="
echo "Deploying SQLGym Postgres to S3 Pipeline"
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"
echo "========================================="

cd "$(dirname "$0")/.."

echo "Step 1: Installing Python dependencies..."
pip install -r requirements.txt -t lambda/

echo "Step 2: Validating SAM template..."
sam validate --template template.yaml --region $AWS_REGION

echo "Step 3: Building SAM application..."
sam build --template template.yaml

echo "Step 4: Deploying to AWS..."
sam deploy \
  --template-file template.yaml \
  --stack-name $STACK_NAME \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION \
  --parameter-overrides \
    Environment=$ENVIRONMENT \
    DatabaseHost=$DB_HOST \
    DatabaseName=$DB_NAME \
    DatabaseUser=$DB_USER \
    DatabasePassword=$DB_PASSWORD \
    S3BucketName=$S3_BUCKET_NAME \
    SyncSchedule="$SYNC_SCHEDULE" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

echo "========================================="
echo "Deployment completed successfully!"
echo "========================================="

echo "To invoke the function manually:"
echo "aws lambda invoke --function-name ${ENVIRONMENT}-sqlgym-postgres-to-s3 --region $AWS_REGION output.json"

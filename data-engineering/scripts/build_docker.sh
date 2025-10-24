#!/bin/bash

set -e

ENVIRONMENT=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="sqlgym-postgres-to-s3"
IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

echo "========================================="
echo "Building Docker image for Lambda"
echo "Environment: $ENVIRONMENT"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Image Tag: $IMAGE_TAG"
echo "========================================="

cd "$(dirname "$0")/.."

echo "Step 1: Create ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION 2>/dev/null || \
  aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION

echo "Step 2: Login to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "Step 3: Build Docker image..."
docker build --platform linux/amd64 -t $ECR_REPO:$IMAGE_TAG .

echo "Step 4: Tag image for ECR..."
docker tag $ECR_REPO:$IMAGE_TAG \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$IMAGE_TAG

docker tag $ECR_REPO:$IMAGE_TAG \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$ENVIRONMENT-latest

echo "Step 5: Push to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$IMAGE_TAG
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$ENVIRONMENT-latest

echo "========================================="
echo "Docker image built and pushed successfully!"
echo "Image URI: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
echo "========================================="

echo "To update Lambda function with new image:"
echo "aws lambda update-function-code \\"
echo "  --function-name ${ENVIRONMENT}-sqlgym-postgres-to-s3 \\"
echo "  --image-uri ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_REPO:$IMAGE_TAG \\"
echo "  --region $AWS_REGION"

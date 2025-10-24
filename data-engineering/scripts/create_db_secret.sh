#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==============================================="
echo "AWS Secrets Manager - Database Secret Creator"
echo "==============================================="
echo ""
echo "⚠️  WARNING: This bash script may fail if passwords"
echo "   contain special characters (quotes, backslashes, etc.)"
echo ""
echo "   RECOMMENDED: Use the Python version instead:"
echo "   python scripts/create_db_secret.py $1 ${2:-us-east-1}"
echo ""
read -p "Continue with bash script? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi
echo ""

if [ -z "$1" ]; then
    echo "Usage: $0 <environment> [region]"
    echo ""
    echo "Example: $0 production us-east-1"
    echo "Example: $0 staging"
    echo ""
    exit 1
fi

ENVIRONMENT=$1
AWS_REGION=${2:-us-east-1}
SECRET_NAME="${ENVIRONMENT}/sqlgym/database"

echo "Environment: $ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Secret Name: $SECRET_NAME"
echo ""

read -p "Enter Neon Postgres Host (e.g., your-db.neon.tech): " DB_HOST
read -p "Enter Database Name [sqlgym]: " DB_NAME
DB_NAME=${DB_NAME:-sqlgym}
read -p "Enter Database Port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}
read -p "Enter Database Username: " DB_USER
read -sp "Enter Database Password: " DB_PASSWORD
echo ""
echo ""

SECRET_VALUE=$(cat <<EOF
{
  "host": "$DB_HOST",
  "port": "$DB_PORT",
  "database": "$DB_NAME",
  "username": "$DB_USER",
  "password": "$DB_PASSWORD"
}
EOF
)

echo "Creating secret in AWS Secrets Manager..."
echo ""

if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" &>/dev/null; then
    echo "Secret already exists. Updating..."
    SECRET_ARN=$(aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE" \
        --region "$AWS_REGION" \
        --query 'ARN' \
        --output text)
else
    echo "Creating new secret..."
    SECRET_ARN=$(aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Database credentials for SQLGym $ENVIRONMENT environment" \
        --secret-string "$SECRET_VALUE" \
        --region "$AWS_REGION" \
        --tags Key=Environment,Value="$ENVIRONMENT" Key=Project,Value=SQLGym \
        --query 'ARN' \
        --output text)
fi

echo ""
echo "✅ Secret created/updated successfully!"
echo ""
echo "Secret ARN: $SECRET_ARN"
echo ""
echo "==============================================="
echo "Next Steps:"
echo "==============================================="
echo "1. Copy this ARN and save it securely"
echo "2. Use it when deploying your Lambda function:"
echo ""
echo "   make deploy ENVIRONMENT=$ENVIRONMENT \\"
echo "     DATABASE_SECRET_ARN=\"$SECRET_ARN\" \\"
echo "     S3_BUCKET_NAME=\"your-bucket-name\""
echo ""
echo "3. Or update your deployment script with the ARN"
echo ""
echo "To test the secret retrieval:"
echo "  aws secretsmanager get-secret-value --secret-id $SECRET_NAME --region $AWS_REGION"
echo ""

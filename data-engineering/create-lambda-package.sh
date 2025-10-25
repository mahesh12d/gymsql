#!/bin/bash

# Script to create a Lambda deployment package for manual upload
# This creates a .zip file you can upload directly to AWS Lambda Console

echo "Creating Lambda deployment package..."

# Create a temporary directory
mkdir -p lambda-package
cd lambda-package

# Copy the Lambda handler
cp ../lambda/handler.py .

# Copy configuration files
cp ../pipeline_config.json .
cp ../database_config.json .

# Install Python dependencies
echo "Installing Python dependencies..."
pip install \
  psycopg2-binary \
  pandas \
  pyarrow \
  boto3 \
  -t .

# Create the zip file
echo "Creating deployment.zip..."
zip -r ../lambda-deployment.zip .

# Cleanup
cd ..
rm -rf lambda-package

echo "✅ Done! File created: lambda-deployment.zip"
echo ""
echo "📦 Package size:"
ls -lh lambda-deployment.zip
echo ""
echo "Next steps:"
echo "1. Download 'lambda-deployment.zip' from Replit"
echo "2. Upload it to AWS Lambda Console"

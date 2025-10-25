#!/bin/bash

# SQLGym - Google Cloud Run Deployment Script
# This script deploys the full-stack app using Docker

set -e

# Configuration
PROJECT_ID="${GCLOUD_PROJECT_ID:-sqlgym-app}"
REGION="${GCLOUD_REGION:-us-central1}"
SERVICE_NAME="${GCLOUD_SERVICE_NAME:-sqlgym}"
MEMORY="${GCLOUD_MEMORY:-2Gi}"
CPU="${GCLOUD_CPU:-2}"

echo "🚀 Deploying SQLGym to Google Cloud Run"
echo "================================================"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo "Memory: $MEMORY"
echo "CPU: $CPU"
echo "================================================"

# Set the project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs (if not already enabled)
echo "🔌 Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Build using Dockerfile and deploy
echo "🐳 Building and deploying with Docker..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory $MEMORY \
  --cpu $CPU \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --port 8080 \
  --set-env-vars "ENV=production"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set your environment variables (DATABASE_URL, JWT_SECRET, etc.)"
echo "2. Test your deployment"
echo ""
echo "To set environment variables:"
echo "gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars DATABASE_URL=your_db_url"
echo ""

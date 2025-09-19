#!/bin/bash
# Git to S3 Migration Runner
# 
# This script helps administrators migrate parquet files from Git repositories to S3 storage.
#
# Prerequisites:
# 1. AWS credentials configured (AWS CLI or environment variables)
# 2. DATABASE_URL environment variable set
# 3. Python 3.8+ installed
# 4. S3 bucket created with appropriate permissions
#
# Usage:
#   ./scripts/run_migration.sh your-dataset-bucket [--dry-run]
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if S3 bucket is provided
if [ $# -eq 0 ]; then
    error "Usage: $0 <s3-bucket-name> [--dry-run]"
fi

S3_BUCKET="$1"
DRY_RUN_FLAG=""
if [ "$2" = "--dry-run" ]; then
    DRY_RUN_FLAG="--dry-run"
    warn "Running in DRY RUN mode - no changes will be made"
fi

info "Starting Git to S3 migration for bucket: $S3_BUCKET"

# Check prerequisites
info "Checking prerequisites..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    error "DATABASE_URL environment variable is not set"
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    error "Python 3 is not installed or not in PATH"
fi

# Check if AWS credentials are configured (lightweight check)
if ! python3 -c "import boto3; boto3.client('s3')" &> /dev/null; then
    error "AWS credentials are not configured or boto3 is not available"
fi

# Check if S3 bucket exists and is accessible
info "Verifying S3 bucket access..."
if ! python3 -c "import boto3; boto3.client('s3').head_bucket(Bucket='$S3_BUCKET')" &> /dev/null; then
    error "S3 bucket '$S3_BUCKET' does not exist or is not accessible"
fi

# Install Python dependencies if needed
if [ ! -f "scripts/.migration_deps_installed" ]; then
    info "Installing Python dependencies..."
    pip install -r scripts/requirements.txt
    touch scripts/.migration_deps_installed
    info "Dependencies installed"
else
    info "Dependencies already installed"
fi

# Run the migration
info "Starting migration process..."
python3 scripts/migrate_git_to_s3.py --s3-bucket "$S3_BUCKET" $DRY_RUN_FLAG --verbose

if [ $? -eq 0 ]; then
    if [ "$DRY_RUN_FLAG" = "--dry-run" ]; then
        info "Dry run completed successfully!"
        info "Run without --dry-run to perform the actual migration"
    else
        info "Migration completed successfully!"
        info "All Git-based parquet files have been migrated to S3"
    fi
else
    error "Migration failed - check the logs above for details"
fi
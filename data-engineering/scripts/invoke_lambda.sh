#!/bin/bash

set -e

ENVIRONMENT=${1:-production}
SYNC_TYPE=${2:-incremental}
AWS_REGION=${AWS_REGION:-us-east-1}
FUNCTION_NAME="${ENVIRONMENT}-sqlgym-postgres-to-s3"

echo "Invoking Lambda function: $FUNCTION_NAME"
echo "Sync type: $SYNC_TYPE"
echo "Region: $AWS_REGION"

PAYLOAD=$(cat <<EOF
{
  "sync_type": "$SYNC_TYPE",
  "force_full_sync": false
}
EOF
)

echo "Payload: $PAYLOAD"

aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --region $AWS_REGION \
  --payload "$PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
  response.json

echo ""
echo "Response:"
cat response.json | jq '.'

echo ""
echo "Lambda invocation completed!"

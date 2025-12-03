#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - Update Lambda Endpoints
# Updates Optimizer Lambda with SageMaker endpoint names

# Configuration
REGION="${AWS_REGION:-us-east-2}"

echo "=========================================="
echo "Updating Lambda Endpoints Configuration"
echo "=========================================="
echo ""

# Check if endpoints exist and are InService
check_endpoint() {
  local endpoint_name=$1

  STATUS=$(aws sagemaker describe-endpoint \
    --endpoint-name "${endpoint_name}" \
    --query 'EndpointStatus' \
    --output text \
    --region "${REGION}" \
    2>/dev/null || echo "NOT_FOUND")

  echo "${STATUS}"
}

CREATIVE_SCORER_STATUS=$(check_endpoint "linkedin-ads-creative-scorer")
BID_OPTIMIZER_STATUS=$(check_endpoint "linkedin-ads-bid-optimizer")

echo "Endpoint Status:"
echo "  Creative Scorer: ${CREATIVE_SCORER_STATUS}"
echo "  Bid Optimizer:   ${BID_OPTIMIZER_STATUS}"
echo ""

if [ "${CREATIVE_SCORER_STATUS}" != "InService" ] && [ "${BID_OPTIMIZER_STATUS}" != "InService" ]; then
  echo "⚠️  No endpoints are InService yet."
  echo "   Deploy endpoints first: ./deploy-endpoints.sh"
  echo "   Then wait for them to become InService before running this script."
  exit 1
fi

# Get current environment variables
echo "📝 Updating Optimizer Lambda environment variables..."

CURRENT_ENV=$(aws lambda get-function-configuration \
  --function-name linkedin-ads-optimizer \
  --query 'Environment.Variables' \
  --region "${REGION}")

# Update endpoint names
UPDATED_ENV=$(echo "${CURRENT_ENV}" | jq \
  --arg creative_endpoint "${CREATIVE_SCORER_STATUS}" \
  --arg bid_endpoint "${BID_OPTIMIZER_STATUS}" \
  'if $creative_endpoint == "InService" then .CREATIVE_SCORER_ENDPOINT = "linkedin-ads-creative-scorer" else . end |
   if $bid_endpoint == "InService" then .BID_OPTIMIZER_ENDPOINT = "linkedin-ads-bid-optimizer" else . end')

# Apply update
aws lambda update-function-configuration \
  --function-name linkedin-ads-optimizer \
  --environment "Variables=${UPDATED_ENV}" \
  --region "${REGION}" \
  > /dev/null

echo "✓ Environment variables updated"
echo ""

echo "=========================================="
echo "✅ Lambda Configuration Updated!"
echo "=========================================="
echo ""
echo "Updated Endpoints:"

if [ "${CREATIVE_SCORER_STATUS}" == "InService" ]; then
  echo "  ✓ CREATIVE_SCORER_ENDPOINT = linkedin-ads-creative-scorer"
fi

if [ "${BID_OPTIMIZER_STATUS}" == "InService" ]; then
  echo "  ✓ BID_OPTIMIZER_ENDPOINT = linkedin-ads-bid-optimizer"
fi

echo ""
echo "The Optimizer Lambda will now use ML models for predictions!"
echo ""

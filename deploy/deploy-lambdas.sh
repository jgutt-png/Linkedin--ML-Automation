#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - Lambda Deployment Script
# Deploys all Lambda functions with proper configuration

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="linkedin-ads-data-${ACCOUNT_ID}"
ATHENA_BUCKET="linkedin-ads-athena-results-${ACCOUNT_ID}"
DEPLOYMENT_BUCKET="linkedin-ads-deployments-${ACCOUNT_ID}"

echo "=========================================="
echo "Deploying Lambda Functions"
echo "=========================================="
echo ""

deploy_lambda() {
  local function_name=$1
  local role_suffix=$2
  local handler=$3
  local timeout=$4
  local memory=$5
  local description=$6

  local role_arn="arn:aws:iam::${ACCOUNT_ID}:role/LinkedInAds${role_suffix}Role"
  local code_uri="s3://${DEPLOYMENT_BUCKET}/lambda/${function_name}.zip"

  echo "📦 Deploying ${function_name}..."

  # Check if function exists
  if aws lambda get-function --function-name "${function_name}" --region "${REGION}" 2>/dev/null; then
    echo "  → Updating existing function..."

    aws lambda update-function-code \
      --function-name "${function_name}" \
      --s3-bucket "${DEPLOYMENT_BUCKET}" \
      --s3-key "lambda/${function_name}.zip" \
      --region "${REGION}" \
      > /dev/null

    aws lambda update-function-configuration \
      --function-name "${function_name}" \
      --timeout "${timeout}" \
      --memory-size "${memory}" \
      --region "${REGION}" \
      > /dev/null

  else
    echo "  → Creating new function..."

    aws lambda create-function \
      --function-name "${function_name}" \
      --runtime python3.11 \
      --role "${role_arn}" \
      --handler "${handler}" \
      --code "S3Bucket=${DEPLOYMENT_BUCKET},S3Key=lambda/${function_name}.zip" \
      --description "${description}" \
      --timeout "${timeout}" \
      --memory-size "${memory}" \
      --region "${REGION}" \
      > /dev/null
  fi

  echo "  ✓ Function deployed"
}

# Deploy Data Processor Lambda
deploy_lambda \
  "linkedin-ads-data-processor" \
  "DataProcessor" \
  "handler.lambda_handler" \
  300 \
  1024 \
  "Prepares ML training data from LinkedIn Ads performance data"

# Set environment variables
aws lambda update-function-configuration \
  --function-name "linkedin-ads-data-processor" \
  --environment "Variables={
    BUCKET_NAME=${BUCKET_NAME},
    ATHENA_OUTPUT_BUCKET=${ATHENA_BUCKET},
    ATHENA_DATABASE=linkedin_ads
  }" \
  --region "${REGION}" \
  > /dev/null

echo ""

# Deploy Optimizer Lambda
deploy_lambda \
  "linkedin-ads-optimizer" \
  "Optimizer" \
  "handler.lambda_handler" \
  600 \
  2048 \
  "Main optimization engine - pauses losers, scales winners, adjusts bids"

# Get SNS Topic ARN
SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'linkedin-ads-alerts')].TopicArn" --output text)

# Set environment variables
aws lambda update-function-configuration \
  --function-name "linkedin-ads-optimizer" \
  --environment "Variables={
    BUCKET_NAME=${BUCKET_NAME},
    ATHENA_OUTPUT_BUCKET=${ATHENA_BUCKET},
    ATHENA_DATABASE=linkedin_ads,
    LINKEDIN_ACCESS_TOKEN_SECRET=linkedin-access-token,
    SNS_TOPIC_ARN=${SNS_TOPIC_ARN},
    MIN_CTR_THRESHOLD=1.0,
    TOP_PERFORMER_THRESHOLD=3.0,
    MAX_CPC=8.0,
    MIN_SAMPLE_SIZE=100,
    BID_CHANGE_THRESHOLD=0.50,
    CREATIVE_SCORER_ENDPOINT=,
    BID_OPTIMIZER_ENDPOINT=
  }" \
  --region "${REGION}" \
  > /dev/null

echo ""

# Deploy Copy Generator Lambda
deploy_lambda \
  "linkedin-ads-copy-generator" \
  "CopyGenerator" \
  "handler.lambda_handler" \
  300 \
  512 \
  "Generates new ad copy variations using Claude API"

# Set environment variables
aws lambda update-function-configuration \
  --function-name "linkedin-ads-copy-generator" \
  --environment "Variables={
    BUCKET_NAME=${BUCKET_NAME},
    ATHENA_OUTPUT_BUCKET=${ATHENA_BUCKET},
    ANTHROPIC_API_KEY_SECRET=anthropic-api-key
  }" \
  --region "${REGION}" \
  > /dev/null

echo ""

# Deploy Token Rotator Lambda
deploy_lambda \
  "linkedin-ads-token-rotator" \
  "TokenRotator" \
  "handler.lambda_handler" \
  180 \
  256 \
  "Automatic LinkedIn OAuth token rotation every 60 days"

# Get SNS Topic ARN
SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'linkedin-ads-alerts')].TopicArn" --output text)

# Set environment variables
aws lambda update-function-configuration \
  --function-name "linkedin-ads-token-rotator" \
  --environment "Variables={
    SNS_TOPIC_ARN=${SNS_TOPIC_ARN}
  }" \
  --region "${REGION}" \
  > /dev/null

echo ""
echo "=========================================="
echo "✅ All Lambda Functions Deployed!"
echo "=========================================="
echo ""
echo "Functions:"
echo "  • linkedin-ads-data-processor"
echo "  • linkedin-ads-optimizer"
echo "  • linkedin-ads-copy-generator"
echo "  • linkedin-ads-token-rotator"
echo ""
echo "Next Steps:"
echo "1. Store secrets in AWS Secrets Manager:"
echo "   - linkedin-access-token (LinkedIn API token)"
echo "   - anthropic-api-key (Claude API key)"
echo ""
echo "2. Configure token rotation: ./setup-token-rotation.sh"
echo "3. Create EventBridge schedules: ./deploy-schedules.sh"
echo ""

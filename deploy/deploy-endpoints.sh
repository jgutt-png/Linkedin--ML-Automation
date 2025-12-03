#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - SageMaker Endpoint Deployment
# Deploys trained models to real-time inference endpoints

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="linkedin-ads-data-${ACCOUNT_ID}"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LinkedInAdsSageMakerRole"

echo "=========================================="
echo "SageMaker Endpoint Deployment"
echo "=========================================="
echo ""

# Function to find latest successful training job
find_latest_training_job() {
  local job_prefix=$1

  aws sagemaker list-training-jobs \
    --name-contains "${job_prefix}" \
    --status-equals Completed \
    --sort-by CreationTime \
    --sort-order Descending \
    --max-results 1 \
    --query 'TrainingJobSummaries[0].TrainingJobName' \
    --output text \
    --region "${REGION}"
}

# Function to deploy endpoint
deploy_endpoint() {
  local model_name=$1
  local training_job=$2
  local endpoint_name=$3

  echo "📦 Deploying ${model_name}..."

  # Get model artifacts from training job
  MODEL_DATA=$(aws sagemaker describe-training-job \
    --training-job-name "${training_job}" \
    --query 'ModelArtifacts.S3ModelArtifacts' \
    --output text \
    --region "${REGION}")

  # Get training image
  TRAINING_IMAGE=$(aws sagemaker describe-training-job \
    --training-job-name "${training_job}" \
    --query 'AlgorithmSpecification.TrainingImage' \
    --output text \
    --region "${REGION}")

  echo "  Training Job: ${training_job}"
  echo "  Model Data:   ${MODEL_DATA}"

  # Create model
  aws sagemaker create-model \
    --model-name "${model_name}" \
    --primary-container "{
      \"Image\": \"${TRAINING_IMAGE}\",
      \"ModelDataUrl\": \"${MODEL_DATA}\"
    }" \
    --execution-role-arn "${ROLE_ARN}" \
    --region "${REGION}" \
    2>/dev/null || echo "  ℹ️  Model already exists"

  # Create endpoint configuration
  aws sagemaker create-endpoint-config \
    --endpoint-config-name "${model_name}-config" \
    --production-variants "[{
      \"VariantName\": \"AllTraffic\",
      \"ModelName\": \"${model_name}\",
      \"InitialInstanceCount\": 1,
      \"InstanceType\": \"ml.t2.medium\"
    }]" \
    --region "${REGION}" \
    2>/dev/null || echo "  ℹ️  Endpoint config already exists"

  # Create or update endpoint
  if aws sagemaker describe-endpoint --endpoint-name "${endpoint_name}" --region "${REGION}" 2>/dev/null; then
    echo "  → Updating existing endpoint..."
    aws sagemaker update-endpoint \
      --endpoint-name "${endpoint_name}" \
      --endpoint-config-name "${model_name}-config" \
      --region "${REGION}"
  else
    echo "  → Creating new endpoint..."
    aws sagemaker create-endpoint \
      --endpoint-name "${endpoint_name}" \
      --endpoint-config-name "${model_name}-config" \
      --region "${REGION}"
  fi

  echo "  ✓ Endpoint deployment started: ${endpoint_name}"
}

# Deploy Creative Scorer
echo "🔍 Finding latest Creative Scorer training job..."
CREATIVE_SCORER_JOB=$(find_latest_training_job "linkedin-ads-creative-scorer")

if [ "${CREATIVE_SCORER_JOB}" == "None" ] || [ -z "${CREATIVE_SCORER_JOB}" ]; then
  echo "❌ No completed Creative Scorer training job found!"
  echo "   Run ./train-models.sh first"
  CREATIVE_SCORER_DEPLOYED=false
else
  deploy_endpoint \
    "linkedin-ads-creative-scorer-model" \
    "${CREATIVE_SCORER_JOB}" \
    "linkedin-ads-creative-scorer"
  CREATIVE_SCORER_DEPLOYED=true
fi

echo ""

# Deploy Bid Optimizer
echo "🔍 Finding latest Bid Optimizer training job..."
BID_OPTIMIZER_JOB=$(find_latest_training_job "linkedin-ads-bid-optimizer")

if [ "${BID_OPTIMIZER_JOB}" == "None" ] || [ -z "${BID_OPTIMIZER_JOB}" ]; then
  echo "❌ No completed Bid Optimizer training job found!"
  echo "   Run ./train-models.sh first"
  BID_OPTIMIZER_DEPLOYED=false
else
  deploy_endpoint \
    "linkedin-ads-bid-optimizer-model" \
    "${BID_OPTIMIZER_JOB}" \
    "linkedin-ads-bid-optimizer"
  BID_OPTIMIZER_DEPLOYED=true
fi

echo ""

if [ "$CREATIVE_SCORER_DEPLOYED" = true ] || [ "$BID_OPTIMIZER_DEPLOYED" = true ]; then
  echo "=========================================="
  echo "✅ Endpoint Deployment Started!"
  echo "=========================================="
  echo ""
  echo "Endpoints will take 5-10 minutes to become InService."
  echo ""
  echo "Monitor status:"

  if [ "$CREATIVE_SCORER_DEPLOYED" = true ]; then
    echo "  aws sagemaker describe-endpoint --endpoint-name linkedin-ads-creative-scorer"
  fi

  if [ "$BID_OPTIMIZER_DEPLOYED" = true ]; then
    echo "  aws sagemaker describe-endpoint --endpoint-name linkedin-ads-bid-optimizer"
  fi

  echo ""
  echo "Or in AWS Console:"
  echo "  https://${REGION}.console.aws.amazon.com/sagemaker/home?region=${REGION}#/endpoints"
  echo ""
  echo "Next Steps (after endpoints are InService):"
  echo "1. Update Optimizer Lambda environment variables:"
  echo ""

  if [ "$CREATIVE_SCORER_DEPLOYED" = true ]; then
    echo "   CREATIVE_SCORER_ENDPOINT=linkedin-ads-creative-scorer"
  fi

  if [ "$BID_OPTIMIZER_DEPLOYED" = true ]; then
    echo "   BID_OPTIMIZER_ENDPOINT=linkedin-ads-bid-optimizer"
  fi

  echo ""
  echo "   Run: ./update-lambda-endpoints.sh"
  echo ""
else
  echo "=========================================="
  echo "⚠️  No Endpoints Deployed"
  echo "=========================================="
  echo ""
  echo "Train models first: ./train-models.sh"
  echo ""
fi

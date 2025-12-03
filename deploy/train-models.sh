#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - SageMaker Model Training Script
# Trains both Creative Scorer and Bid Optimizer models

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="linkedin-ads-data-${ACCOUNT_ID}"
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/LinkedInAdsSageMakerRole"

# SageMaker scikit-learn container image for us-east-2
SKLEARN_IMAGE="683313688378.dkr.ecr.us-east-2.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"

echo "=========================================="
echo "SageMaker Model Training"
echo "=========================================="
echo ""
echo "⚠️  NOTE: This script requires sufficient training data!"
echo "   Make sure data processor has run and created training datasets."
echo ""
read -p "Continue with training? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Training cancelled."
  exit 0
fi
echo ""

# Check if training data exists
echo "📊 Checking for training data..."

if ! aws s3 ls "s3://${BUCKET_NAME}/training_data/creative_scoring/" --region "${REGION}" 2>/dev/null | grep -q ".csv"; then
  echo "❌ No creative scoring training data found!"
  echo "   Run the data processor Lambda first to generate training data."
  exit 1
fi

if ! aws s3 ls "s3://${BUCKET_NAME}/training_data/bid_optimization/" --region "${REGION}" 2>/dev/null | grep -q ".csv"; then
  echo "❌ No bid optimization training data found!"
  echo "   Run the data processor Lambda first to generate training data."
  exit 1
fi

echo "✓ Training data found"
echo ""

# Train Creative Scorer
echo "🤖 Training Creative Scorer Model..."
echo ""

CREATIVE_SCORER_JOB="linkedin-ads-creative-scorer-$(date +%Y%m%d-%H%M%S)"

aws sagemaker create-training-job \
  --training-job-name "${CREATIVE_SCORER_JOB}" \
  --role-arn "${ROLE_ARN}" \
  --algorithm-specification "{
    \"TrainingImage\": \"${SKLEARN_IMAGE}\",
    \"TrainingInputMode\": \"File\"
  }" \
  --input-data-config "[
    {
      \"ChannelName\": \"training\",
      \"DataSource\": {
        \"S3DataSource\": {
          \"S3DataType\": \"S3Prefix\",
          \"S3Uri\": \"s3://${BUCKET_NAME}/training_data/creative_scoring/\",
          \"S3DataDistributionType\": \"FullyReplicated\"
        }
      },
      \"ContentType\": \"text/csv\"
    }
  ]" \
  --output-data-config "{
    \"S3OutputPath\": \"s3://${BUCKET_NAME}/models/creative_scorer/\"
  }" \
  --resource-config "{
    \"InstanceType\": \"ml.m5.xlarge\",
    \"InstanceCount\": 1,
    \"VolumeSizeInGB\": 10
  }" \
  --stopping-condition "{
    \"MaxRuntimeInSeconds\": 3600
  }" \
  --hyper-parameters "{
    \"n_estimators\": \"100\",
    \"max_depth\": \"10\",
    \"min_samples_split\": \"5\",
    \"min_samples_leaf\": \"2\",
    \"sagemaker_program\": \"train_creative_scorer.py\",
    \"sagemaker_submit_directory\": \"s3://${BUCKET_NAME}/code/sagemaker/sagemaker-code.tar.gz\"
  }" \
  --region "${REGION}"

echo "  Training Job: ${CREATIVE_SCORER_JOB}"
echo "  Status: IN PROGRESS"
echo ""

# Train Bid Optimizer
echo "🤖 Training Bid Optimizer Model..."
echo ""

BID_OPTIMIZER_JOB="linkedin-ads-bid-optimizer-$(date +%Y%m%d-%H%M%S)"

aws sagemaker create-training-job \
  --training-job-name "${BID_OPTIMIZER_JOB}" \
  --role-arn "${ROLE_ARN}" \
  --algorithm-specification "{
    \"TrainingImage\": \"${SKLEARN_IMAGE}\",
    \"TrainingInputMode\": \"File\"
  }" \
  --input-data-config "[
    {
      \"ChannelName\": \"training\",
      \"DataSource\": {
        \"S3DataSource\": {
          \"S3DataType\": \"S3Prefix\",
          \"S3Uri\": \"s3://${BUCKET_NAME}/training_data/bid_optimization/\",
          \"S3DataDistributionType\": \"FullyReplicated\"
        }
      },
      \"ContentType\": \"text/csv\"
    }
  ]" \
  --output-data-config "{
    \"S3OutputPath\": \"s3://${BUCKET_NAME}/models/bid_optimizer/\"
  }" \
  --resource-config "{
    \"InstanceType\": \"ml.m5.xlarge\",
    \"InstanceCount\": 1,
    \"VolumeSizeInGB\": 10
  }" \
  --stopping-condition "{
    \"MaxRuntimeInSeconds\": 3600
  }" \
  --hyper-parameters "{
    \"n_estimators\": \"200\",
    \"learning_rate\": \"0.1\",
    \"max_depth\": \"5\",
    \"min_samples_split\": \"10\",
    \"min_samples_leaf\": \"4\",
    \"subsample\": \"0.8\",
    \"sagemaker_program\": \"train_bid_optimizer.py\",
    \"sagemaker_submit_directory\": \"s3://${BUCKET_NAME}/code/sagemaker/sagemaker-code.tar.gz\"
  }" \
  --region "${REGION}"

echo "  Training Job: ${BID_OPTIMIZER_JOB}"
echo "  Status: IN PROGRESS"
echo ""

echo "=========================================="
echo "✅ Training Jobs Started!"
echo "=========================================="
echo ""
echo "Jobs:"
echo "  • Creative Scorer: ${CREATIVE_SCORER_JOB}"
echo "  • Bid Optimizer:   ${BID_OPTIMIZER_JOB}"
echo ""
echo "Monitor progress:"
echo "  aws sagemaker describe-training-job --training-job-name ${CREATIVE_SCORER_JOB}"
echo "  aws sagemaker describe-training-job --training-job-name ${BID_OPTIMIZER_JOB}"
echo ""
echo "Or in AWS Console:"
echo "  https://${REGION}.console.aws.amazon.com/sagemaker/home?region=${REGION}#/jobs"
echo ""
echo "Training typically takes 10-30 minutes per model."
echo ""

# Wait for training to complete and version the models
echo "⏳ Waiting for training jobs to complete..."
echo "(This may take 10-30 minutes - you can Ctrl+C and version models later)"
echo ""

wait_for_training() {
  local job_name=$1
  local timeout=3600  # 1 hour timeout

  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    STATUS=$(aws sagemaker describe-training-job \
      --training-job-name "${job_name}" \
      --region "${REGION}" \
      --query 'TrainingJobStatus' \
      --output text 2>/dev/null || echo "UNKNOWN")

    if [ "${STATUS}" == "Completed" ]; then
      echo "  ✓ ${job_name} completed"
      return 0
    elif [ "${STATUS}" == "Failed" ]; then
      echo "  ❌ ${job_name} failed"
      return 1
    elif [ "${STATUS}" == "Stopped" ]; then
      echo "  ⚠️  ${job_name} was stopped"
      return 1
    fi

    sleep 30
    elapsed=$((elapsed + 30))
  done

  echo "  ⏰ Timeout waiting for ${job_name}"
  return 1
}

version_model() {
  local job_name=$1
  local model_name=$2
  local model_type=$3

  echo "📦 Versioning ${model_name}..."

  # Get latest version number
  VERSIONS=$(aws s3 ls "s3://${BUCKET_NAME}/models/${model_name}/" | grep "v" | awk '{print $2}' | sed 's/v//g' | sed 's,/,,g' | sort -n | tail -1)

  if [ -z "${VERSIONS}" ]; then
    NEW_VERSION=1
  else
    NEW_VERSION=$((VERSIONS + 1))
  fi

  echo "  New version: v${NEW_VERSION}"

  # Get model artifacts location
  MODEL_DATA=$(aws sagemaker describe-training-job \
    --training-job-name "${job_name}" \
    --region "${REGION}" \
    --query 'ModelArtifacts.S3ModelArtifacts' \
    --output text)

  # Get training metrics
  METRICS=$(aws sagemaker describe-training-job \
    --training-job-name "${job_name}" \
    --region "${REGION}" \
    --query 'FinalMetricDataList' \
    --output json)

  # Copy model to versioned location
  aws s3 cp "${MODEL_DATA}" "s3://${BUCKET_NAME}/models/${model_name}/v${NEW_VERSION}/model.tar.gz" --region "${REGION}"

  # Create metadata file
  cat > /tmp/model_metadata.json <<EOF
{
  "version": ${NEW_VERSION},
  "model_type": "${model_type}",
  "training_job": "${job_name}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "model_artifacts": "${MODEL_DATA}",
  "metrics": ${METRICS},
  "status": "production"
}
EOF

  # Upload metadata
  aws s3 cp /tmp/model_metadata.json "s3://${BUCKET_NAME}/models/${model_name}/v${NEW_VERSION}/metadata.json" --region "${REGION}"

  # Update "latest" pointer
  echo "v${NEW_VERSION}" > /tmp/latest.txt
  aws s3 cp /tmp/latest.txt "s3://${BUCKET_NAME}/models/${model_name}/latest.txt" --region "${REGION}"

  # Also copy to "latest" folder for easy access
  aws s3 cp "${MODEL_DATA}" "s3://${BUCKET_NAME}/models/${model_name}/latest/model.tar.gz" --region "${REGION}"
  aws s3 cp /tmp/model_metadata.json "s3://${BUCKET_NAME}/models/${model_name}/latest/metadata.json" --region "${REGION}"

  # Cleanup
  rm /tmp/model_metadata.json /tmp/latest.txt

  echo "  ✓ Model versioned as v${NEW_VERSION}"
  echo "  ✓ Latest pointer updated"
}

# Try to wait and version (optional - user can Ctrl+C)
if wait_for_training "${CREATIVE_SCORER_JOB}"; then
  version_model "${CREATIVE_SCORER_JOB}" "creative_scorer" "RandomForestRegressor"
fi

if wait_for_training "${BID_OPTIMIZER_JOB}"; then
  version_model "${BID_OPTIMIZER_JOB}" "bid_optimizer" "GradientBoostingRegressor"
fi

echo ""
echo "=========================================="
echo "✅ Model Training and Versioning Complete!"
echo "=========================================="
echo ""
echo "Model versions saved to:"
echo "  s3://${BUCKET_NAME}/models/creative_scorer/vX/"
echo "  s3://${BUCKET_NAME}/models/bid_optimizer/vX/"
echo ""
echo "Latest versions accessible at:"
echo "  s3://${BUCKET_NAME}/models/creative_scorer/latest/"
echo "  s3://${BUCKET_NAME}/models/bid_optimizer/latest/"
echo ""
echo "Next Steps:"
echo "1. Deploy models to endpoints: ./deploy-endpoints.sh"
echo "2. Update Lambda environment variables with endpoint names"
echo ""

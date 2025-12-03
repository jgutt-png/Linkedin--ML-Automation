#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - Infrastructure Deployment Script
# This script deploys all AWS infrastructure for the ML optimization pipeline

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="linkedin-ads-data-${ACCOUNT_ID}"
ATHENA_BUCKET="linkedin-ads-athena-results-${ACCOUNT_ID}"
DEPLOYMENT_BUCKET="linkedin-ads-deployments-${ACCOUNT_ID}"

echo "=========================================="
echo "LinkedIn Ads ML Pipeline Deployment"
echo "=========================================="
echo "Region: ${REGION}"
echo "Account: ${ACCOUNT_ID}"
echo ""

# Step 1: Create IAM Roles
echo "📋 Step 1: Creating IAM Roles..."

# SageMaker Role
echo "  → Creating SageMaker IAM role..."
aws iam create-role \
  --role-name LinkedInAdsSageMakerRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sagemaker.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "  ℹ️  Role already exists"

aws iam attach-role-policy \
  --role-name LinkedInAdsSageMakerRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess 2>/dev/null || true

# Lambda Roles
echo "  → Creating Lambda IAM roles..."
for role in DataProcessor Optimizer CopyGenerator TokenRotator; do
  role_name="LinkedInAds${role}Role"
  echo "    - ${role_name}"

  aws iam create-role \
    --role-name "${role_name}" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }' 2>/dev/null || echo "      ℹ️  Role already exists"

  aws iam attach-role-policy \
    --role-name "${role_name}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true
done

# EventBridge Role
echo "  → Creating EventBridge IAM role..."
aws iam create-role \
  --role-name EventBridgeToLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "events.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' 2>/dev/null || echo "  ℹ️  Role already exists"

echo "✅ IAM Roles created"
echo ""

# Step 2: Create S3 Buckets (if not exist)
echo "📦 Step 2: Verifying S3 Buckets..."

for bucket in "${BUCKET_NAME}" "${ATHENA_BUCKET}" "${DEPLOYMENT_BUCKET}"; do
  if aws s3 ls "s3://${bucket}" 2>/dev/null; then
    echo "  ✓ ${bucket} exists"
  else
    echo "  → Creating ${bucket}..."
    aws s3 mb "s3://${bucket}" --region "${REGION}"
  fi
done

echo "✅ S3 Buckets ready"
echo ""

# Step 3: Create SNS Topic for Alerts
echo "📢 Step 3: Creating SNS Topic..."

SNS_TOPIC_ARN=$(aws sns create-topic \
  --name linkedin-ads-alerts \
  --region "${REGION}" \
  --query TopicArn \
  --output text 2>/dev/null || aws sns list-topics --query "Topics[?contains(TopicArn, 'linkedin-ads-alerts')].TopicArn" --output text)

echo "  SNS Topic: ${SNS_TOPIC_ARN}"
echo "✅ SNS Topic ready"
echo ""

# Step 4: Upload SageMaker Code to S3
echo "🤖 Step 4: Uploading SageMaker Training Scripts..."

# Create code archive
cd ../sagemaker
tar czf sagemaker-code.tar.gz *.py requirements.txt
aws s3 cp sagemaker-code.tar.gz "s3://${BUCKET_NAME}/code/sagemaker/sagemaker-code.tar.gz"
rm sagemaker-code.tar.gz
cd ../deploy

echo "✅ SageMaker code uploaded"
echo ""

# Step 5: Package and Upload Lambda Functions
echo "⚡ Step 5: Packaging Lambda Functions..."

package_lambda() {
  local lambda_name=$1
  local lambda_dir="../lambda/${lambda_name}"

  echo "  → Packaging ${lambda_name}..."

  cd "${lambda_dir}"

  # Install dependencies
  if [ -f requirements.txt ]; then
    pip install -r requirements.txt -t package/ --quiet
    cd package
    zip -r "../${lambda_name}.zip" . --quiet
    cd ..
  fi

  # Add handler
  zip -g "${lambda_name}.zip" handler.py --quiet

  # Upload to S3
  aws s3 cp "${lambda_name}.zip" "s3://${DEPLOYMENT_BUCKET}/lambda/${lambda_name}.zip"

  # Cleanup
  rm -rf package "${lambda_name}.zip"

  cd ../../deploy
}

package_lambda "data_processor"
package_lambda "optimizer"
package_lambda "copy_generator"
package_lambda "token_rotator"

echo "✅ Lambda functions packaged and uploaded"
echo ""

# Step 6: Create CloudWatch Alarms
echo "🔔 Step 6: Creating CloudWatch Alarms..."

create_lambda_alarm() {
  local function_name=$1
  local alarm_name=$2
  local description=$3

  echo "  → Creating alarm for ${function_name}..."

  # Error alarm
  aws cloudwatch put-metric-alarm \
    --alarm-name "${alarm_name}-errors" \
    --alarm-description "${description} - Error rate alarm" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value="${function_name}" \
    --alarm-actions "${SNS_TOPIC_ARN}" \
    --region "${REGION}" \
    2>/dev/null || echo "    ℹ️  Alarm already exists"

  # Duration alarm (timeout warning at 80% of limit)
  aws cloudwatch put-metric-alarm \
    --alarm-name "${alarm_name}-duration" \
    --alarm-description "${description} - Duration alarm" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 240000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value="${function_name}" \
    --alarm-actions "${SNS_TOPIC_ARN}" \
    --region "${REGION}" \
    2>/dev/null || echo "    ℹ️  Alarm already exists"
}

# Create alarms for each Lambda (only if SNS topic exists)
if [ -n "${SNS_TOPIC_ARN}" ]; then
  create_lambda_alarm \
    "linkedin-ads-data-processor" \
    "linkedin-ml-data-processor" \
    "Data Processor Lambda"

  create_lambda_alarm \
    "linkedin-ads-optimizer" \
    "linkedin-ml-optimizer" \
    "Optimizer Lambda"

  create_lambda_alarm \
    "linkedin-ads-copy-generator" \
    "linkedin-ml-copy-generator" \
    "Copy Generator Lambda"

  create_lambda_alarm \
    "linkedin-ads-token-rotator" \
    "linkedin-ml-token-rotator" \
    "Token Rotator Lambda"

  echo "  ✓ CloudWatch alarms created"
else
  echo "  ⚠️  Skipping alarms (SNS topic not found)"
fi

echo "✅ CloudWatch alarms configured"
echo ""

# Step 7: Wait for IAM roles to propagate
echo "⏳ Step 7: Waiting for IAM roles to propagate..."
sleep 10
echo ""

echo "=========================================="
echo "✅ Infrastructure Deployment Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Deploy Lambda functions: ./deploy-lambdas.sh"
echo "2. Create EventBridge schedules: ./deploy-schedules.sh"
echo "3. Once you have data, train models: ./train-models.sh"
echo ""
echo "Configuration:"
echo "  Region:             ${REGION}"
echo "  Data Bucket:        ${BUCKET_NAME}"
echo "  Athena Bucket:      ${ATHENA_BUCKET}"
echo "  Deployment Bucket:  ${DEPLOYMENT_BUCKET}"
echo "  SNS Topic:          ${SNS_TOPIC_ARN}"
echo ""

#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - Token Rotation Setup Script
# Configures AWS Secrets Manager to automatically rotate LinkedIn OAuth token

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
SECRET_NAME="linkedin-access-token"
LAMBDA_FUNCTION="linkedin-ads-token-rotator"
ROTATION_DAYS=55  # Rotate every 55 days (LinkedIn tokens expire after 60)

echo "=========================================="
echo "Token Rotation Configuration"
echo "=========================================="
echo ""

# Get Lambda ARN
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${LAMBDA_FUNCTION}"

echo "📋 Configuration:"
echo "  Secret: ${SECRET_NAME}"
echo "  Lambda: ${LAMBDA_FUNCTION}"
echo "  Rotation: Every ${ROTATION_DAYS} days"
echo ""

# Check if secret exists
echo "🔍 Checking if secret exists..."
if ! aws secretsmanager describe-secret --secret-id "${SECRET_NAME}" --region "${REGION}" 2>/dev/null; then
  echo ""
  echo "❌ Secret '${SECRET_NAME}' does not exist!"
  echo ""
  echo "Please create the secret first with this structure:"
  echo "{"
  echo '  "access_token": "YOUR_LINKEDIN_ACCESS_TOKEN",'
  echo '  "refresh_token": "YOUR_LINKEDIN_REFRESH_TOKEN",'
  echo '  "client_id": "YOUR_LINKEDIN_CLIENT_ID",'
  echo '  "client_secret": "YOUR_LINKEDIN_CLIENT_SECRET"'
  echo "}"
  echo ""
  echo "Create it with:"
  echo "  aws secretsmanager create-secret \\"
  echo "    --name ${SECRET_NAME} \\"
  echo "    --secret-string '{...}' \\"
  echo "    --region ${REGION}"
  echo ""
  exit 1
fi

echo "  ✓ Secret exists"
echo ""

# Check if Lambda exists
echo "🔍 Checking if Lambda function exists..."
if ! aws lambda get-function --function-name "${LAMBDA_FUNCTION}" --region "${REGION}" 2>/dev/null; then
  echo ""
  echo "❌ Lambda function '${LAMBDA_FUNCTION}' does not exist!"
  echo ""
  echo "Deploy Lambdas first with:"
  echo "  ./deploy-lambdas.sh"
  echo ""
  exit 1
fi

echo "  ✓ Lambda exists"
echo ""

# Grant Lambda permission to access the secret
echo "🔐 Granting Lambda permission to rotate secret..."

aws lambda add-permission \
  --function-name "${LAMBDA_FUNCTION}" \
  --statement-id "SecretsManagerRotation" \
  --action "lambda:InvokeFunction" \
  --principal "secretsmanager.amazonaws.com" \
  --region "${REGION}" \
  2>/dev/null || echo "  ℹ️  Permission already exists"

echo "  ✓ Permission granted"
echo ""

# Configure rotation
echo "🔄 Configuring automatic rotation..."

aws secretsmanager rotate-secret \
  --secret-id "${SECRET_NAME}" \
  --rotation-lambda-arn "${LAMBDA_ARN}" \
  --rotation-rules "{\"AutomaticallyAfterDays\": ${ROTATION_DAYS}}" \
  --region "${REGION}" \
  2>/dev/null || aws secretsmanager update-secret-version-stage \
    --secret-id "${SECRET_NAME}" \
    --version-stage "AWSCURRENT" \
    --region "${REGION}"

echo "  ✓ Rotation configured"
echo ""

# Test rotation (optional)
echo "🧪 Testing rotation..."
read -p "Do you want to test rotation now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo ""
  echo "⏳ Starting test rotation..."
  echo "   (This will refresh your LinkedIn token)"
  echo ""

  ROTATION_ID=$(aws secretsmanager rotate-secret \
    --secret-id "${SECRET_NAME}" \
    --region "${REGION}" \
    --query 'VersionId' \
    --output text)

  echo "  Rotation initiated: ${ROTATION_ID}"
  echo ""
  echo "  Monitor progress:"
  echo "    aws secretsmanager describe-secret --secret-id ${SECRET_NAME}"
  echo ""
  echo "  View Lambda logs:"
  echo "    aws logs tail /aws/lambda/${LAMBDA_FUNCTION} --follow"
  echo ""
else
  echo ""
  echo "  ⏭️  Skipping test rotation"
  echo ""
fi

echo "=========================================="
echo "✅ Token Rotation Configured!"
echo "=========================================="
echo ""
echo "Your LinkedIn OAuth token will automatically rotate every ${ROTATION_DAYS} days."
echo ""
echo "Monitor rotations:"
echo "  • CloudWatch Logs: /aws/lambda/${LAMBDA_FUNCTION}"
echo "  • SNS notifications to: linkedin-ads-alerts topic"
echo ""
echo "View rotation history:"
echo "  aws secretsmanager list-secret-version-ids --secret-id ${SECRET_NAME}"
echo ""
echo "Manually trigger rotation:"
echo "  aws secretsmanager rotate-secret --secret-id ${SECRET_NAME}"
echo ""

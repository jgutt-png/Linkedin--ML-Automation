#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - EventBridge Schedules Deployment
# Creates scheduled triggers for automated pipeline execution

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=========================================="
echo "Creating EventBridge Schedules"
echo "=========================================="
echo ""

# Create EventBridge rule for Data Processor (Daily at 6 AM UTC)
echo "⏰ Creating Data Processor schedule..."

aws events put-rule \
  --name linkedin-ads-data-processor-daily \
  --description "Trigger data processor Lambda daily to prepare ML training data" \
  --schedule-expression "cron(0 6 * * ? *)" \
  --state ENABLED \
  --region "${REGION}" \
  > /dev/null

aws lambda add-permission \
  --function-name linkedin-ads-data-processor \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/linkedin-ads-data-processor-daily" \
  --region "${REGION}" \
  2>/dev/null || echo "  ℹ️  Permission already exists"

aws events put-targets \
  --rule linkedin-ads-data-processor-daily \
  --targets "Id=1,Arn=arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:linkedin-ads-data-processor" \
  --region "${REGION}" \
  > /dev/null

echo "  ✓ Data Processor: Daily at 6 AM UTC"
echo ""

# Create EventBridge rule for Optimizer (Daily at 8 AM UTC)
echo "⏰ Creating Optimizer schedule..."

aws events put-rule \
  --name linkedin-ads-optimizer-daily \
  --description "Trigger optimizer Lambda daily for automated campaign optimization" \
  --schedule-expression "cron(0 8 * * ? *)" \
  --state ENABLED \
  --region "${REGION}" \
  > /dev/null

aws lambda add-permission \
  --function-name linkedin-ads-optimizer \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/linkedin-ads-optimizer-daily" \
  --region "${REGION}" \
  2>/dev/null || echo "  ℹ️  Permission already exists"

aws events put-targets \
  --rule linkedin-ads-optimizer-daily \
  --targets "Id=1,Arn=arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:linkedin-ads-optimizer" \
  --region "${REGION}" \
  > /dev/null

echo "  ✓ Optimizer: Daily at 8 AM UTC"
echo ""

# Create EventBridge rule for Copy Generator (Weekly on Monday at 9 AM UTC)
echo "⏰ Creating Copy Generator schedule..."

aws events put-rule \
  --name linkedin-ads-copy-generator-weekly \
  --description "Trigger copy generator Lambda weekly to create new ad variations" \
  --schedule-expression "cron(0 9 ? * MON *)" \
  --state ENABLED \
  --region "${REGION}" \
  > /dev/null

aws lambda add-permission \
  --function-name linkedin-ads-copy-generator \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${REGION}:${ACCOUNT_ID}:rule/linkedin-ads-copy-generator-weekly" \
  --region "${REGION}" \
  2>/dev/null || echo "  ℹ️  Permission already exists"

# Configure with input parameters
aws events put-targets \
  --rule linkedin-ads-copy-generator-weekly \
  --targets "Id=1,Arn=arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:linkedin-ads-copy-generator,Input={\"product_info\":\"YOUR_PRODUCT_DESCRIPTION that helps investors find off-market deals and distressed properties\",\"target_audience\":\"YOUR_TARGET_AUDIENCE (e.g., professionals in your target industry)\",\"num_variations\":5}" \
  --region "${REGION}" \
  > /dev/null

echo "  ✓ Copy Generator: Weekly on Mondays at 9 AM UTC"
echo ""

echo "=========================================="
echo "✅ All Schedules Created!"
echo "=========================================="
echo ""
echo "Active Schedules:"
echo "  • Data Processor:   Daily at 6 AM UTC"
echo "  • Optimizer:        Daily at 8 AM UTC"
echo "  • Copy Generator:   Weekly (Mon) at 9 AM UTC"
echo ""
echo "Pipeline Execution Flow:"
echo "  1. 6 AM UTC: Data processor prepares training data"
echo "  2. 8 AM UTC: Optimizer analyzes and optimizes campaigns"
echo "  3. Weekly:   Copy generator creates new variations"
echo ""
echo "To manually trigger:"
echo "  aws lambda invoke --function-name linkedin-ads-data-processor response.json"
echo "  aws lambda invoke --function-name linkedin-ads-optimizer response.json"
echo "  aws lambda invoke --function-name linkedin-ads-copy-generator response.json"
echo ""

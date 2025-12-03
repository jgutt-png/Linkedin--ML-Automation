# LinkedIn Ads ML Pipeline - Deployment Guide

Complete deployment documentation for the automated LinkedIn Ads optimization system.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Deployment](#detailed-deployment)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Model Training & Deployment](#model-training--deployment)
7. [Testing & Verification](#testing--verification)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This deployment creates a fully automated LinkedIn Ads optimization pipeline with:

- **Data Collection**: Already deployed (Phase 1 from original setup)
- **ML Training Infrastructure**: SageMaker for model training
- **Automated Optimization**: Daily Lambda execution for campaign optimization
- **AI Copy Generation**: Weekly Claude API-powered ad copy creation

### System Architecture

```
LinkedIn Ads API
      ↓
[Data Collection Lambda] → S3 Raw Data
      ↓
[Glue Crawler] → Athena Tables
      ↓
[Data Processor Lambda] → Training Data (S3)
      ↓
[SageMaker Training Jobs] → Trained Models
      ↓
[SageMaker Endpoints] → Real-time Predictions
      ↓
[Optimizer Lambda] → Campaign Actions (pause/scale/adjust)
      ↓
[Copy Generator Lambda] → New Ad Variations
```

---

## ✅ Prerequisites

### AWS Configuration

```bash
# Verify AWS CLI is configured
aws sts get-caller-identity

# Set region (if not already set)
export AWS_REGION=us-east-2
```

### Required AWS Permissions

Your IAM user/role needs permissions for:
- IAM (role creation)
- Lambda (function deployment)
- S3 (bucket operations)
- SageMaker (training jobs, endpoints)
- EventBridge (schedule creation)
- Secrets Manager (secret storage)
- SNS (topic creation)
- Athena & Glue (already configured)

### LinkedIn & Anthropic API Access

- **LinkedIn Ads API**: Access token from developer portal
- **Anthropic API**: API key for Claude (get from console.anthropic.com)

---

## 🚀 Quick Start

### One-Command Deployment

Deploy everything at once:

```bash
cd deploy
chmod +x *.sh
./deploy-all.sh
```

This will:
1. Create all IAM roles
2. Deploy Lambda functions
3. Set up EventBridge schedules
4. Upload SageMaker training code

**Time**: ~5 minutes

---

## 📦 Detailed Deployment

### Phase 1: Infrastructure

Creates IAM roles, S3 buckets, SNS topics:

```bash
./deploy-infrastructure.sh
```

**What it creates:**
- IAM roles:
  - `LinkedInAdsSageMakerRole`
  - `LinkedInAdsDataProcessorRole`
  - `LinkedInAdsOptimizerRole`
  - `LinkedInAdsCopyGeneratorRole`
  - `EventBridgeToLambdaRole`
- S3 buckets (if needed):
  - `linkedin-ads-data-{account-id}`
  - `linkedin-ads-athena-results-{account-id}`
  - `linkedin-ads-deployments-{account-id}`
- SNS topic: `linkedin-ads-alerts`

### Phase 2: Lambda Functions

Packages and deploys all Lambda functions:

```bash
./deploy-lambdas.sh
```

**Functions deployed:**
1. **linkedin-ads-data-processor**
   - Prepares ML training data
   - Runs: Daily at 6 AM UTC
   - Memory: 1024 MB
   - Timeout: 5 minutes

2. **linkedin-ads-optimizer**
   - Main decision engine
   - Runs: Daily at 8 AM UTC
   - Memory: 2048 MB
   - Timeout: 10 minutes

3. **linkedin-ads-copy-generator**
   - AI ad copy generation
   - Runs: Weekly (Mondays) at 9 AM UTC
   - Memory: 512 MB
   - Timeout: 5 minutes

### Phase 3: EventBridge Schedules

Creates automated triggers:

```bash
./deploy-schedules.sh
```

**Schedules created:**
- `linkedin-ads-data-processor-daily` - cron(0 6 * * ? *)
- `linkedin-ads-optimizer-daily` - cron(0 8 * * ? *)
- `linkedin-ads-copy-generator-weekly` - cron(0 9 ? * MON *)

---

## 🔐 Post-Deployment Configuration

### Store API Secrets

**LinkedIn Access Token:**
```bash
aws secretsmanager create-secret \
  --name linkedin-access-token \
  --secret-string '{"access_token":"YOUR_LINKEDIN_ACCESS_TOKEN"}'
```

**Anthropic API Key:**
```bash
aws secretsmanager create-secret \
  --name anthropic-api-key \
  --secret-string '{"api_key":"YOUR_ANTHROPIC_API_KEY"}'
```

### Subscribe to SNS Alerts

Get daily optimization reports:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-2:${ACCOUNT_ID}:linkedin-ads-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

Confirm the subscription via email.

---

## 🤖 Model Training & Deployment

### When to Train Models

Train models after **30+ days** of data collection for meaningful patterns.

### Step 1: Train Models

Initiates SageMaker training jobs:

```bash
./train-models.sh
```

This will:
1. Check for training data in S3
2. Start Creative Scorer training (10-30 min)
3. Start Bid Optimizer training (10-30 min)

**Monitor progress:**
```bash
# Check training status
aws sagemaker list-training-jobs --max-results 5

# Or view in console
# https://us-east-2.console.aws.amazon.com/sagemaker/home?region=us-east-2#/jobs
```

### Step 2: Deploy Endpoints

Once training completes (status: `Completed`):

```bash
./deploy-endpoints.sh
```

This creates real-time inference endpoints:
- `linkedin-ads-creative-scorer`
- `linkedin-ads-bid-optimizer`

**Deployment time**: 5-10 minutes per endpoint

### Step 3: Update Lambda Configuration

Connect Optimizer Lambda to model endpoints:

```bash
./update-lambda-endpoints.sh
```

This updates environment variables:
- `CREATIVE_SCORER_ENDPOINT=linkedin-ads-creative-scorer`
- `BID_OPTIMIZER_ENDPOINT=linkedin-ads-bid-optimizer`

**The optimizer will now use ML predictions instead of heuristics!**

---

## 🧪 Testing & Verification

### Test Individual Components

**Data Processor:**
```bash
aws lambda invoke \
  --function-name linkedin-ads-data-processor \
  --log-type Tail \
  output.json

cat output.json | jq
```

**Optimizer:**
```bash
aws lambda invoke \
  --function-name linkedin-ads-optimizer \
  --log-type Tail \
  output.json

cat output.json | jq
```

**Copy Generator:**
```bash
aws lambda invoke \
  --function-name linkedin-ads-copy-generator \
  --log-type Tail \
  output.json

cat output.json | jq
```

### View CloudWatch Logs

```bash
# Data Processor logs
aws logs tail /aws/lambda/linkedin-ads-data-processor --follow

# Optimizer logs
aws logs tail /aws/lambda/linkedin-ads-optimizer --follow

# Copy Generator logs
aws logs tail /aws/lambda/linkedin-ads-copy-generator --follow
```

### Check S3 Outputs

**Training data:**
```bash
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/training_data/ --recursive
```

**Generated copy:**
```bash
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/generated_copy/
aws s3 cp s3://linkedin-ads-data-${ACCOUNT_ID}/generated_copy/latest.json - | jq
```

**Optimization logs:**
```bash
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/optimization_logs/
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Lambda Permission Errors

**Symptom:** "Unable to assume role" or "Access Denied"

**Solution:** Wait 10-30 seconds for IAM role propagation, then retry.

#### 2. No Training Data Found

**Symptom:** Training script reports no data files

**Solution:**
1. Check data collection is running: `aws lambda get-function --function-name linkedin-ads-data-collector`
2. Manually invoke data processor: `aws lambda invoke --function-name linkedin-ads-data-processor out.json`
3. Verify Athena has data: Query `linkedin_ads.creative_performance` table

#### 3. Endpoint Creation Fails

**Symptom:** "No completed training job found"

**Solution:**
1. Check training job status: `aws sagemaker list-training-jobs`
2. If failed, check logs: `aws sagemaker describe-training-job --training-job-name JOB_NAME`
3. Common causes:
   - Insufficient training data (need 100+ samples)
   - Missing/corrupt data files
   - Incorrect S3 paths

#### 4. Optimizer Not Pausing Creatives

**Symptom:** Low-performing ads still running

**Possible causes:**
1. Not enough sample size (default: 100 clicks minimum)
2. LinkedIn API token expired
3. Environment variables not set

**Check:**
```bash
aws lambda get-function-configuration \
  --function-name linkedin-ads-optimizer \
  --query 'Environment.Variables'
```

#### 5. Copy Generator Returns Empty Variations

**Symptom:** No ad copy generated

**Solutions:**
1. Check Anthropic API key: `aws secretsmanager get-secret-value --secret-id anthropic-api-key`
2. Verify API key is valid at console.anthropic.com
3. Check CloudWatch logs for API errors

### View All Resources

```bash
# List Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `linkedin-ads`)].FunctionName'

# List SageMaker endpoints
aws sagemaker list-endpoints --name-contains linkedin-ads

# List EventBridge rules
aws events list-rules --name-prefix linkedin-ads

# List S3 buckets
aws s3 ls | grep linkedin-ads
```

---

## 📊 Monitoring & Maintenance

### Daily Checks

Monitor SNS email reports for:
- Paused creatives count
- Bid adjustments made
- Top performers identified

### Weekly Reviews

1. **Check generated copy**: Review new variations in S3
2. **Model performance**: Monitor prediction accuracy in CloudWatch metrics
3. **Cost analysis**: Review SageMaker endpoint costs

### Monthly Maintenance

1. **Retrain models**: As data grows, retrain for better predictions
2. **Tune thresholds**: Adjust MIN_CTR_THRESHOLD, MAX_CPC based on results
3. **Review automation actions**: Analyze optimization_logs for patterns

---

## 💰 Cost Estimates

### Lambda (Light Usage)
- 3 functions × 30 invocations/month = ~$0.50/month

### SageMaker Training (Monthly)
- 2 models × ml.m5.xlarge × 30 min = ~$2/month

### SageMaker Endpoints (24/7)
- 2 endpoints × ml.t2.medium = ~$60/month

### S3 & Data Transfer
- ~$5/month

**Total**: ~$70/month (excluding existing Phase 1 costs)

**Cost Optimization:**
- Use endpoints only during business hours
- Use spot instances for training
- Delete old training artifacts

---

## 📚 Additional Resources

### AWS Documentation
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [SageMaker Training](https://docs.aws.amazon.com/sagemaker/latest/dg/how-it-works-training.html)
- [EventBridge Schedules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)

### LinkedIn Ads API
- [API Documentation](https://learn.microsoft.com/en-us/linkedin/marketing/)
- [Rate Limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)

### Anthropic Claude API
- [API Reference](https://docs.anthropic.com/claude/reference/)
- [Prompt Engineering](https://docs.anthropic.com/claude/docs/intro-to-prompting)

---

## 🆘 Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review this troubleshooting guide
3. Verify all secrets are correctly stored in Secrets Manager
4. Ensure sufficient training data exists (30+ days recommended)

---

**Last Updated**: December 2025
**Version**: 1.0.0

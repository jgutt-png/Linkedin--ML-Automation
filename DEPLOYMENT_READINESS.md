# Deployment Readiness Checklist

## ✅ All Features Complete

All requested features have been implemented and integrated into the deployment pipeline:

### 1. ✅ Token Rotation
- **Lambda**: `lambda/token_rotator/handler.py` (320 lines)
- **IAM Role**: `LinkedInAdsTokenRotatorRole` with Secrets Manager permissions
- **Setup Script**: `deploy/setup-token-rotation.sh`
- **Integration**: Added to `deploy-infrastructure.sh` and `deploy-lambdas.sh`
- **CloudWatch Alarms**: Configured for error and duration monitoring
- **SNS Notifications**: Success/failure alerts

### 2. ✅ CloudWatch Metrics
- **Optimizer Lambda**: Added `send_cloudwatch_metrics()` function
- **Data Processor Lambda**: Added `send_cloudwatch_metrics()` function
- **Namespaces**:
  - `LinkedInAds/Optimizer` - 15+ optimization metrics
  - `LinkedInAds/Campaigns` - Campaign-specific metrics with dimensions
  - `LinkedInAds/DataProcessor` - Dataset and aggregate creation metrics
- **IAM Permissions**: CloudWatch PutMetricData added to both roles

### 3. ✅ Model Versioning
- **Training Script**: `deploy/train-models.sh` updated
- **Features**:
  - Auto-increment versions (v1, v2, v3...)
  - Metadata tracking (training job, metrics, timestamps)
  - Latest pointer (`latest.txt` and `latest/` folder)
  - Rollback support
- **S3 Structure**: Organized versioned folders with metadata.json

### 4. ✅ Processed Aggregates
- **Data Processor Lambda**: Added 3 aggregate functions
  - `create_daily_aggregates()` - Last 90 days
  - `create_weekly_summaries()` - Last 180 days
  - `create_creative_metadata()` - All-time stats
- **Formats**: JSON (for lookups) + Parquet (for queries)
- **Amplify-Ready**: Optimized for frontend consumption
- **Performance Categories**: Auto-categorizes creatives (high/medium/low/very_low)

---

## 📂 Files Modified/Created

### New Files Created
```
lambda/token_rotator/handler.py          (320 lines) - OAuth rotation logic
lambda/token_rotator/requirements.txt    (2 lines)   - Dependencies
deploy/setup-token-rotation.sh           (109 lines) - Rotation config script
NEW_FEATURES.md                          (600+ lines) - Comprehensive documentation
DEPLOYMENT_READINESS.md                  (this file)  - Deployment checklist
```

### Files Modified
```
lambda/data_processor/handler.py         - Added 3 aggregate functions + CloudWatch metrics
lambda/optimizer/handler.py              - Added CloudWatch metrics (from previous work)
deploy/deploy-infrastructure.sh          - Added token_rotator packaging + IAM + alarms
deploy/deploy-lambdas.sh                 - Added token_rotator deployment
deploy/train-models.sh                   - Added model versioning functions
infrastructure/lambda-iam-roles.json     - Added TokenRotatorRole + CloudWatch permissions
```

---

## 🚀 Deployment Order

All scripts are ready. Follow this order:

### Step 1: Infrastructure Setup
```bash
cd /Users/default/linkedin-automation/deploy
./deploy-infrastructure.sh
```
**What it does**:
- Creates IAM roles (including TokenRotatorRole)
- Creates S3 buckets
- Creates SNS topic for alerts
- Packages ALL Lambda functions (including token_rotator)
- Uploads SageMaker code
- Creates CloudWatch alarms

**Expected output**: 4 Lambda packages uploaded, all IAM roles created

---

### Step 2: Setup Athena Database
```bash
./setup-athena.sh
```
**What it does**:
- Creates `linkedin_ads` database
- Creates `creative_performance` table
- Sets up partitioning by date

**Expected output**: Database and table created successfully

---

### Step 3: Deploy Lambda Functions
```bash
./deploy-lambdas.sh
```
**What it does**:
- Deploys 4 Lambda functions:
  - linkedin-ads-data-processor (with aggregates + metrics)
  - linkedin-ads-optimizer (with metrics)
  - linkedin-ads-copy-generator
  - linkedin-ads-token-rotator
- Sets environment variables
- Configures function settings

**Expected output**: All 4 functions deployed

---

### Step 4: Store Secrets
```bash
# Create LinkedIn OAuth secret
aws secretsmanager create-secret \
  --name linkedin-access-token \
  --secret-string '{
    "access_token": "YOUR_LINKEDIN_ACCESS_TOKEN",
    "refresh_token": "YOUR_LINKEDIN_REFRESH_TOKEN",
    "client_id": "YOUR_LINKEDIN_CLIENT_ID",
    "client_secret": "YOUR_LINKEDIN_CLIENT_SECRET"
  }'

# Create Anthropic API key secret
aws secretsmanager create-secret \
  --name anthropic-api-key \
  --secret-string '{"api_key": "YOUR_ANTHROPIC_API_KEY"}'
```

---

### Step 5: Configure Token Rotation
```bash
./setup-token-rotation.sh
```
**What it does**:
- Grants Lambda permission to rotate secret
- Configures rotation schedule (every 55 days)
- Optionally tests rotation

**Expected output**: Rotation configured, test successful (if run)

---

### Step 6: Create EventBridge Schedules
```bash
./deploy-schedules.sh
```
**What it does**:
- Creates schedule for data processor (daily)
- Creates schedule for optimizer (daily)
- Creates schedule for copy generator (weekly)

**Expected output**: 3 schedules created

---

### Step 7: Wait for Data Collection
**Timeline**: 7-14 days minimum

Monitor data collection:
```bash
# Check S3 for raw data
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/raw/analytics/

# View collector logs
aws logs tail /aws/lambda/linkedin-ads-collector --follow
```

**You need**: At least 7 days of data before training models

---

### Step 8: Train ML Models (After Data Collection)
```bash
./train-models.sh
```
**What it does**:
- Checks for training data
- Trains creative scorer model
- Trains bid optimizer model
- Automatically versions models (v1/, v2/, etc.)
- Creates metadata.json for each version
- Updates "latest" pointers

**Expected output**:
- 2 training jobs started
- Auto-versioned as v1
- Models saved to S3

**Timeline**: 10-30 minutes per model

---

### Step 9: Deploy SageMaker Endpoints (After Training)
```bash
./deploy-endpoints.sh
```
**What it does**:
- Creates SageMaker endpoints for both models
- Uses latest model versions
- Configures real-time inference

**Expected output**: 2 endpoints created and InService

---

### Step 10: Update Lambda Environment Variables
```bash
# Get endpoint names
CREATIVE_SCORER=$(aws sagemaker list-endpoints --query "Endpoints[?contains(EndpointName, 'creative-scorer')].EndpointName" --output text)
BID_OPTIMIZER=$(aws sagemaker list-endpoints --query "Endpoints[?contains(EndpointName, 'bid-optimizer')].EndpointName" --output text)

# Update optimizer Lambda
aws lambda update-function-configuration \
  --function-name linkedin-ads-optimizer \
  --environment "Variables={
    BUCKET_NAME=linkedin-ads-data-${ACCOUNT_ID},
    ATHENA_OUTPUT_BUCKET=linkedin-ads-athena-results-${ACCOUNT_ID},
    ATHENA_DATABASE=linkedin_ads,
    LINKEDIN_ACCESS_TOKEN_SECRET=linkedin-access-token,
    SNS_TOPIC_ARN=${SNS_TOPIC_ARN},
    MIN_CTR_THRESHOLD=1.0,
    TOP_PERFORMER_THRESHOLD=3.0,
    MAX_CPC=8.0,
    MIN_SAMPLE_SIZE=100,
    BID_CHANGE_THRESHOLD=0.50,
    CREATIVE_SCORER_ENDPOINT=${CREATIVE_SCORER},
    BID_OPTIMIZER_ENDPOINT=${BID_OPTIMIZER}
  }"
```

---

## 🧪 Testing Each Component

### Test Token Rotation
```bash
# Trigger manual rotation
aws secretsmanager rotate-secret --secret-id linkedin-access-token

# Watch logs
aws logs tail /aws/lambda/linkedin-ads-token-rotator --follow
```

**Expected**: 4 rotation steps complete successfully (createSecret → setSecret → testSecret → finishSecret)

---

### Test Data Processor
```bash
# Invoke manually
aws lambda invoke \
  --function-name linkedin-ads-data-processor \
  response.json

cat response.json

# Check aggregates created
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/processed/aggregates/
```

**Expected**:
- 2 training datasets created (if data exists)
- 3 aggregates created
- CloudWatch metrics sent

---

### Test Optimizer
```bash
# Invoke manually
aws lambda invoke \
  --function-name linkedin-ads-optimizer \
  response.json

cat response.json
```

**Expected**:
- Optimization actions logged
- CloudWatch metrics sent
- SNS notification (if actions taken)

---

### Test Copy Generator
```bash
# Invoke manually
aws lambda invoke \
  --function-name linkedin-ads-copy-generator \
  response.json

cat response.json
```

**Expected**: New ad copy variations generated

---

## 📊 Monitoring Setup

### CloudWatch Dashboards

Create a custom dashboard:

1. Go to CloudWatch → Dashboards → Create Dashboard
2. Add widgets for:
   - **Optimizer Metrics** (Namespace: LinkedInAds/Optimizer)
     - Line: AverageCTR, AverageCPC over time
     - Number: TotalActions, CreativesPaused today
     - Bar: Top campaigns by conversions
   - **Data Processor Metrics** (Namespace: LinkedInAds/DataProcessor)
     - Number: DatasetsCreated, AggregatesCreated
     - Line: TotalTrainingSamples over time
   - **Lambda Health**
     - Errors, Duration, Invocations for all functions

### SNS Email Subscriptions

```bash
SNS_TOPIC=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'linkedin-ads-alerts')].TopicArn" --output text)

aws sns subscribe \
  --topic-arn ${SNS_TOPIC} \
  --protocol email \
  --notification-endpoint your-email@example.com
```

---

## 🎯 Success Criteria

Before considering deployment complete, verify:

- [ ] All 4 Lambda functions deployed successfully
- [ ] IAM roles have correct permissions
- [ ] Token rotation configured and tested
- [ ] EventBridge schedules created
- [ ] At least 7 days of data collected
- [ ] Training datasets created by data processor
- [ ] ML models trained and versioned
- [ ] SageMaker endpoints deployed and InService
- [ ] CloudWatch metrics appearing in console
- [ ] SNS email subscription confirmed
- [ ] Aggregates created in S3
- [ ] CloudWatch alarms configured

---

## 💰 Cost Estimate

### Phase 1 (Data Collection - Active Now)
- **Lambda**: ~$5/month (daily runs)
- **S3**: ~$2/month (raw data storage)
- **Secrets Manager**: $0.40/month (LinkedIn token)
- **SNS**: ~$0.10/month (alerts)
- **Total Phase 1**: ~$7.50/month

### Phase 2 (ML Active - After Training)
**Added costs**:
- **SageMaker Endpoints**: ~$140/month (2 × ml.t2.medium)
- **SageMaker Training**: ~$5/training run (one-time or periodic)
- **Athena Queries**: ~$5/month (data processing)
- **CloudWatch Metrics**: ~$6/month (custom metrics)
- **Total Phase 2**: ~$156/month additional

### Total Monthly Cost (Full System)
**~$163.50/month** when ML optimization is active

**Cost Optimization Options**:
1. Use ml.t2.small endpoints ($70/month savings)
2. Delete endpoints when not actively optimizing
3. Retrain models less frequently
4. Use fewer CloudWatch metrics

---

## 🔧 Troubleshooting Guide

### Token Rotation Fails
**Symptoms**: SNS alert, rotation stuck in AWSPENDING

**Check**:
```bash
# View secret versions
aws secretsmanager list-secret-version-ids --secret-id linkedin-access-token

# Check logs
aws logs tail /aws/lambda/linkedin-ads-token-rotator --follow
```

**Common Issues**:
- Missing client_id or client_secret in secret
- LinkedIn app doesn't have refresh_token grant enabled
- Lambda timeout (increase to 180s)

---

### CloudWatch Metrics Missing
**Symptoms**: No metrics in LinkedInAds/* namespaces

**Check**:
```bash
# List all namespaces
aws cloudwatch list-metrics

# Check if functions ran
aws logs tail /aws/lambda/linkedin-ads-optimizer --since 1h
```

**Common Issues**:
- IAM role missing CloudWatch PutMetricData permission
- Lambda not being invoked (check EventBridge schedules)

---

### Aggregates Not Created
**Symptoms**: S3 path `processed/aggregates/` is empty

**Check**:
```bash
# Check if data exists in Athena
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM linkedin_ads.creative_performance" \
  --result-configuration "OutputLocation=s3://linkedin-ads-athena-results-${ACCOUNT_ID}/"

# Check data processor logs
aws logs tail /aws/lambda/linkedin-ads-data-processor --follow
```

**Common Issues**:
- No data collected yet (need 7+ days)
- Athena table not created (run setup-athena.sh)
- S3 permissions issue

---

### Model Training Fails
**Symptoms**: SageMaker job status = Failed

**Check**:
```bash
# Get training job details
aws sagemaker describe-training-job --training-job-name <job-name>

# View training logs
aws logs tail /aws/sagemaker/TrainingJobs --log-stream-name-prefix <job-name>
```

**Common Issues**:
- Insufficient training data (<100 samples)
- Invalid hyperparameters
- S3 permissions for SageMaker role

---

## 📚 Documentation Reference

Detailed documentation available:

- **NEW_FEATURES.md** - In-depth guide for all 4 new features
- **GAP_ANALYSIS.md** - Original gap analysis
- **FIXES_AND_OPTIONAL_FEATURES.md** - Implementation decisions
- **README.md** - Overall project documentation

---

## ✨ What's Different from Original Plan

All changes are **additions only** - nothing was removed:

### Original Plan (Completed)
✅ Phase 1: Data Collection (deployed)
✅ ML infrastructure (ready)
✅ 3 Lambda functions (ready)
✅ SageMaker training (ready)
✅ Basic monitoring (ready)

### New Additions (This Session)
🆕 Automatic token rotation (no manual OAuth refresh)
🆕 Comprehensive CloudWatch metrics (dashboard-ready)
🆕 Model versioning with rollback (v1, v2, v3...)
🆕 Pre-computed aggregates for Amplify frontend

**Result**: More automated, more observable, more frontend-ready

---

## 🎉 Ready for Deployment

All features are complete and integrated. You can now:

1. **Deploy immediately** - All scripts ready
2. **Let data collect** - Phase 1 runs automatically
3. **Train models** - Once you have data
4. **Activate ML optimization** - Deploy endpoints
5. **Build Amplify frontend** - Use pre-computed aggregates

**No blockers. Ready to ship! 🚀**

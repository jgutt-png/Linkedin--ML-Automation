# New Features Documentation

This document describes the additional features implemented for the LinkedIn Ads ML Pipeline before deployment.

## Overview

Four major features were added to enhance automation, observability, and frontend integration:

1. **Token Rotation** - Automatic LinkedIn OAuth refresh
2. **CloudWatch Metrics** - Custom dashboards and monitoring
3. **Model Versioning** - Track and rollback ML models
4. **Processed Aggregates** - Pre-computed data for Amplify frontend

---

## 1. Token Rotation

### What It Does

Automatically refreshes your LinkedIn OAuth token every 55 days (before the 60-day expiration) using AWS Secrets Manager rotation.

### Why It's Important

- **Eliminates manual token refresh** - No more manual OAuth flows
- **Prevents data collection gaps** - Token always stays fresh
- **SNS notifications** - Get alerts on success/failure
- **Fully automated** - Set it and forget it

### How It Works

1. **Secrets Manager** triggers rotation every 55 days
2. **Lambda function** uses refresh_token to get new access_token
3. **Tests new token** by calling LinkedIn API
4. **Swaps versions** - AWSPENDING → AWSCURRENT
5. **Sends notification** via SNS

### Setup

```bash
# 1. Create secret with LinkedIn credentials
aws secretsmanager create-secret \
  --name linkedin-access-token \
  --secret-string '{
    "access_token": "YOUR_ACCESS_TOKEN",
    "refresh_token": "YOUR_REFRESH_TOKEN",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'

# 2. Configure rotation
./deploy/setup-token-rotation.sh
```

### Files

- `lambda/token_rotator/handler.py` - Rotation logic (4-step process)
- `lambda/token_rotator/requirements.txt` - Dependencies
- `deploy/setup-token-rotation.sh` - Configuration script

### Monitoring

```bash
# View rotation history
aws secretsmanager list-secret-version-ids --secret-id linkedin-access-token

# Manual rotation (for testing)
aws secretsmanager rotate-secret --secret-id linkedin-access-token

# Check logs
aws logs tail /aws/lambda/linkedin-ads-token-rotator --follow
```

---

## 2. CloudWatch Metrics

### What It Does

Sends comprehensive custom metrics to CloudWatch for dashboard creation and alerting.

### Metrics Sent

**Optimization Actions** (from Optimizer Lambda):
- `TotalActions` - Number of optimization decisions made
- `CreativesPaused` - Underperformers disabled
- `CreativesScaled` - Top performers scaled up
- `BidAdjustments` - Bid changes made
- `TopPerformersIdentified` - High CTR creatives found

**Performance Trends**:
- `TotalImpressions` - Aggregate impressions
- `TotalClicks` - Aggregate clicks
- `TotalCost` - Spend tracked
- `TotalConversions` - Conversions tracked
- `AverageCTR` - Click-through rate (%)
- `AverageCPC` - Cost per click ($)
- `AverageCPA` - Cost per acquisition ($)

**Portfolio Health**:
- `TotalCreatives` - All creatives tracked
- `ActiveCreatives` - Currently running
- `HighPerformers` - CTR >= 3.0%
- `Underperformers` - CTR < 1.0%

### Namespaces

- `LinkedInAds/Optimizer` - Optimization metrics
- `LinkedInAds/Campaigns` - Campaign-specific metrics (with dimensions)

### Creating Dashboards

```bash
# View metrics in AWS Console
https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#metricsV2:

# Example dashboard widgets:
# - Line graph: AverageCTR over time
# - Number: TotalActions today
# - Bar chart: Top campaigns by conversions
```

### Files Modified

- `lambda/optimizer/handler.py` - Added `send_cloudwatch_metrics()` function

---

## 3. Model Versioning

### What It Does

Automatically versions ML models after training with metadata tracking and rollback capability.

### Features

- **Auto-increment versions** - v1, v2, v3, etc.
- **Metadata tracking** - Training job, metrics, timestamps
- **Latest pointer** - Easy access to current production model
- **Rollback support** - Revert to any previous version

### Directory Structure

```
s3://linkedin-ads-data-{account}/models/
├── creative_scorer/
│   ├── v1/
│   │   ├── model.tar.gz
│   │   └── metadata.json
│   ├── v2/
│   │   ├── model.tar.gz
│   │   └── metadata.json
│   ├── latest/
│   │   ├── model.tar.gz
│   │   └── metadata.json
│   └── latest.txt  (contains "v2")
└── bid_optimizer/
    ├── v1/
    ├── v2/
    └── latest/
```

### Metadata Format

```json
{
  "version": 2,
  "model_type": "RandomForestRegressor",
  "training_job": "linkedin-ads-creative-scorer-20250101-120000",
  "created_at": "2025-01-01T12:00:00Z",
  "model_artifacts": "s3://...",
  "metrics": {
    "train:rmse": 0.123,
    "validation:rmse": 0.145
  },
  "status": "production"
}
```

### Usage

```bash
# Train models (auto-versions after completion)
./deploy/train-models.sh

# List all versions
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/models/creative_scorer/

# Get latest version
aws s3 cp s3://linkedin-ads-data-${ACCOUNT_ID}/models/creative_scorer/latest.txt -

# Download specific version
aws s3 cp s3://linkedin-ads-data-${ACCOUNT_ID}/models/creative_scorer/v1/model.tar.gz .

# Rollback to v1 (manually)
aws s3 cp s3://...v1/model.tar.gz s3://...latest/model.tar.gz
echo "v1" | aws s3 cp - s3://...latest.txt
```

### Files Modified

- `deploy/train-models.sh` - Added `version_model()` and `wait_for_training()` functions

---

## 4. Processed Aggregates

### What It Does

Pre-computes daily/weekly aggregates and creative metadata for fast Amplify frontend queries.

### Why It's Important

- **Fast dashboard loading** - No expensive Athena queries
- **Amplify-optimized** - JSON + Parquet formats
- **Real-time updates** - Refreshed by data processor
- **Cost-effective** - One Athena query → many frontend reads

### Aggregates Created

#### Daily Aggregates
- **Timeframe**: Last 90 days
- **Granularity**: Per day, per campaign
- **Location**: `s3://bucket/processed/aggregates/daily/all_days.parquet`
- **Use Case**: Time-series charts, trend lines

**Fields**: report_date, campaign_id, total_creatives, impressions, clicks, cost, conversions, avg_ctr, avg_cpc, avg_cpa

#### Weekly Summaries
- **Timeframe**: Last 180 days (26 weeks)
- **Granularity**: Per week, per campaign
- **Location**: `s3://bucket/processed/aggregates/weekly/all_weeks.parquet`
- **Use Case**: Week-over-week growth, monthly reports

**Fields**: week_start, campaign_id, impressions, clicks, cost, conversions, avg_ctr, avg_cpc, cpc, ctr, cpa

#### Creative Metadata
- **Timeframe**: All-time
- **Granularity**: Per creative
- **Location**:
  - `s3://bucket/processed/aggregates/creative_metadata.json` (for lookups)
  - `s3://bucket/processed/aggregates/creative_metadata.parquet` (for bulk queries)
- **Use Case**: Creative detail pages, performance categories

**Fields**: creative_id, campaign_id, lifetime_impressions, lifetime_clicks, lifetime_cost, lifetime_conversions, avg_ctr, avg_cpc, first_seen, last_seen, days_active, performance_category

**Performance Categories**:
- `high`: CTR >= 3.0%
- `medium`: CTR >= 1.5%
- `low`: CTR >= 0.5%
- `very_low`: CTR < 0.5%

### Amplify Integration

```javascript
// Example: Fetch daily aggregates for last 30 days
const response = await Storage.get('processed/aggregates/daily/all_days.parquet');
const data = await parquet.parse(response);

const last30Days = data.filter(d =>
  d.report_date >= new Date(Date.now() - 30*24*60*60*1000)
);

// Example: Get creative metadata
const creativeMeta = await fetch(
  's3://bucket/processed/aggregates/creative_metadata.json'
);
const creatives = await creativeMeta.json();

// Quick lookup
const creativeInfo = creatives['urn:li:sponsoredCreative:123'];
console.log(creativeInfo.performance_category); // "high"
console.log(creativeInfo.lifetime_clicks); // 1234
```

### When Aggregates Update

Aggregates are created every time the data processor runs:

```bash
# Manual trigger
aws lambda invoke \
  --function-name linkedin-ads-data-processor \
  response.json

# Check aggregates created
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/processed/aggregates/
```

### Files Modified

- `lambda/data_processor/handler.py` - Added 3 aggregate functions:
  - `create_daily_aggregates()`
  - `create_weekly_summaries()`
  - `create_creative_metadata()`

---

## Deployment Checklist

All new features are now integrated into the deployment process:

### Infrastructure Deployment
```bash
./deploy/deploy-infrastructure.sh
```
**Includes**:
- ✅ Token rotator Lambda packaging
- ✅ Token rotator IAM role creation
- ✅ CloudWatch alarms for token rotator

### Lambda Deployment
```bash
./deploy/deploy-lambdas.sh
```
**Deploys**:
- ✅ linkedin-ads-data-processor (with aggregates)
- ✅ linkedin-ads-optimizer (with CloudWatch metrics)
- ✅ linkedin-ads-copy-generator
- ✅ linkedin-ads-token-rotator

### Token Rotation Setup
```bash
./deploy/setup-token-rotation.sh
```
**Configures**:
- ✅ Secrets Manager rotation schedule (every 55 days)
- ✅ Lambda permissions
- ✅ Optional rotation test

### Model Training
```bash
./deploy/train-models.sh
```
**Features**:
- ✅ Automatic model versioning
- ✅ Metadata tracking
- ✅ Latest pointer updates

---

## Monitoring All Features

### CloudWatch Logs

```bash
# Token rotation
aws logs tail /aws/lambda/linkedin-ads-token-rotator --follow

# Optimizer (metrics)
aws logs tail /aws/lambda/linkedin-ads-optimizer --follow

# Data processor (aggregates)
aws logs tail /aws/lambda/linkedin-ads-data-processor --follow
```

### CloudWatch Metrics

```bash
# View all custom metrics
aws cloudwatch list-metrics --namespace LinkedInAds/Optimizer
aws cloudwatch list-metrics --namespace LinkedInAds/Campaigns

# Get metric data
aws cloudwatch get-metric-statistics \
  --namespace LinkedInAds/Optimizer \
  --metric-name AverageCTR \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### SNS Notifications

Subscribe to alerts:

```bash
# Get SNS topic
SNS_TOPIC=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'linkedin-ads-alerts')].TopicArn" --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn ${SNS_TOPIC} \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### S3 Data Inspection

```bash
# View aggregates
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/processed/aggregates/

# Download for inspection
aws s3 cp s3://linkedin-ads-data-${ACCOUNT_ID}/processed/aggregates/creative_metadata.json .

# View model versions
aws s3 ls s3://linkedin-ads-data-${ACCOUNT_ID}/models/creative_scorer/
```

---

## Next Steps

1. **Deploy Infrastructure**: `./deploy/deploy-infrastructure.sh`
2. **Deploy Lambdas**: `./deploy/deploy-lambdas.sh`
3. **Store Secrets**: Create LinkedIn token and Anthropic API key in Secrets Manager
4. **Setup Token Rotation**: `./deploy/setup-token-rotation.sh`
5. **Create Schedules**: `./deploy/deploy-schedules.sh`
6. **Wait for Data**: Let Phase 1 collect data (7+ days)
7. **Setup Athena**: `./deploy/setup-athena.sh`
8. **Train Models**: `./deploy/train-models.sh`
9. **Deploy Endpoints**: `./deploy/deploy-endpoints.sh`
10. **Build Amplify Frontend**: Connect to S3 aggregates

---

## Frontend Integration Guide

### Recommended Amplify Architecture

```
amplify/
├── backend/
│   └── storage/
│       └── linkedinAdsData/
│           ├── bucket: linkedin-ads-data-{account}
│           └── access: read
└── src/
    ├── components/
    │   ├── DashboardCharts.jsx (daily aggregates)
    │   ├── WeeklyTrends.jsx (weekly summaries)
    │   └── CreativeGrid.jsx (creative metadata)
    └── utils/
        └── dataFetcher.js
```

### Example Data Fetcher

```javascript
import { Storage } from 'aws-amplify';
import * as parquet from 'parquetjs';

export async function getDailyData(days = 30) {
  const key = 'processed/aggregates/daily/all_days.parquet';
  const response = await Storage.get(key, { download: true });
  const reader = await parquet.ParquetReader.openBuffer(response.Body);
  const records = await reader.toArray();

  // Filter to last N days
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);

  return records.filter(r => new Date(r.report_date) >= cutoff);
}

export async function getCreativeMetadata() {
  const key = 'processed/aggregates/creative_metadata.json';
  const response = await Storage.get(key, { download: true });
  return JSON.parse(await response.Body.text());
}

export async function getWeeklyTrends() {
  const key = 'processed/aggregates/weekly/all_weeks.parquet';
  const response = await Storage.get(key, { download: true });
  const reader = await parquet.ParquetReader.openBuffer(response.Body);
  return await reader.toArray();
}
```

---

## Troubleshooting

### Token Rotation Fails

**Check**:
1. Secret has all required fields (access_token, refresh_token, client_id, client_secret)
2. LinkedIn app has refresh_token grant enabled
3. Lambda has permission to update secret
4. Check CloudWatch logs for error details

**Fix**:
```bash
# View secret structure
aws secretsmanager get-secret-value --secret-id linkedin-access-token

# Check Lambda logs
aws logs tail /aws/lambda/linkedin-ads-token-rotator --follow
```

### CloudWatch Metrics Not Appearing

**Check**:
1. Optimizer Lambda is running
2. Environment variables are set
3. IAM role has CloudWatch PutMetricData permission

**Fix**:
```bash
# Test optimizer manually
aws lambda invoke --function-name linkedin-ads-optimizer response.json

# Check metrics
aws cloudwatch list-metrics --namespace LinkedInAds/Optimizer
```

### Aggregates Not Created

**Check**:
1. Data processor Lambda completed successfully
2. Athena queries returned data
3. S3 bucket permissions are correct

**Fix**:
```bash
# Check logs
aws logs tail /aws/lambda/linkedin-ads-data-processor --follow

# Verify data exists in Athena
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM linkedin_ads.creative_performance" \
  --result-configuration "OutputLocation=s3://linkedin-ads-athena-results-${ACCOUNT_ID}/"
```

### Model Versioning Not Working

**Check**:
1. Training completed successfully
2. S3 permissions allow copy operations
3. Model artifacts exist

**Fix**:
```bash
# Check training job status
aws sagemaker describe-training-job --training-job-name <job-name>

# Manually version
./deploy/train-models.sh
```

---

## Cost Impact

### Token Rotation
- **Lambda**: ~1 invocation/month (55 days) = $0.00
- **Secrets Manager**: $0.40/month per secret
- **Total**: ~$0.40/month

### CloudWatch Metrics
- **Custom Metrics**: ~20 metrics × $0.30 = $6.00/month
- **API Calls**: Negligible
- **Total**: ~$6.00/month

### Processed Aggregates
- **S3 Storage**: ~10 MB × $0.023/GB = $0.00
- **Athena Queries**: 3 queries/day × $5/TB = ~$0.15/month
- **Total**: ~$0.15/month

### Model Versioning
- **S3 Storage**: ~100 MB/version × 5 versions = ~$0.01/month
- **No additional compute cost**
- **Total**: ~$0.01/month

**Grand Total: ~$6.56/month for all new features**

---

## Summary

All four optional features are now fully integrated:

| Feature | Status | Files Modified | Benefits |
|---------|--------|----------------|----------|
| Token Rotation | ✅ Complete | Lambda + IAM + Deploy scripts | Zero manual token refresh |
| CloudWatch Metrics | ✅ Complete | Optimizer Lambda | Dashboard-ready metrics |
| Model Versioning | ✅ Complete | Training script | Rollback capability |
| Processed Aggregates | ✅ Complete | Data Processor Lambda | Fast frontend queries |

Ready for deployment! 🚀

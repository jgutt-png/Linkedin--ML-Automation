# AWS Architecture - LinkedIn Ads Automation

Complete technical architecture for automated LinkedIn advertising optimization pipeline.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          LINKEDIN ADS AUTOMATION                        │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   LinkedIn   │───▶│    Lambda    │───▶│      S3      │              │
│  │   Ads API    │    │  (Collector) │    │  (Raw Data)  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                    │                      │
│         │                   │                    ▼                      │
│         │            ┌──────────────┐    ┌──────────────┐              │
│         │            │  EventBridge │    │    Athena    │              │
│         │            │  (Scheduler) │    │  (Queries)   │              │
│         │            └──────────────┘    └──────────────┘              │
│         │                                        │                      │
│         │                                        ▼                      │
│         │                                 ┌──────────────┐              │
│         │                                 │  CloudWatch  │              │
│         │                                 │  (Metrics)   │              │
│         │                                 └──────────────┘              │
│         │                                        │                      │
│         │                                        ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   LinkedIn   │◀───│    Lambda    │◀───│  SageMaker   │              │
│  │   Ads API    │    │  (Optimizer) │    │   (Models)   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                   │                    ▲                      │
│         │                   │                    │                      │
│         │                   ▼                    │                      │
│         │            ┌──────────────┐            │                      │
│         │            │   Secrets    │            │                      │
│         │            │   Manager    │            │                      │
│         │            └──────────────┘            │                      │
│         │                                        │                      │
│         └────────────────────────────────────────┘                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Collection Pipeline

**Timeline**: Week 1
**Goal**: Get LinkedIn ad data flowing into S3 every 6 hours

### Components

1. **S3 Bucket** - Store raw JSON from LinkedIn API
2. **Lambda (Collector)** - Pull analytics data
3. **EventBridge** - Schedule collection every 6 hours
4. **Secrets Manager** - OAuth tokens and credentials
5. **IAM Roles** - Permissions

---

### S3 Bucket Structure

```
s3://your-company-linkedin-ads/
│
├── raw/                                    # Raw API responses
│   └── analytics/
│       └── 2024/
│           └── 12/
│               └── 01/
│                   ├── creative_performance_1701432000.json
│                   ├── campaign_performance_1701432000.json
│                   └── daily_summary_1701432000.json
│
├── processed/                              # Cleaned/aggregated data
│   ├── daily_aggregates/
│   │   └── 2024-12-01.parquet
│   ├── weekly_summaries/
│   │   └── 2024-W48.parquet
│   └── creative_metadata/
│       └── all_creatives.json
│
├── models/                                 # ML model artifacts
│   ├── creative_scoring/
│   │   └── v1/
│   │       ├── model.tar.gz
│   │       └── metadata.json
│   └── bid_optimizer/
│       └── v1/
│           └── model.tar.gz
│
└── logs/                                   # Action logs
    └── optimizer_actions/
        └── 2024-12-01.jsonl
```

---

### Data Schema

#### Raw Creative Performance Data

```json
{
  "timestamp": "2024-12-01T12:00:00Z",
  "pulled_at": "2024-12-01T12:05:23Z",
  "campaign_id": "454453134",
  "campaign_name": "Real Estate Investors - Q4 2024",
  "ad_account_id": "123456789",
  "date_range": {
    "start": "2024-11-30T00:00:00Z",
    "end": "2024-12-01T00:00:00Z"
  },
  "creatives": [
    {
      "creative_id": "934611584",
      "creative_name": "Off-Market Deals - Version A",
      "status": "ACTIVE",
      "metrics": {
        "impressions": 1250,
        "clicks": 45,
        "cost_usd": 225.00,
        "conversions": 3,
        "ctr": 0.036,
        "cpc": 5.00,
        "conversion_rate": 0.0667,
        "cost_per_conversion": 75.00
      },
      "targeting": {
        "locations": ["urn:li:geo:103644278"],
        "job_titles": ["urn:li:title:4081", "urn:li:title:463"],
        "job_functions": ["urn:li:function:17"],
        "seniority": ["urn:li:seniority:4", "urn:li:seniority:5"]
      },
      "creative_content": {
        "headline": "Find Off-Market Real Estate Deals Before Competitors",
        "description": "Access exclusive data intelligence on distressed properties...",
        "cta": "Get Started",
        "image_url": "https://media.licdn.com/..."
      }
    }
  ]
}
```

---

### Lambda: Data Collector

**File**: `lambda/collector/handler.py`

```python
"""
LinkedIn Ads Data Collector
Pulls campaign and creative analytics every 6 hours
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os

# AWS Clients
s3 = boto3.client('s3')
secrets = boto3.client('secretsmanager')
cloudwatch = boto3.client('cloudwatch')

# Environment Variables
BUCKET_NAME = os.environ['BUCKET_NAME']
CAMPAIGN_IDS = os.environ['CAMPAIGN_IDS'].split(',')
SECRET_NAME = os.environ['SECRET_NAME']


def get_linkedin_credentials() -> Dict[str, str]:
    """Retrieve LinkedIn OAuth token from Secrets Manager."""
    try:
        response = secrets.get_secret_value(SecretId=SECRET_NAME)
        credentials = json.loads(response['SecretString'])
        return credentials
    except Exception as e:
        print(f"Error retrieving credentials: {e}")
        raise


def get_api_headers(access_token: str) -> Dict[str, str]:
    """Generate headers for LinkedIn API requests."""
    return {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202411',
        'Content-Type': 'application/json'
    }


def pull_creative_analytics(
    access_token: str,
    campaign_id: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """
    Pull performance metrics broken down by creative.

    API Endpoint: GET /adAnalytics
    Docs: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
    """

    headers = get_api_headers(access_token)

    params = {
        'q': 'analytics',
        'pivot': 'CREATIVE',
        'dateRange.start.day': start_date.day,
        'dateRange.start.month': start_date.month,
        'dateRange.start.year': start_date.year,
        'dateRange.end.day': end_date.day,
        'dateRange.end.month': end_date.month,
        'dateRange.end.year': end_date.year,
        'campaigns[0]': f'urn:li:sponsoredCampaign:{campaign_id}',
        'fields': 'dateRange,impressions,clicks,costInUsd,externalWebsiteConversions,approximateUniqueImpressions'
    }

    try:
        response = requests.get(
            'https://api.linkedin.com/rest/adAnalytics',
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling LinkedIn API: {e}")
        raise


def pull_campaign_details(access_token: str, campaign_id: str) -> Dict[str, Any]:
    """Get campaign configuration including targeting."""

    headers = get_api_headers(access_token)

    try:
        response = requests.get(
            f'https://api.linkedin.com/rest/adCampaigns/{campaign_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting campaign details: {e}")
        raise


def save_to_s3(data: Dict[str, Any], bucket: str, key: str) -> None:
    """Save JSON data to S3."""
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2, default=str),
            ContentType='application/json'
        )
        print(f"Saved to s3://{bucket}/{key}")
    except Exception as e:
        print(f"Error saving to S3: {e}")
        raise


def send_cloudwatch_metrics(metrics: Dict[str, float]) -> None:
    """Send custom metrics to CloudWatch."""
    try:
        metric_data = [
            {
                'MetricName': key,
                'Value': value,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            }
            for key, value in metrics.items()
        ]

        cloudwatch.put_metric_data(
            Namespace='LinkedInAds/Collector',
            MetricData=metric_data
        )
    except Exception as e:
        print(f"Error sending CloudWatch metrics: {e}")


def lambda_handler(event, context):
    """
    Main Lambda handler - executes every 6 hours via EventBridge.

    Flow:
    1. Get LinkedIn OAuth token from Secrets Manager
    2. Pull analytics for each campaign (last 24 hours)
    3. Save raw data to S3
    4. Send metrics to CloudWatch
    """

    print(f"Starting data collection at {datetime.utcnow().isoformat()}")

    # Date range (last 24 hours)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)

    try:
        # Get credentials
        credentials = get_linkedin_credentials()
        access_token = credentials['access_token']

        total_impressions = 0
        total_clicks = 0
        total_cost = 0

        # Process each campaign
        for campaign_id in CAMPAIGN_IDS:
            print(f"Processing campaign {campaign_id}")

            # Pull analytics data
            analytics_data = pull_creative_analytics(
                access_token,
                campaign_id,
                start_date,
                end_date
            )

            # Pull campaign configuration
            campaign_details = pull_campaign_details(access_token, campaign_id)

            # Combine data
            payload = {
                'pulled_at': datetime.utcnow().isoformat(),
                'campaign_id': campaign_id,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'analytics': analytics_data,
                'campaign_config': campaign_details
            }

            # Calculate totals for CloudWatch
            if 'elements' in analytics_data:
                for element in analytics_data['elements']:
                    total_impressions += element.get('impressions', 0)
                    total_clicks += element.get('clicks', 0)
                    total_cost += element.get('costInUsd', 0)

            # Save to S3
            timestamp = int(datetime.utcnow().timestamp())
            s3_key = (
                f"raw/analytics/"
                f"{end_date.year}/"
                f"{end_date.month:02d}/"
                f"{end_date.day:02d}/"
                f"campaign_{campaign_id}_{timestamp}.json"
            )

            save_to_s3(payload, BUCKET_NAME, s3_key)

        # Send metrics to CloudWatch
        send_cloudwatch_metrics({
            'TotalImpressions': total_impressions,
            'TotalClicks': total_clicks,
            'TotalCost': total_cost,
            'CTR': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
            'CPC': (total_cost / total_clicks) if total_clicks > 0 else 0
        })

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data collection successful',
                'campaigns_processed': len(CAMPAIGN_IDS),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        print(f"Error in lambda_handler: {e}")

        # Send failure metric
        send_cloudwatch_metrics({'CollectionFailure': 1})

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Data collection failed',
                'error': str(e)
            })
        }
```

**File**: `lambda/collector/requirements.txt`

```
requests==2.31.0
boto3==1.28.85
```

---

### Terraform Infrastructure

**File**: `terraform/main.tf`

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "your-company-terraform-state"
    key    = "linkedin-automation/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "LinkedIn Ads Automation"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

**File**: `terraform/variables.tf`

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "linkedin-ads-automation"
}

variable "campaign_ids" {
  description = "Comma-separated list of LinkedIn campaign IDs to track"
  type        = string
  default     = "454453134"
}

variable "collection_schedule" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "rate(6 hours)"
}
```

**File**: `terraform/s3.tf`

```hcl
# S3 Bucket for storing LinkedIn ads data
resource "aws_s3_bucket" "linkedin_ads" {
  bucket = "your-company-${var.project_name}"
}

# Enable versioning
resource "aws_s3_bucket_versioning" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy - delete raw data after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  rule {
    id     = "delete-old-raw-data"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    expiration {
      days = 90
    }
  }

  rule {
    id     = "archive-processed-data"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

**File**: `terraform/secrets.tf`

```hcl
# Secrets Manager for LinkedIn OAuth tokens
resource "aws_secretsmanager_secret" "linkedin_credentials" {
  name        = "${var.project_name}-credentials"
  description = "LinkedIn Ads API OAuth credentials"

  recovery_window_in_days = 7
}

# Secret rotation (optional - implement later)
resource "aws_secretsmanager_secret_rotation" "linkedin_credentials" {
  secret_id           = aws_secretsmanager_secret.linkedin_credentials.id
  rotation_lambda_arn = aws_lambda_function.token_rotator.arn

  rotation_rules {
    automatically_after_days = 60
  }
}

# Output the secret ARN
output "linkedin_credentials_arn" {
  description = "ARN of LinkedIn credentials secret"
  value       = aws_secretsmanager_secret.linkedin_credentials.arn
  sensitive   = true
}
```

**File**: `terraform/lambda.tf`

```hcl
# IAM Role for Lambda Collector
resource "aws_iam_role" "lambda_collector" {
  name = "${var.project_name}-collector-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda Collector
resource "aws_iam_role_policy" "lambda_collector" {
  name = "${var.project_name}-collector-policy"
  role = aws_iam_role.lambda_collector.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.linkedin_ads.arn,
          "${aws_s3_bucket.linkedin_ads.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.linkedin_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_collector" {
  name              = "/aws/lambda/${aws_lambda_function.collector.function_name}"
  retention_in_days = 14
}

# Lambda Function - Data Collector
resource "aws_lambda_function" "collector" {
  filename         = "collector.zip"
  function_name    = "${var.project_name}-collector"
  role            = aws_iam_role.lambda_collector.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  source_code_hash = filebase64sha256("collector.zip")

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.linkedin_ads.id
      CAMPAIGN_IDS = var.campaign_ids
      SECRET_NAME  = aws_secretsmanager_secret.linkedin_credentials.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_collector
  ]
}

# Lambda Function URL (optional - for manual triggers)
resource "aws_lambda_function_url" "collector" {
  function_name      = aws_lambda_function.collector.function_name
  authorization_type = "AWS_IAM"
}
```

**File**: `terraform/eventbridge.tf`

```hcl
# EventBridge Rule - Schedule collection every 6 hours
resource "aws_cloudwatch_event_rule" "collector_schedule" {
  name                = "${var.project_name}-collector-schedule"
  description         = "Trigger LinkedIn data collection every 6 hours"
  schedule_expression = var.collection_schedule
}

# EventBridge Target - Lambda Function
resource "aws_cloudwatch_event_target" "collector" {
  rule      = aws_cloudwatch_event_rule.collector_schedule.name
  target_id = "linkedin-ads-collector"
  arn       = aws_lambda_function.collector.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.collector_schedule.arn
}
```

---

## Phase 2: Analytics with Athena

**Timeline**: Week 2
**Goal**: Query and analyze collected data

### Athena Table Definition

**File**: `athena/create_tables.sql`

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS linkedin_ads;

-- Raw analytics table
CREATE EXTERNAL TABLE IF NOT EXISTS linkedin_ads.raw_analytics (
  pulled_at STRING,
  campaign_id STRING,
  date_range STRUCT<
    start: STRING,
    end: STRING
  >,
  analytics STRUCT<
    elements: ARRAY<STRUCT<
      pivotValue: STRING,
      dateRange: STRUCT<
        start: STRUCT<day: INT, month: INT, year: INT>,
        end: STRUCT<day: INT, month: INT, year: INT>
      >,
      impressions: BIGINT,
      clicks: BIGINT,
      costInUsd: DOUBLE,
      externalWebsiteConversions: BIGINT,
      approximateUniqueImpressions: BIGINT
    >>
  >,
  campaign_config STRUCT<
    id: STRING,
    name: STRING,
    status: STRING,
    dailyBudget: STRUCT<amount: DOUBLE, currencyCode: STRING>,
    unitCost: STRUCT<amount: DOUBLE, currencyCode: STRING>
  >
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true'
)
LOCATION 's3://your-company-linkedin-ads-automation/raw/analytics/';

-- Performance by creative view
CREATE OR REPLACE VIEW linkedin_ads.creative_performance AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  elem.pivotValue as creative_id,
  SUM(elem.impressions) as total_impressions,
  SUM(elem.clicks) as total_clicks,
  SUM(elem.costInUsd) as total_cost,
  SUM(elem.externalWebsiteConversions) as total_conversions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr_percent,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as avg_cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cost_per_conversion
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  elem.pivotValue;

-- Daily campaign summary view
CREATE OR REPLACE VIEW linkedin_ads.daily_summary AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  campaign_config.name as campaign_name,
  campaign_config.dailyBudget.amount as daily_budget,
  SUM(elem.impressions) as impressions,
  SUM(elem.clicks) as clicks,
  SUM(elem.costInUsd) as cost,
  SUM(elem.externalWebsiteConversions) as conversions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cpa
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  campaign_config.name,
  campaign_config.dailyBudget.amount
ORDER BY report_date DESC;
```

### Common Queries

```sql
-- Top performing creatives (last 7 days)
SELECT
  creative_id,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  AVG(ctr_percent) as avg_ctr,
  AVG(avg_cpc) as avg_cpc,
  SUM(total_conversions) as conversions
FROM linkedin_ads.creative_performance
WHERE report_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY creative_id
HAVING SUM(total_clicks) > 10  -- Minimum sample size
ORDER BY avg_ctr DESC
LIMIT 10;

-- Underperforming creatives to pause
SELECT
  creative_id,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  AVG(ctr_percent) as avg_ctr,
  SUM(total_cost) as total_spent
FROM linkedin_ads.creative_performance
WHERE report_date >= CURRENT_DATE - INTERVAL '3' DAY
GROUP BY creative_id
HAVING
  SUM(total_clicks) > 100 AND  -- Minimum sample size
  AVG(ctr_percent) < 1.0       -- CTR below 1%
ORDER BY total_spent DESC;

-- Daily trend analysis
SELECT
  report_date,
  SUM(impressions) as total_impressions,
  SUM(clicks) as total_clicks,
  SUM(cost) as total_cost,
  AVG(ctr) as avg_ctr,
  AVG(cpc) as avg_cpc
FROM linkedin_ads.daily_summary
WHERE report_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY report_date
ORDER BY report_date;

-- Budget pacing check
SELECT
  campaign_id,
  campaign_name,
  daily_budget,
  SUM(cost) as actual_spend,
  ROUND((SUM(cost) / daily_budget) * 100, 1) as pacing_percent
FROM linkedin_ads.daily_summary
WHERE report_date = CURRENT_DATE
GROUP BY campaign_id, campaign_name, daily_budget;
```

---

## Phase 3: ML Models

**Timeline**: Week 3-4
**Goal**: Train models to predict performance

### Model 1: Creative CTR Predictor

**File**: `sagemaker/train_creative_scorer.py`

```python
"""
Train a model to predict creative CTR based on copy features.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import boto3
import json

def extract_features(creative_copy: str) -> dict:
    """Extract features from ad copy."""

    features = {
        'word_count': len(creative_copy.split()),
        'char_count': len(creative_copy),
        'has_numbers': any(char.isdigit() for char in creative_copy),
        'has_percent': '%' in creative_copy,
        'has_dollar': '$' in creative_copy,
        'has_question': '?' in creative_copy,
        'has_exclamation': '!' in creative_copy,
        'mention_free': 'free' in creative_copy.lower(),
        'mention_new': 'new' in creative_copy.lower(),
        'mention_now': 'now' in creative_copy.lower(),
        'mention_today': 'today' in creative_copy.lower(),
        'mention_data': 'data' in creative_copy.lower(),
        'mention_exclusive': 'exclusive' in creative_copy.lower(),
        'uppercase_ratio': sum(1 for c in creative_copy if c.isupper()) / len(creative_copy) if creative_copy else 0
    }

    return features

def train_model(training_data_s3_path: str):
    """Train creative CTR prediction model."""

    # Load training data from S3
    s3 = boto3.client('s3')
    # ... load data logic

    # Extract features
    X = pd.DataFrame([
        extract_features(row['creative_copy'])
        for _, row in df.iterrows()
    ])

    y = df['ctr']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=42
    )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print(f"MSE: {mse:.4f}")
    print(f"R²: {r2:.4f}")

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop features:")
    print(feature_importance.head(10))

    # Save model
    joblib.dump(model, '/opt/ml/model/creative_scorer.joblib')

    return model

if __name__ == '__main__':
    train_model('s3://your-company-linkedin-ads-automation/processed/training/')
```

---

## Phase 4: Automated Optimization

**Timeline**: Week 5
**Goal**: Full automation - no manual intervention

### Decision Engine Lambda

**File**: `lambda/optimizer/handler.py`

```python
"""
LinkedIn Ads Optimizer
Runs daily to:
- Pause underperforming creatives
- Scale winning creatives
- Adjust bids
- Generate new variations
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

# Thresholds
MIN_CTR_THRESHOLD = 1.0  # Pause if CTR < 1%
TOP_PERFORMER_THRESHOLD = 3.0  # Scale if CTR > 3%
MIN_SAMPLE_SIZE = 100  # Minimum clicks before making decisions
MAX_CPC = 8.0  # Pause if CPC > $8

def get_performance_data(days=7) -> List[Dict]:
    """Query Athena for recent performance."""

    athena = boto3.client('athena')

    query = f"""
    SELECT
      creative_id,
      SUM(total_impressions) as impressions,
      SUM(total_clicks) as clicks,
      AVG(ctr_percent) as ctr,
      AVG(avg_cpc) as cpc,
      SUM(total_cost) as cost
    FROM linkedin_ads.creative_performance
    WHERE report_date >= CURRENT_DATE - INTERVAL '{days}' DAY
    GROUP BY creative_id
    HAVING SUM(total_clicks) > {MIN_SAMPLE_SIZE}
    """

    # Execute query and get results
    # ... implementation

    return results

def pause_creative(access_token: str, creative_id: str) -> bool:
    """Pause an underperforming creative."""

    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202411',
        'Content-Type': 'application/json'
    }

    payload = {
        'status': 'PAUSED'
    }

    response = requests.patch(
        f'https://api.linkedin.com/rest/creatives/{creative_id}',
        headers=headers,
        json=payload
    )

    return response.status_code == 200

def create_variation(access_token: str, winning_creative_id: str) -> str:
    """Create a variation of a winning creative."""

    # Get original creative
    # Generate new copy variation
    # Create new creative
    # Return new creative ID

    pass

def update_campaign_bid(access_token: str, campaign_id: str, new_bid: float) -> bool:
    """Update campaign bid."""

    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202411',
        'Content-Type': 'application/json'
    }

    payload = {
        'unitCost': {
            'amount': str(new_bid),
            'currencyCode': 'USD'
        }
    }

    response = requests.patch(
        f'https://api.linkedin.com/rest/adCampaigns/{campaign_id}',
        headers=headers,
        json=payload
    )

    return response.status_code == 200

def lambda_handler(event, context):
    """Main optimization loop - runs daily."""

    print(f"Starting optimization at {datetime.utcnow().isoformat()}")

    actions_taken = []

    # Get credentials
    credentials = get_linkedin_credentials()
    access_token = credentials['access_token']

    # Get performance data
    performance = get_performance_data(days=7)

    # Process each creative
    for creative in performance:
        creative_id = creative['creative_id']
        ctr = creative['ctr']
        cpc = creative['cpc']
        clicks = creative['clicks']

        # Pause underperformers
        if ctr < MIN_CTR_THRESHOLD and clicks > MIN_SAMPLE_SIZE:
            if pause_creative(access_token, creative_id):
                actions_taken.append({
                    'action': 'paused',
                    'creative_id': creative_id,
                    'reason': f'CTR {ctr:.2f}% below threshold',
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Scale winners
        elif ctr > TOP_PERFORMER_THRESHOLD:
            new_creative_id = create_variation(access_token, creative_id)
            if new_creative_id:
                actions_taken.append({
                    'action': 'scaled',
                    'original_creative_id': creative_id,
                    'new_creative_id': new_creative_id,
                    'reason': f'High CTR {ctr:.2f}%',
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Pause high CPC
        if cpc > MAX_CPC:
            if pause_creative(access_token, creative_id):
                actions_taken.append({
                    'action': 'paused',
                    'creative_id': creative_id,
                    'reason': f'CPC ${cpc:.2f} above threshold',
                    'timestamp': datetime.utcnow().isoformat()
                })

    # Log actions
    log_actions(actions_taken)

    # Send report
    send_daily_report(actions_taken)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'actions_taken': len(actions_taken),
            'timestamp': datetime.utcnow().isoformat()
        })
    }
```

---

## Cost Analysis

### Monthly AWS Costs

| Service | Usage | Cost |
|---------|-------|------|
| **Lambda (Collector)** | 120 invocations/month (6 hrs) × 30s × 512MB | $0.50 |
| **Lambda (Optimizer)** | 30 invocations/month (daily) × 2min × 1024MB | $1.00 |
| **S3** | 100GB storage + 1M API requests | $2.50 |
| **Athena** | 100GB scanned/month | $5.00 |
| **Secrets Manager** | 2 secrets | $0.80 |
| **EventBridge** | 150 rules/month | $0.00 (free tier) |
| **CloudWatch Logs** | 5GB/month | $2.50 |
| **SageMaker Training** | 10 hours/month ml.m5.large | $10.00 |
| **SageMaker Endpoint** (optional) | Real-time predictions | $50.00 |
| **TOTAL** | | **$22.30 - $72.30** |

**Ad Spend**: $1,667/month ($20K/year)
**Infrastructure**: < 5% of ad budget

---

## Security Best Practices

1. **Secrets Management**
   - Store all credentials in Secrets Manager
   - Enable automatic rotation
   - Never commit to git

2. **IAM Least Privilege**
   - Separate roles for each Lambda
   - S3 bucket policies to restrict access
   - CloudTrail logging enabled

3. **Data Encryption**
   - S3 server-side encryption (SSE-S3)
   - Secrets Manager encryption at rest
   - TLS for all API calls

4. **Monitoring**
   - CloudWatch alarms for failures
   - Daily cost reports
   - Weekly performance summaries

---

## Deployment Checklist

- [ ] LinkedIn API access approved
- [ ] OAuth credentials in Secrets Manager
- [ ] Terraform state S3 bucket created
- [ ] AWS credentials configured locally
- [ ] Lambda deployment packages built
- [ ] Terraform plan reviewed
- [ ] Infrastructure deployed
- [ ] First data collection successful
- [ ] Athena tables created
- [ ] Sample queries tested
- [ ] CloudWatch alarms configured
- [ ] First optimization run successful

---

## Next Steps

1. **Complete LinkedIn API application** (5-10 days)
2. **Deploy Phase 1** - Data collection (1 day)
3. **Let data accumulate** (2 weeks minimum)
4. **Deploy Phase 2** - Analytics (2 days)
5. **Train ML models** (1 week)
6. **Deploy Phase 4** - Automation (3 days)
7. **Monitor and iterate**

---

## Support

For questions or issues:
- **AWS**: AWS Support Console
- **LinkedIn API**: https://www.linkedin.com/help/linkedin/ask/api
- **This project**: Internal team Slack #linkedin-automation

# Implementation Guide

Step-by-step instructions to build the LinkedIn Ads automation pipeline.

---

## Prerequisites

- AWS Account with admin access
- LinkedIn Company Page
- Git installed
- Terraform installed (>= 1.0)
- Python 3.11+
- AWS CLI configured

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Setup** | 1 day | LinkedIn API + AWS foundation |
| **Phase 1** | 1 day | Data collection pipeline |
| **Data Accumulation** | 2 weeks | Let ads run and gather data |
| **Phase 2** | 2 days | Analytics dashboard |
| **Phase 3** | 1 week | Train ML models |
| **Phase 4** | 3 days | Automated optimization |
| **Total** | ~4 weeks | End-to-end implementation |

---

## Step 1: LinkedIn API Access

### 1.1 Create Developer App

1. Go to https://www.linkedin.com/developers/apps/new
2. Fill in app details:
   - **Name**: YOUR_COMPANY_NAME Ads Manager
   - **LinkedIn Page**: Select your company page
   - **Privacy Policy**: https://acquisitionatlas.com/privacy
   - **Logo**: Upload 300x300px logo
3. Click **Create app**

### 1.2 Request Advertising API Access

1. Navigate to **Products** tab
2. Find **Advertising API** (Development Tier)
3. Click **Request access**
4. Fill out the application form (see [LINKEDIN_API_SETUP.md](./LINKEDIN_API_SETUP.md) for exact responses)
5. Submit and wait 5-10 business days

### 1.3 Save Credentials (After Approval)

Once approved:
1. Go to **Auth** tab
2. Note your **Client ID** and **Client Secret**
3. Add redirect URL: `http://localhost:8000/callback`
4. Verify scopes: `r_ads`, `rw_ads`, `r_basicprofile`, `r_organization_social`

**⚠️ Do NOT commit these credentials to git**

---

## Step 2: AWS Foundation

### 2.1 Create Terraform State Bucket

```bash
aws s3 mb s3://your-company-terraform-state --region us-east-1

aws s3api put-bucket-versioning \
  --bucket your-company-terraform-state \
  --versioning-configuration Status=Enabled
```

### 2.2 Clone Repository

```bash
cd ~
git clone https://github.com/jgutt-png/linkedin-automation.git
cd linkedin-automation
```

### 2.3 Create Directory Structure

```bash
mkdir -p terraform
mkdir -p lambda/collector
mkdir -p lambda/optimizer
mkdir -p athena
mkdir -p sagemaker
mkdir -p scripts
mkdir -p .secrets
```

### 2.4 Store LinkedIn Credentials Locally (Temporary)

Create `.secrets/linkedin_credentials.json`:

```json
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "access_token": "WILL_GENERATE_NEXT"
}
```

Add to `.gitignore`:

```bash
echo ".secrets/" >> .gitignore
```

---

## Step 3: OAuth Flow Setup

### 3.1 Create OAuth Helper Script

**File**: `scripts/oauth_setup.py`

```python
#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 flow to get access token.
Run this once to authorize and get an access token.
"""

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# Load credentials
with open('.secrets/linkedin_credentials.json') as f:
    creds = json.load(f)

CLIENT_ID = creds['client_id']
CLIENT_SECRET = creds['client_secret']
REDIRECT_URI = 'http://localhost:8000/callback'

# OAuth URLs
AUTH_URL = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'

# Required scopes
SCOPES = ['r_ads', 'rw_ads', 'r_basicprofile', 'r_organization_social']

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse authorization code from callback
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'code' in params:
            code = params['code'][0]

            # Exchange code for access token
            token_response = requests.post(TOKEN_URL, data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET
            })

            if token_response.status_code == 200:
                token_data = token_response.json()
                access_token = token_data['access_token']
                expires_in = token_data['expires_in']

                # Save token
                creds['access_token'] = access_token
                creds['expires_in'] = expires_in

                with open('.secrets/linkedin_credentials.json', 'w') as f:
                    json.dump(creds, f, indent=2)

                # Success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"""
                    <html>
                    <body>
                        <h1>Success!</h1>
                        <p>Access token saved. You can close this window.</p>
                    </body>
                    </html>
                """)

                print(f"\n✓ Access token saved!")
                print(f"  Expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            else:
                print(f"Error getting token: {token_response.text}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

def main():
    # Build authorization URL
    auth_params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES)
    }

    auth_url = f"{AUTH_URL}?{'&'.join(f'{k}={v}' for k, v in auth_params.items())}"

    print("Starting OAuth flow...")
    print(f"\n1. Opening browser to authorize app")
    print(f"2. After authorizing, you'll be redirected to localhost:8000")
    print(f"3. Access token will be saved automatically\n")

    # Start local server for callback
    server = HTTPServer(('localhost', 8000), CallbackHandler)

    # Open browser
    webbrowser.open(auth_url)

    # Handle one request (the callback)
    server.handle_request()

    print("\nDone! Access token saved to .secrets/linkedin_credentials.json")

if __name__ == '__main__':
    main()
```

### 3.2 Run OAuth Flow

```bash
chmod +x scripts/oauth_setup.py
python3 scripts/oauth_setup.py
```

This will:
1. Open browser to LinkedIn authorization page
2. After you approve, redirect to localhost:8000
3. Exchange auth code for access token
4. Save token to `.secrets/linkedin_credentials.json`

### 3.3 Test API Access

```bash
# Get access token
ACCESS_TOKEN=$(jq -r '.access_token' .secrets/linkedin_credentials.json)

# Test API call
curl -X GET 'https://api.linkedin.com/rest/adAccounts?q=search' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'X-Restli-Protocol-Version: 2.0.0' \
  -H 'LinkedIn-Version: 202411'
```

Should return your ad accounts.

---

## Step 4: Deploy Phase 1 (Data Collection)

### 4.1 Store Credentials in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name linkedin-ads-automation-credentials \
  --description "LinkedIn Ads API credentials" \
  --secret-string file://.secrets/linkedin_credentials.json \
  --region us-east-1
```

Verify:

```bash
aws secretsmanager get-secret-value \
  --secret-id linkedin-ads-automation-credentials \
  --region us-east-1
```

### 4.2 Create Lambda Deployment Package

```bash
cd lambda/collector

# Copy handler code (from AWS_ARCHITECTURE.md)
# Create requirements.txt:
cat > requirements.txt <<EOF
requests==2.31.0
boto3==1.28.85
EOF

# Install dependencies
pip3 install -r requirements.txt -t .

# Create zip
zip -r ../../collector.zip .

cd ../..
```

### 4.3 Configure Terraform Variables

**File**: `terraform/terraform.tfvars`

```hcl
aws_region        = "us-east-1"
environment       = "prod"
project_name      = "linkedin-ads-automation"
campaign_ids      = "454453134"  # Your LinkedIn campaign ID
collection_schedule = "rate(6 hours)"
```

### 4.4 Initialize Terraform

```bash
cd terraform
terraform init
```

### 4.5 Review Plan

```bash
terraform plan
```

Review the resources that will be created:
- S3 bucket
- Lambda function (collector)
- EventBridge rule
- IAM roles and policies
- CloudWatch log groups

### 4.6 Deploy Infrastructure

```bash
terraform apply
```

Type `yes` to confirm.

### 4.7 Verify Deployment

Check Lambda function:

```bash
aws lambda list-functions --region us-east-1 | grep linkedin-ads
```

Test manual invocation:

```bash
aws lambda invoke \
  --function-name linkedin-ads-automation-collector \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
```

Check S3 for data:

```bash
aws s3 ls s3://your-company-linkedin-ads-automation/raw/analytics/ --recursive
```

---

## Step 5: Set Up Analytics (Phase 2)

### 5.1 Create Athena Database

```bash
# Open AWS Console → Athena
# Or use AWS CLI:

aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS linkedin_ads" \
  --result-configuration "OutputLocation=s3://aws-athena-query-results-YOUR-ACCOUNT-ID/" \
  --region us-east-1
```

### 5.2 Create Tables

Copy SQL from `docs/AWS_ARCHITECTURE.md` → Athena section.

Run each CREATE TABLE and CREATE VIEW statement in Athena console.

### 5.3 Test Queries

```sql
-- Check data is loading
SELECT COUNT(*) as total_rows
FROM linkedin_ads.raw_analytics;

-- Top creatives by CTR
SELECT
  creative_id,
  AVG(ctr_percent) as avg_ctr,
  SUM(total_clicks) as clicks
FROM linkedin_ads.creative_performance
WHERE report_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY creative_id
ORDER BY avg_ctr DESC
LIMIT 10;
```

---

## Step 6: Let Data Accumulate

**Wait 2 weeks** before training ML models.

During this time:
- Monitor Lambda logs in CloudWatch
- Check S3 data is accumulating
- Run Athena queries to spot-check data quality
- Verify EventBridge is triggering on schedule

### Monitoring Commands

```bash
# Check last Lambda execution
aws logs tail /aws/lambda/linkedin-ads-automation-collector --since 1h

# Count S3 objects
aws s3 ls s3://your-company-linkedin-ads-automation/raw/analytics/ --recursive | wc -l

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace LinkedInAds/Collector \
  --metric-name TotalClicks \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

---

## Step 7: Train ML Models (Phase 3)

After 2+ weeks of data:

### 7.1 Prepare Training Data

```sql
-- Export creative performance to S3
CREATE TABLE linkedin_ads.creative_training_data
WITH (
  format = 'PARQUET',
  external_location = 's3://your-company-linkedin-ads-automation/processed/training/'
) AS
SELECT
  creative_id,
  AVG(ctr_percent) as ctr,
  AVG(avg_cpc) as cpc,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  SUM(total_conversions) as conversions
FROM linkedin_ads.creative_performance
GROUP BY creative_id
HAVING SUM(total_clicks) > 50;
```

### 7.2 Set Up SageMaker Notebook

1. AWS Console → SageMaker → Notebooks
2. Create notebook instance (ml.t3.medium)
3. Open Jupyter
4. Upload `sagemaker/train_creative_scorer.py`
5. Run training script

### 7.3 Deploy Model Endpoint (Optional)

If you want real-time predictions:

```python
from sagemaker.sklearn import SKLearnModel

model = SKLearnModel(
    model_data='s3://.../model.tar.gz',
    role='arn:aws:iam::...:role/SageMakerRole',
    entry_point='train_creative_scorer.py',
    framework_version='1.2-1'
)

predictor = model.deploy(
    instance_type='ml.t2.medium',
    initial_instance_count=1
)
```

---

## Step 8: Deploy Optimizer (Phase 4)

### 8.1 Create Optimizer Lambda

```bash
cd lambda/optimizer

# Copy code from AWS_ARCHITECTURE.md
# Create requirements.txt
# Install dependencies
pip3 install -r requirements.txt -t .

# Create zip
zip -r ../../optimizer.zip .

cd ../..
```

### 8.2 Add Optimizer to Terraform

**File**: `terraform/lambda_optimizer.tf`

```hcl
# IAM Role for Optimizer
resource "aws_iam_role" "lambda_optimizer" {
  name = "${var.project_name}-optimizer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Optimizer Lambda
resource "aws_lambda_function" "optimizer" {
  filename         = "optimizer.zip"
  function_name    = "${var.project_name}-optimizer"
  role            = aws_iam_role.lambda_optimizer.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 1024

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.linkedin_ads.id
      SECRET_NAME  = aws_secretsmanager_secret.linkedin_credentials.name
    }
  }
}

# Run daily at 9 AM UTC
resource "aws_cloudwatch_event_rule" "optimizer_schedule" {
  name                = "${var.project_name}-optimizer-schedule"
  schedule_expression = "cron(0 9 * * ? *)"
}

resource "aws_cloudwatch_event_target" "optimizer" {
  rule      = aws_cloudwatch_event_rule.optimizer_schedule.name
  target_id = "optimizer"
  arn       = aws_lambda_function.optimizer.arn
}

resource "aws_lambda_permission" "optimizer_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.optimizer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.optimizer_schedule.arn
}
```

### 8.3 Deploy

```bash
cd terraform
terraform apply
```

### 8.4 Test Optimizer

```bash
# Manual test
aws lambda invoke \
  --function-name linkedin-ads-automation-optimizer \
  --region us-east-1 \
  /tmp/optimizer_response.json

cat /tmp/optimizer_response.json
```

Check CloudWatch logs for actions taken.

---

## Step 9: Monitoring & Alerts

### 9.1 Create CloudWatch Alarms

```bash
# Alert if collector fails
aws cloudwatch put-metric-alarm \
  --alarm-name linkedin-collector-failures \
  --alarm-description "Alert when collector fails" \
  --metric-name CollectionFailure \
  --namespace LinkedInAds/Collector \
  --statistic Sum \
  --period 3600 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:alerts

# Alert if ad spend too high
aws cloudwatch put-metric-alarm \
  --alarm-name linkedin-high-daily-spend \
  --metric-name TotalCost \
  --namespace LinkedInAds/Collector \
  --statistic Sum \
  --period 86400 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:alerts
```

### 9.2 Set Up SNS for Alerts

```bash
# Create SNS topic
aws sns create-topic --name linkedin-ads-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:linkedin-ads-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### 9.3 Daily Summary Email

Add to optimizer Lambda to send daily reports via SNS.

---

## Step 10: Maintenance

### Weekly Tasks
- Review CloudWatch logs for errors
- Check Athena queries for data quality
- Review optimizer actions log
- Verify ad performance improved

### Monthly Tasks
- Review AWS costs
- Retrain ML models with new data
- Adjust optimization thresholds if needed
- Rotate LinkedIn access token (if expired)

### Quarterly Tasks
- Review overall ROI
- Experiment with new targeting
- Add new ML models or features
- Scale infrastructure if needed

---

## Troubleshooting

### Lambda Timeout
**Issue**: Lambda timing out
**Fix**: Increase timeout in Terraform:
```hcl
timeout = 300  # 5 minutes
```

### LinkedIn API Rate Limits
**Issue**: 429 Too Many Requests
**Fix**: Add exponential backoff:
```python
import time
for attempt in range(3):
    response = requests.get(...)
    if response.status_code == 429:
        time.sleep(2 ** attempt)
    else:
        break
```

### Athena Queries Failing
**Issue**: "Table not found" or "Permission denied"
**Fix**: Verify:
- S3 bucket name in CREATE TABLE
- IAM role has S3 read permissions
- Glue Data Catalog permissions

### OAuth Token Expired
**Issue**: 401 Unauthorized from LinkedIn API
**Fix**: Rerun OAuth flow:
```bash
python3 scripts/oauth_setup.py
aws secretsmanager update-secret \
  --secret-id linkedin-ads-automation-credentials \
  --secret-string file://.secrets/linkedin_credentials.json
```

### No Data in S3
**Issue**: S3 bucket empty after first run
**Fix**:
1. Check Lambda logs: `aws logs tail /aws/lambda/linkedin-ads-automation-collector`
2. Verify EventBridge rule is enabled
3. Test Lambda manually
4. Check IAM permissions for S3 PutObject

---

## Cost Optimization Tips

1. **Use S3 Lifecycle Policies**
   - Archive old data to Glacier
   - Delete raw data after 90 days

2. **Optimize Lambda Memory**
   - Start with 512MB
   - Monitor CloudWatch metrics
   - Reduce if memory usage < 50%

3. **Limit Athena Scans**
   - Use partitioned tables
   - Add date range filters to queries
   - Convert to Parquet for smaller scans

4. **SageMaker Endpoints**
   - Use batch inference instead of real-time
   - Or invoke on-demand, don't keep running 24/7

---

## Success Metrics

Track these KPIs to measure success:

| Metric | Before Automation | Target After |
|--------|------------------|--------------|
| CTR | 1.5% | 2.5%+ |
| CPC | $6.50 | $5.00 |
| Time spent on ads | 10 hrs/week | 1 hr/week |
| Ad variations tested | 5/month | 20/month |
| Cost per conversion | $85 | $60 |

---

## Next Steps After Deployment

1. **Week 1**: Monitor data collection, ensure no errors
2. **Week 2**: Run Athena queries, validate data quality
3. **Week 3-4**: Train ML models, test predictions
4. **Week 5**: Enable optimizer, start with conservative thresholds
5. **Week 6+**: Gradually increase automation confidence

---

## Getting Help

- **AWS Issues**: AWS Support Console
- **LinkedIn API**: https://www.linkedin.com/help/linkedin/ask/api
- **Terraform**: https://www.terraform.io/docs
- **This Project**: GitHub Issues

---

## Congratulations! 🎉

You now have a fully automated LinkedIn ads optimization pipeline.

The system will:
- ✓ Collect performance data every 6 hours
- ✓ Identify winners and losers
- ✓ Auto-pause underperformers
- ✓ Scale winning creatives
- ✓ Optimize bids dynamically
- ✓ Send daily reports

**No manual intervention required.**

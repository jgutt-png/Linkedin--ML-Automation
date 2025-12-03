# Deployment Guide

Quick deployment instructions once LinkedIn API is approved.

---

## Prerequisites

✓ LinkedIn Advertising API approved
✓ AWS CLI configured
✓ Terraform installed
✓ Python 3.11+

---

## Step 1: Create Terraform State Bucket

```bash
aws s3 mb s3://your-company-terraform-state --region us-east-1

aws s3api put-bucket-versioning \
  --bucket your-company-terraform-state \
  --versioning-configuration Status=Enabled
```

---

## Step 2: Set Up LinkedIn Credentials

### Create credentials file

```bash
mkdir -p .secrets
cat > .secrets/linkedin_credentials.json <<EOF
{
  "client_id": "YOUR_CLIENT_ID_FROM_LINKEDIN",
  "client_secret": "YOUR_CLIENT_SECRET_FROM_LINKEDIN"
}
EOF
```

### Run OAuth flow

```bash
chmod +x scripts/oauth_setup.py
python3 scripts/oauth_setup.py
```

This will:
- Open browser for LinkedIn authorization
- Save access token locally
- Upload to AWS Secrets Manager

---

## Step 3: Build Lambda Package

```bash
cd lambda/collector

# Install dependencies
pip3 install -r requirements.txt -t .

# Create deployment package
zip -r ../../collector.zip .

cd ../..
```

---

## Step 4: Configure Terraform

```bash
cd terraform

# Copy example config
cp terraform.tfvars.example terraform.tfvars

# Edit with your settings
nano terraform.tfvars
```

Update these values:
- `campaign_ids` - Your LinkedIn campaign IDs (comma-separated)
- `alert_email` - Email for alerts (optional)

---

## Step 5: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy
terraform apply
```

Type `yes` when prompted.

---

## Step 6: Verify Deployment

### Test Lambda manually

```bash
aws lambda invoke \
  --function-name linkedin-ads-automation-collector \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
```

### Check CloudWatch logs

```bash
aws logs tail /aws/lambda/linkedin-ads-automation-collector --follow
```

### Verify S3 data

```bash
aws s3 ls s3://your-company-linkedin-ads-automation/raw/analytics/ --recursive
```

---

## Step 7: Set Up Athena

### Create database

```bash
# Run in Athena console
aws athena start-query-execution \
  --query-string "$(cat athena/01_create_database.sql)" \
  --result-configuration "OutputLocation=s3://aws-athena-query-results-YOUR-ACCOUNT-ID/" \
  --region us-east-1
```

### Create tables

```bash
# Run each SQL file in Athena console
# 01_create_database.sql
# 02_create_raw_analytics_table.sql
# 03_create_views.sql
```

Or use AWS Console → Athena → Query Editor

---

## Step 8: Test Queries (After 24 Hours)

```sql
-- Check data is loading
SELECT COUNT(*) FROM linkedin_ads.raw_analytics;

-- View recent performance
SELECT * FROM linkedin_ads.daily_summary
ORDER BY report_date DESC
LIMIT 10;
```

---

## Step 9: Subscribe to Alerts

Check your email for SNS subscription confirmation and click the link.

---

## Step 10: Monitor

### CloudWatch Dashboard

```bash
# Get dashboard URL
terraform output dashboard_url
```

### Check metrics

```bash
aws cloudwatch get-metric-statistics \
  --namespace LinkedInAds/Collector \
  --metric-name TotalClicks \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

---

## Troubleshooting

### Lambda timeout

Increase timeout in `terraform/lambda_collector.tf`:
```hcl
timeout = 300  # 5 minutes
```

Then:
```bash
terraform apply
```

### LinkedIn API 401 Unauthorized

Token expired. Regenerate:
```bash
python3 scripts/oauth_setup.py
```

### No data in S3

1. Check Lambda logs for errors
2. Verify campaign_ids are correct
3. Test manual invocation
4. Check IAM permissions

---

## What Runs Automatically

- **Every 6 hours**: Lambda collector pulls data
- **Daily**: CloudWatch checks for anomalies
- **Continuous**: Metrics sent to CloudWatch

---

## Next Steps

1. **Wait 2 weeks** for data accumulation
2. **Review Athena queries** to understand performance
3. **Train ML models** (Phase 3)
4. **Deploy optimizer** (Phase 4)

---

## Costs

**Expected monthly cost**: $20-70

Monitor via:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-12-01,End=2024-12-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter file://cost-filter.json
```

---

## Support

- **Terraform errors**: Check `terraform/README.md`
- **Lambda errors**: Check CloudWatch Logs
- **API errors**: Check LinkedIn developer portal

---

## Rollback

```bash
cd terraform
terraform destroy
```

This will delete all resources except:
- Terraform state bucket
- S3 data (delete manually if needed)

---

## Success Criteria

✓ Lambda runs every 6 hours
✓ Data appears in S3
✓ Athena queries return results
✓ CloudWatch dashboard shows metrics
✓ No errors in logs

You're ready for Phase 2!

# LinkedIn Ads ML Automation - Template Setup Guide

This is a **template repository** for building an automated LinkedIn advertising optimization system using AWS and machine learning.

All sensitive information (company names, AWS account IDs, product-specific details) has been replaced with placeholders. Follow this guide to customize the template for your needs.

---

## 🚀 Quick Start

### Step 1: Find and Replace Placeholders

The following placeholders need to be replaced throughout the codebase:

| Placeholder | Replace With | Example |
|------------|--------------|---------|
| `YOUR_COMPANY_NAME` | Your company name | `Acme Corp` |
| `your-company` | Your company (lowercase, no spaces) | `acme-corp` |
| `YourCompanyName` | Your company (PascalCase) | `AcmeCorp` |
| `YOUR_ACCOUNT_ID` | Your AWS account ID | `123456789012` |
| `YOUR_PRODUCT_DESCRIPTION` | Brief description of your product | `SaaS platform for XYZ` |
| `YOUR_TARGET_AUDIENCE` | Your target customer profile | `CFOs, IT Directors in Fortune 500` |
| `YOUR_TARGET_MARKET` | Your geographic/industry market | `North America B2B SaaS` |
| `your-email@example.com` | Your notification email | `alerts@yourcompany.com` |

### Step 2: Find and Replace Using Command Line

From the repository root, run:

```bash
# Replace company name (update with your values)
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/YOUR_COMPANY_NAME/YourCompany/g' {} +

find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/your-company/yourcompany/g' {} +

# Replace AWS account ID
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/YOUR_ACCOUNT_ID/123456789012/g' {} +

# Replace product description
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/YOUR_PRODUCT_DESCRIPTION/Your product description/g' {} +

# Replace target audience
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/YOUR_TARGET_AUDIENCE/Your target audience/g' {} +

# Replace email
find . -type f \( -name "*.md" -o -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.json" \) \
  -exec sed -i '' 's/your-email@example.com/your-actual-email@company.com/g' {} +
```

**Note**: On Linux, remove the `''` after `-i`: `-i 's/...`

### Step 3: Configure Terraform Variables

Edit `terraform/terraform.tfvars`:

```hcl
# AWS Configuration
aws_region  = "us-east-1"  # Your preferred region
environment = "prod"

# Project Settings
project_name = "linkedin-ads-automation"

# LinkedIn Campaign IDs (add after campaigns are created)
campaign_ids = ""

# Schedules
collection_schedule = "rate(6 hours)"
optimizer_schedule  = "cron(0 9 * * ? *)"

# Alerting
alert_email = "your-email@yourcompany.com"
```

### Step 4: Update Terraform Backend

Edit `terraform/main.tf` to configure your Terraform state bucket:

```hcl
backend "s3" {
  bucket = "yourcompany-terraform-state"  # Create this bucket first
  key    = "linkedin-automation/terraform.tfstate"
  region = "us-east-1"  # Match your AWS region
}
```

### Step 5: LinkedIn API Setup

1. Follow the guide in `docs/LINKEDIN_API_SETUP.md`
2. Apply for LinkedIn Advertising API access
3. Wait for approval (5-10 business days)
4. Create `.secrets/linkedin_credentials.json`:

```json
{
  "client_id": "YOUR_LINKEDIN_CLIENT_ID",
  "client_secret": "YOUR_LINKEDIN_CLIENT_SECRET"
}
```

### Step 6: Get OAuth Token

Run the OAuth setup script:

```bash
python3 scripts/oauth_setup.py
```

This will:
- Open your browser for LinkedIn authorization
- Save the access token locally
- Upload credentials to AWS Secrets Manager

### Step 7: Deploy Infrastructure

```bash
# Create Terraform state bucket (if not exists)
aws s3 mb s3://yourcompany-terraform-state --region us-east-1

# Initialize and deploy
cd terraform
terraform init
terraform plan
terraform apply
```

### Step 8: Verify Deployment

```bash
# Test Lambda collector
aws lambda invoke \
  --function-name linkedin-ads-automation-collector \
  --region us-east-1 \
  /tmp/response.json

# Check logs
aws logs tail /aws/lambda/linkedin-ads-automation-collector --follow

# View collected data
aws s3 ls s3://yourcompany-linkedin-ads-automation/raw/analytics/ --recursive
```

---

## 📁 Repository Structure

```
linkedin-automation/
├── README.md                          # Main project documentation
├── TEMPLATE_SETUP.md                  # This file - setup instructions
├── QUICK_START.md                     # Fast deployment guide
├── DEPLOYMENT.md                      # Detailed deployment steps
│
├── lambda/                            # Lambda Functions
│   ├── collector/                     # Data collection from LinkedIn API
│   ├── optimizer/                     # ML-powered optimization engine
│   ├── copy_generator/                # AI ad copy generation
│   ├── data_processor/                # ML training data prep
│   └── token_rotator/                 # OAuth token refresh
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf                       # Provider & backend config
│   ├── variables.tf                  # Input variables
│   ├── terraform.tfvars.example      # Example configuration
│   ├── s3.tf                         # S3 buckets
│   ├── lambda_collector.tf           # Lambda resources
│   ├── eventbridge.tf                # Schedulers
│   ├── secrets.tf                    # Secrets Manager
│   └── monitoring.tf                 # CloudWatch alarms
│
├── athena/                           # SQL Analytics
│   ├── 01_create_database.sql
│   ├── 02_create_raw_analytics_table.sql
│   ├── 03_create_views.sql
│   └── 04_sample_queries.sql
│
├── sagemaker/                        # ML Model Training
│   ├── train_creative_scorer.py      # CTR prediction model
│   ├── train_bid_optimizer.py        # Bid optimization model
│   └── requirements.txt
│
├── scripts/                          # Utility Scripts
│   ├── oauth_setup.py               # OAuth token generation
│   └── README.md
│
└── docs/                             # Documentation
    ├── LINKEDIN_API_SETUP.md
    ├── AWS_ARCHITECTURE.md
    └── IMPLEMENTATION_GUIDE.md
```

---

## 🔧 Customization Points

### 1. Optimization Thresholds

Edit `lambda/optimizer/handler.py`:

```python
# Adjust these based on your goals
MIN_CTR_THRESHOLD = 1.0           # Pause creatives below this CTR
TOP_PERFORMER_THRESHOLD = 3.0     # Scale creatives above this CTR
MAX_CPC = 8.0                     # Pause if cost per click exceeds this
MIN_SAMPLE_SIZE = 100             # Minimum clicks before taking action
```

### 2. Collection Frequency

Edit `terraform/variables.tf` or `terraform.tfvars`:

```hcl
collection_schedule = "rate(3 hours)"  # Collect every 3 hours instead of 6
optimizer_schedule  = "cron(0 6 * * ? *)"  # Run at 6 AM UTC instead of 9 AM
```

### 3. AWS Region

Change the region in:
- `terraform/terraform.tfvars`: `aws_region = "us-west-2"`
- `terraform/main.tf`: Backend region
- `scripts/oauth_setup.py`: Line 206

### 4. Ad Copy Generation

Customize the AI prompts in `lambda/copy_generator/handler.py`:
- Line 157-204: Adjust the Claude API prompt for your brand voice
- Line 302-307: Modify default product/audience descriptions

### 5. Metrics and Alerts

Add custom CloudWatch metrics in `lambda/collector/handler.py`:
- Line 151-171: `send_cloudwatch_metrics()` function
- Add your own business-specific metrics

---

## 💰 Cost Estimate

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| Lambda | ~$1 | Based on 120 invocations/month |
| S3 | ~$1-5 | Depends on data volume |
| Athena | ~$5-10 | Based on query frequency |
| Secrets Manager | ~$0.40 | Per secret |
| CloudWatch | ~$1-2 | Logs and metrics |
| SageMaker (optional) | ~$10-50 | If using ML endpoints |
| **Total** | **~$20-70/month** | Scales with usage |

**Infrastructure cost**: ~2-5% of ad spend for most use cases

---

## 🔐 Security Best Practices

1. **Never commit secrets**
   - `.secrets/` is in `.gitignore`
   - Use AWS Secrets Manager for credentials
   - Rotate OAuth tokens every 60 days

2. **IAM Least Privilege**
   - Lambda roles have minimal permissions
   - Review `terraform/lambda_collector.tf` IAM policies

3. **S3 Encryption**
   - All buckets use AES-256 encryption
   - Public access is blocked

4. **VPC Endpoints** (Optional for production)
   - Add VPC endpoints for Lambda to access AWS services privately
   - See `docs/AWS_ARCHITECTURE.md` for setup

---

## 📊 Monitoring and Alerts

### CloudWatch Dashboards

View metrics at:
```
https://console.aws.amazon.com/cloudwatch/home?region=YOUR_REGION#dashboards:
```

### SNS Alerts

Subscribe to notifications:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:YOUR_REGION:YOUR_ACCOUNT_ID:linkedin-ads-automation-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### Log Analysis

```bash
# View recent errors
aws logs filter-pattern /aws/lambda/linkedin-ads-automation-collector \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000

# Count successful runs
aws logs filter-pattern /aws/lambda/linkedin-ads-automation-collector \
  --filter-pattern "Collection Complete" \
  --start-time $(date -u -d '24 hours ago' +%s)000
```

---

## 🎯 What This Template Provides

✅ **Complete Infrastructure**
- Terraform configs for all AWS resources
- Production-ready security settings
- Automated deployment scripts

✅ **Data Collection**
- LinkedIn Ads API integration
- Automatic scheduling (every 6 hours)
- Structured storage in S3

✅ **Analytics**
- Athena database and tables
- Pre-built SQL queries
- Performance analysis views

✅ **ML Optimization**
- Creative performance scoring
- Bid optimization algorithms
- Automated decision making

✅ **AI Copy Generation**
- Claude API integration
- Pattern-based copywriting
- A/B testing variations

✅ **Monitoring**
- CloudWatch dashboards
- Email/SMS alerts
- Detailed logging

---

## 🚨 Troubleshooting

### LinkedIn API 401 Unauthorized
- Token expired → Run `python3 scripts/oauth_setup.py`
- Wrong scopes → Check LinkedIn Developer Portal permissions

### Lambda Timeout
- Increase timeout in `terraform/lambda_collector.tf`
- Check CloudWatch logs for bottlenecks

### No Data in S3
- Verify campaign IDs in Lambda environment variables
- Check Lambda execution role has S3 write permissions
- Review CloudWatch logs for API errors

### Athena Query Failures
- Ensure S3 bucket exists and has data
- Check partitions are created correctly
- Verify IAM permissions for Athena

---

## 📚 Additional Resources

- **LinkedIn Marketing API Docs**: https://docs.microsoft.com/en-us/linkedin/marketing/
- **AWS Lambda Best Practices**: https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **Claude API Docs**: https://docs.anthropic.com/

---

## 🤝 Contributing

Found a bug or have an improvement?

1. Fork this repository
2. Create a feature branch
3. Submit a pull request

---

## 📝 License

This template is provided as-is under the MIT License. See LICENSE file for details.

---

## ✨ What's Next?

After deployment:

1. **Week 1-2**: Let data accumulate (30+ days recommended)
2. **Week 3**: Train ML models with `sagemaker/train_*.py`
3. **Week 4**: Enable full automation with optimizer Lambda
4. **Monitor**: Review performance improvements weekly

Expected results after 4 weeks:
- CTR improvement: +20-40%
- CPC reduction: -15-25%
- Time savings: ~90% reduction in manual work

---

**Questions?** Check the docs/ folder or open an issue!

**Happy automating!** 🚀

# Complete Replication Guide

**How to replicate this LinkedIn Ads automation system for any company**

This guide provides step-by-step instructions to deploy the entire LinkedIn Ads automation pipeline from scratch. Follow this if you're setting up the system for a new company or in a new AWS account.

**Time to Complete**: 4-6 hours (excluding LinkedIn API approval wait time)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Company Information Gathering](#company-information-gathering)
3. [LinkedIn Developer Setup](#linkedin-developer-setup)
4. [AWS Account Preparation](#aws-account-preparation)
5. [Code Repository Setup](#code-repository-setup)
6. [Infrastructure Deployment](#infrastructure-deployment)
7. [LinkedIn OAuth Configuration](#linkedin-oauth-configuration)
8. [Campaign Setup](#campaign-setup)
9. [Testing & Verification](#testing--verification)
10. [Monitoring Setup](#monitoring-setup)
11. [Data Analytics Configuration](#data-analytics-configuration)
12. [Customization Guide](#customization-guide)
13. [Troubleshooting](#troubleshooting)
14. [Maintenance & Updates](#maintenance--updates)

---

## Prerequisites

### Required Access & Accounts

- [ ] LinkedIn Company Page (admin access required)
- [ ] AWS Account with billing enabled
- [ ] AWS IAM user with AdministratorAccess or equivalent permissions
- [ ] GitHub account (or alternative git hosting)
- [ ] Email address for alerts
- [ ] Credit card for LinkedIn ad spend (~$1,667/month minimum recommended)

### Required Tools

Install on your local machine:

```bash
# Check if tools are installed
aws --version          # AWS CLI (install: https://aws.amazon.com/cli/)
python3 --version      # Python 3.11+ (install: https://python.org)
git --version          # Git (install: https://git-scm.com)
pip3 --version         # pip (usually comes with Python)

# Optional but recommended
terraform --version    # Terraform (install: https://terraform.io)
jq --version          # jq for JSON parsing (install: brew install jq)
```

### Technical Knowledge Requirements

**Minimum Required**:
- Basic command line usage
- Understanding of environment variables
- Ability to copy/paste commands accurately

**Helpful But Not Required**:
- AWS fundamentals (S3, Lambda, IAM)
- Python basics
- SQL query writing
- Infrastructure as Code concepts

---

## Company Information Gathering

Before starting, collect this information about the target company:

### Business Details

```yaml
Company Legal Name: _______________________________
Company Website: __________________________________
LinkedIn Company Page URL: ________________________
Privacy Policy URL: _______________________________
Industry/Sector: __________________________________
Target Audience: __________________________________
Annual Ad Budget: $_______________________________
```

### Contact Information

```yaml
Primary Contact Name: _____________________________
Primary Contact Email: ____________________________
Alert Email(s): ___________________________________
Phone Number (for alerts): ________________________
```

### Technical Details

```yaml
AWS Account ID: ___________________________________
Preferred AWS Region: ______________________________
  (us-east-1 recommended for lowest costs)

GitHub Organization: _______________________________
Repository Name: ___________________________________
```

### Marketing Information

```yaml
Target Job Titles: ________________________________
Target Industries: ________________________________
Target Geographic Regions: ________________________
Typical CTR Benchmark: ____________________________
Maximum CPC: $____________________________________
Daily Budget Per Campaign: $________________________
```

**Save this information** - you'll need it throughout the setup process.

---

## LinkedIn Developer Setup

### Step 1: Create LinkedIn Developer Application

**Duration**: 15 minutes

1. **Navigate to LinkedIn Developers**
   - URL: https://www.linkedin.com/developers/apps
   - Click **"Create app"**

2. **Fill Application Details**

   ```yaml
   App name: [COMPANY_NAME] Ads Automation
   LinkedIn Page: [Select company page from dropdown]
   Privacy policy URL: https://[COMPANY_WEBSITE]/privacy
   App logo: [Upload 300x300px company logo]
   Legal agreement: [Check "I have read and agree..."]
   ```

3. **Click "Create app"** and note the Client ID

4. **Navigate to "Auth" tab** and note:
   - Client ID
   - Client Secret (click "Show" to reveal)

5. **Add OAuth 2.0 Redirect URLs**
   - Click "Add redirect URL"
   - Add: `http://localhost:8000/callback`
   - Click "Update"

### Step 2: Request LinkedIn Advertising API Access

**Duration**: 20 minutes (application), 5-10 days (approval wait)

1. **Go to Products Tab**
   - Find "Advertising API (Development Tier)"
   - Click "Request access"

2. **Complete Application Form**

   **Section: Clients**

   ```yaml
   Where are most of your customers based?
   → [Select primary region: North America / Europe / Asia / Other]

   How many clients leverage the product?
   → N/A (Direct Customer)

   What % of your clients are B2B?
   → N/A (Direct Customer)

   What category best describes the majority of your customers?
   → Direct Customers

   What industries are most common among your customers?
   → [List target industries, e.g., "Real Estate Investment, Commercial Real Estate, Property Technology"]
   ```

   **Section: Business**

   ```yaml
   Primary use case:
   → Direct Advertiser: to manage only owned and operated LinkedIn activity/data streams.

   Annual digital ad spend managed:
   → [Enter annual budget, e.g., 20000]

   Tell us about your business and the product:
   → [COMPANY_NAME] is a [INDUSTRY] company that provides [VALUE_PROPOSITION].
      We aggregate [DATA_SOURCES] to help [TARGET_CUSTOMERS] with [USE_CASES].

      Our platform serves [TARGET_AUDIENCE] seeking [SOLUTIONS] across [GEOGRAPHY].
      We need API access to programmatically manage our LinkedIn advertising campaigns
      that target [TARGET_PROFESSIONAL_AUDIENCE].

   Intended use case (select both):
   ☑ Campaign Management
   ☑ Reporting and ROI

   What do you plan to build with the APIs?
   → We will build an automated campaign optimization system that:

      1. Dynamically adjusts ad creative and targeting based on performance data
         (CTR, CPC, conversion rates)
      2. Automatically pauses underperforming ads and scales winning variations
      3. Optimizes bid strategies based on time-of-day and audience engagement patterns
      4. Pulls real-time analytics to measure ROI and cost-per-acquisition
      5. A/B tests ad copy variations to identify high-performing messaging for
         different [TARGET_AUDIENCE] segments

      This automation will allow us to efficiently reach our target audience while
      maintaining cost-effective customer acquisition.

   Platform partnerships:
   ☑ Other: "None currently - direct advertising only"

   Other API Integrations already built:
   → [Leave all unchecked - this is your first LinkedIn integration]
   ```

3. **Submit Application**

4. **Save Credentials Temporarily**

   Create a secure note with:
   ```yaml
   Client ID: 78xxxxxxxxxxxxx
   Client Secret: xxxxxxxxxxxxxxxxxx
   Application Status: Pending
   Submitted Date: [DATE]
   ```

### Step 3: Request Conversions API Access (Optional)

**Duration**: 10 minutes

*Only complete if you plan to track website conversions*

1. **Go to Products Tab**
   - Find "Conversions API (Standard Tier)"
   - Click "Request access"

2. **Complete Form**

   ```yaml
   Business type:
   → Direct Advertiser: direct build to manage own LinkedIn conversions data streams

   Use cases (select these):
   ☑ Utilize Conversions API and Insight Tag together to measure and optimize campaign performance
   ☑ To track and measure both online and offline events across customer journey
   ☑ To provide alternative mechanism to track conversion events for LinkedIn ads

   Details about use case:
   → [COMPANY_NAME] is building an automated ad optimization system. We need
      Conversions API to:

      1. Track conversion events (sign-ups, demo requests, purchases) from LinkedIn
         ads to our website, enabling ML models to optimize based on actual business outcomes
      2. Measure both online conversions (website actions) and offline conversions
         (sales calls, closed deals) across the full customer journey
      3. Supplement LinkedIn Insight Tag with server-side conversion tracking for
         more reliable data collection

      This conversion data feeds into our automated optimization engine to pause
      low-converting ads, scale high-converting campaigns, and adjust bids based
      on conversion probability.

   Compliance team responsible for privacy?
   → Yes

   Platform partnerships:
   ☑ Other: "None currently - direct advertising only"

   Other API Integrations:
   → [Leave all unchecked]
   ```

3. **Submit Application**

### Step 4: Wait for Approval

**Duration**: 5-10 business days

You'll receive an email at the account associated with your LinkedIn profile when approved.

**While waiting**, proceed with AWS setup and code deployment.

---

## AWS Account Preparation

### Step 1: Configure AWS CLI

**Duration**: 10 minutes

1. **Install AWS CLI** (if not already installed)
   ```bash
   # macOS
   brew install awscli

   # Windows
   # Download from: https://aws.amazon.com/cli/

   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **Get AWS Credentials**

   If you don't have credentials:
   - Log into AWS Console
   - Go to IAM → Users → [Your Username]
   - Security Credentials tab
   - "Create access key" → "Command Line Interface"
   - Download credentials CSV

3. **Configure AWS CLI**
   ```bash
   aws configure
   ```

   Enter:
   ```yaml
   AWS Access Key ID: [Your access key]
   AWS Secret Access Key: [Your secret key]
   Default region name: us-east-2
     (or us-east-1 for lowest costs)
   Default output format: json
   ```

4. **Verify Configuration**
   ```bash
   aws sts get-caller-identity
   ```

   Should return your account ID and user ARN.

### Step 2: Set Up Cost Alerts

**Duration**: 5 minutes

Prevent surprise bills by setting up budget alerts:

```bash
# Create a budget (replace EMAIL and AMOUNT)
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://<(cat <<'EOF'
{
  "BudgetName": "LinkedIn-Ads-Automation-Monthly",
  "BudgetLimit": {
    "Amount": "100",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
EOF
)
```

Or set up via AWS Console:
- AWS Console → Billing → Budgets
- Create budget → Cost budget
- Set monthly limit (e.g., $100 for infrastructure)
- Add email alerts at 80% and 100%

### Step 3: Create IAM User for Automation (Optional but Recommended)

**Duration**: 10 minutes

Create a dedicated IAM user instead of using root credentials:

```bash
# Create user
aws iam create-user --user-name linkedin-automation-user

# Attach policy
aws iam attach-user-policy \
  --user-name linkedin-automation-user \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Create access keys
aws iam create-access-key --user-name linkedin-automation-user
```

Save the AccessKeyId and SecretAccessKey, then configure a new AWS CLI profile:

```bash
aws configure --profile linkedin-automation
```

For all subsequent commands, add `--profile linkedin-automation` or set:
```bash
export AWS_PROFILE=linkedin-automation
```

---

## Code Repository Setup

### Step 1: Fork or Clone Repository

**Duration**: 5 minutes

**Option A: Fork the original repository** (Recommended)

1. Go to: https://github.com/jgutt-png/linkedin-automation
2. Click "Fork" → Create fork
3. Clone your fork:
   ```bash
   git clone https://github.com/[YOUR_USERNAME]/linkedin-automation.git
   cd linkedin-automation
   ```

**Option B: Start fresh with the code**

1. Create new repository on GitHub
   ```bash
   # On GitHub: New Repository → "linkedin-automation-[COMPANY_NAME]"
   ```

2. Clone this repository locally:
   ```bash
   git clone https://github.com/jgutt-png/linkedin-automation.git temp-linkedin
   cd temp-linkedin

   # Copy code to new repo
   git remote remove origin
   git remote add origin https://github.com/[YOUR_ORG]/linkedin-automation-[COMPANY_NAME].git
   git push -u origin main

   cd ..
   mv temp-linkedin linkedin-automation-[COMPANY_NAME]
   cd linkedin-automation-[COMPANY_NAME]
   ```

### Step 2: Customize Configuration Files

**Duration**: 10 minutes

1. **Update Project Name Variables**

   Edit `terraform/variables.tf`:
   ```hcl
   variable "project_name" {
     description = "Project name for resource naming"
     type        = string
     default     = "linkedin-ads-[COMPANY_NAME_LOWERCASE]"  # e.g., linkedin-ads-acme
   }
   ```

2. **Update S3 Bucket Names**

   S3 bucket names must be globally unique. Edit configuration:

   ```bash
   # Choose unique bucket names
   COMPANY_SHORT="acme"  # Replace with your company
   TERRAFORM_BUCKET="${COMPANY_SHORT}-terraform-state"
   DATA_BUCKET="${COMPANY_SHORT}-linkedin-ads-automation"
   ```

   Update in these files:
   - `terraform/main.tf` (backend S3 bucket)
   - `terraform/s3.tf` (data bucket name)
   - All documentation references

3. **Update Documentation**

   Replace "YOUR_COMPANY_NAME" with your company name in:
   - `README.md`
   - `docs/*.md`
   - `QUICK_START.md`
   - `DEPLOYMENT.md`

   Use find/replace:
   ```bash
   find . -type f -name "*.md" -exec sed -i '' 's/YOUR_COMPANY_NAME/[YOUR_COMPANY_NAME]/g' {} +
   find . -type f -name "*.md" -exec sed -i '' 's/your-company/[your-company-lowercase]/g' {} +
   ```

4. **Commit Changes**
   ```bash
   git add -A
   git commit -m "Customize for [COMPANY_NAME]"
   git push origin main
   ```

### Step 3: Configure Local Environment

**Duration**: 5 minutes

1. **Create secrets directory**
   ```bash
   mkdir -p .secrets
   chmod 700 .secrets
   ```

2. **Create .env file** (optional, for easier access)
   ```bash
   cat > .env <<EOF
   AWS_REGION=us-east-2
   AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   PROJECT_NAME=linkedin-ads-[COMPANY_SHORT]
   COMPANY_NAME=[COMPANY_NAME]
   EOF
   ```

3. **Source environment** (add to `.bashrc` or `.zshrc`)
   ```bash
   [ -f ~/linkedin-automation/.env ] && source ~/linkedin-automation/.env
   ```

---

## Infrastructure Deployment

### Step 1: Create S3 Buckets

**Duration**: 5 minutes

```bash
# Set variables (customize these)
COMPANY_SHORT="acme"
AWS_REGION="us-east-2"

TERRAFORM_BUCKET="${COMPANY_SHORT}-terraform-state"
DATA_BUCKET="${COMPANY_SHORT}-linkedin-ads-automation"

# Create Terraform state bucket
aws s3 mb s3://${TERRAFORM_BUCKET} --region ${AWS_REGION}

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ${TERRAFORM_BUCKET} \
  --versioning-configuration Status=Enabled

# Create data bucket
aws s3 mb s3://${DATA_BUCKET} --region ${AWS_REGION}

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ${DATA_BUCKET} \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket ${DATA_BUCKET} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket ${DATA_BUCKET} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "✓ S3 buckets created successfully"
```

### Step 2: Create Secrets Manager Secret

**Duration**: 2 minutes

```bash
# Set variables
SECRET_NAME="${COMPANY_SHORT}-linkedin-credentials"

# Create secret with placeholder values
aws secretsmanager create-secret \
  --name ${SECRET_NAME} \
  --description "LinkedIn Ads API OAuth credentials for ${COMPANY_SHORT}" \
  --secret-string '{
    "client_id": "PLACEHOLDER_UPDATE_AFTER_LINKEDIN_APPROVAL",
    "client_secret": "PLACEHOLDER_UPDATE_AFTER_LINKEDIN_APPROVAL",
    "access_token": "PLACEHOLDER_UPDATE_AFTER_OAUTH_FLOW"
  }' \
  --region ${AWS_REGION}

echo "✓ Secrets Manager secret created: ${SECRET_NAME}"
```

### Step 3: Build Lambda Deployment Package

**Duration**: 5 minutes

```bash
cd lambda/collector

# Install dependencies
pip3 install -r requirements.txt -t . --quiet

# Create deployment package
cd ..
zip -r ../collector.zip collector/ -x "*.pyc" -x "*__pycache__*" -x ".DS_Store"

cd ..

# Verify package size
ls -lh collector.zip
# Should be ~13-14 MB

echo "✓ Lambda deployment package created"
```

### Step 4: Create IAM Role for Lambda

**Duration**: 5 minutes

```bash
# Set variables
ROLE_NAME="${COMPANY_SHORT}-linkedin-collector-role"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create trust policy
cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
  --role-name ${ROLE_NAME} \
  --assume-role-policy-document file:///tmp/trust-policy.json \
  --description "IAM role for LinkedIn Ads data collector Lambda"

# Create permissions policy
cat > /tmp/role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${DATA_BUCKET}",
        "arn:aws:s3:::${DATA_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:${AWS_REGION}:${ACCOUNT_ID}:secret:${SECRET_NAME}-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/aws/lambda/*"
    },
    {
      "Effect": "Allow",
      "Action": ["cloudwatch:PutMetricData"],
      "Resource": "*"
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
  --role-name ${ROLE_NAME} \
  --policy-name ${COMPANY_SHORT}-linkedin-collector-policy \
  --policy-document file:///tmp/role-policy.json

# Wait for role to propagate
sleep 10

echo "✓ IAM role created: ${ROLE_NAME}"
```

### Step 5: Create Lambda Function

**Duration**: 3 minutes

```bash
# Set variables
FUNCTION_NAME="${COMPANY_SHORT}-linkedin-collector"

# Create CloudWatch log group
aws logs create-log-group \
  --log-group-name /aws/lambda/${FUNCTION_NAME} \
  --region ${AWS_REGION}

aws logs put-retention-policy \
  --log-group-name /aws/lambda/${FUNCTION_NAME} \
  --retention-in-days 14 \
  --region ${AWS_REGION}

# Create Lambda function
aws lambda create-function \
  --function-name ${FUNCTION_NAME} \
  --runtime python3.11 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME} \
  --handler handler.lambda_handler \
  --zip-file fileb://collector.zip \
  --timeout 120 \
  --memory-size 512 \
  --environment "Variables={
    BUCKET_NAME=${DATA_BUCKET},
    CAMPAIGN_IDS=,
    SECRET_NAME=${SECRET_NAME}
  }" \
  --region ${AWS_REGION}

echo "✓ Lambda function created: ${FUNCTION_NAME}"
```

### Step 6: Set Up EventBridge Schedule

**Duration**: 3 minutes

```bash
# Set variables
RULE_NAME="${COMPANY_SHORT}-linkedin-collector-schedule"

# Create EventBridge rule
aws events put-rule \
  --name ${RULE_NAME} \
  --description "Trigger LinkedIn data collection every 6 hours" \
  --schedule-expression "rate(6 hours)" \
  --region ${AWS_REGION}

# Add Lambda as target
aws events put-targets \
  --rule ${RULE_NAME} \
  --targets "Id=1,Arn=arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}" \
  --region ${AWS_REGION}

# Grant EventBridge permission to invoke Lambda
aws lambda add-permission \
  --function-name ${FUNCTION_NAME} \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/${RULE_NAME} \
  --region ${AWS_REGION}

echo "✓ EventBridge schedule created: ${RULE_NAME}"
```

### Step 7: Create SNS Topic for Alerts

**Duration**: 2 minutes

```bash
# Set variables
TOPIC_NAME="${COMPANY_SHORT}-linkedin-alerts"

# Create SNS topic
SNS_ARN=$(aws sns create-topic \
  --name ${TOPIC_NAME} \
  --region ${AWS_REGION} \
  --query 'TopicArn' \
  --output text)

echo "✓ SNS topic created: ${SNS_ARN}"

# Subscribe email (optional - requires confirmation)
# ALERT_EMAIL="alerts@yourcompany.com"
# aws sns subscribe \
#   --topic-arn ${SNS_ARN} \
#   --protocol email \
#   --notification-endpoint ${ALERT_EMAIL} \
#   --region ${AWS_REGION}
```

### Step 8: Create CloudWatch Alarms

**Duration**: 5 minutes

```bash
# Alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name "${COMPANY_SHORT}-linkedin-collector-errors" \
  --alarm-description "Alert when LinkedIn data collector fails" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 3600 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=${FUNCTION_NAME} \
  --alarm-actions ${SNS_ARN} \
  --region ${AWS_REGION}

# Alarm for high daily spend
aws cloudwatch put-metric-alarm \
  --alarm-name "${COMPANY_SHORT}-linkedin-high-spend" \
  --alarm-description "Alert when daily ad spend exceeds threshold" \
  --metric-name TotalCost \
  --namespace LinkedInAds/Collector \
  --statistic Sum \
  --period 86400 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ${SNS_ARN} \
  --region ${AWS_REGION}

# Alarm for low CTR
aws cloudwatch put-metric-alarm \
  --alarm-name "${COMPANY_SHORT}-linkedin-low-ctr" \
  --alarm-description "Alert when CTR drops below 1%" \
  --metric-name CTR \
  --namespace LinkedInAds/Collector \
  --statistic Average \
  --period 21600 \
  --threshold 1.0 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions ${SNS_ARN} \
  --region ${AWS_REGION}

echo "✓ CloudWatch alarms created"
```

### Step 9: Verify Deployment

**Duration**: 2 minutes

```bash
echo "=== Deployment Verification ==="
echo ""

echo "S3 Buckets:"
aws s3 ls | grep ${COMPANY_SHORT}
echo ""

echo "Lambda Functions:"
aws lambda list-functions \
  --region ${AWS_REGION} \
  --query "Functions[?contains(FunctionName, '${COMPANY_SHORT}')].{Name:FunctionName,Runtime:Runtime}" \
  --output table
echo ""

echo "Secrets Manager:"
aws secretsmanager list-secrets \
  --region ${AWS_REGION} \
  --query "SecretList[?contains(Name, '${COMPANY_SHORT}')].Name" \
  --output table
echo ""

echo "EventBridge Rules:"
aws events list-rules \
  --region ${AWS_REGION} \
  --query "Rules[?contains(Name, '${COMPANY_SHORT}')].{Name:Name,State:State,Schedule:ScheduleExpression}" \
  --output table
echo ""

echo "✓ All infrastructure deployed successfully!"
```

### Step 10: Save Deployment Details

**Duration**: 3 minutes

```bash
# Create deployment summary
cat > DEPLOYMENT_SUMMARY_$(date +%Y%m%d).txt <<EOF
=== LinkedIn Ads Automation Deployment ===

Company: ${COMPANY_NAME}
Deployed: $(date)
AWS Account: ${ACCOUNT_ID}
AWS Region: ${AWS_REGION}

=== Resources Created ===

S3 Buckets:
- Data: s3://${DATA_BUCKET}
- Terraform State: s3://${TERRAFORM_BUCKET}

Lambda Function:
- Name: ${FUNCTION_NAME}
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 120 seconds

IAM Role:
- Name: ${ROLE_NAME}
- ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}

Secrets Manager:
- Name: ${SECRET_NAME}
- ARN: arn:aws:secretsmanager:${AWS_REGION}:${ACCOUNT_ID}:secret:${SECRET_NAME}

EventBridge Schedule:
- Name: ${RULE_NAME}
- Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)

SNS Topic:
- Name: ${TOPIC_NAME}
- ARN: ${SNS_ARN}

CloudWatch Alarms:
- ${COMPANY_SHORT}-linkedin-collector-errors
- ${COMPANY_SHORT}-linkedin-high-spend
- ${COMPANY_SHORT}-linkedin-low-ctr

=== Next Steps ===

1. Wait for LinkedIn API approval (5-10 days)
2. Run OAuth flow: python3 scripts/oauth_setup.py
3. Update Lambda environment with campaign IDs
4. Test data collection
5. Monitor CloudWatch logs

=== Important URLs ===

Lambda Console:
https://console.aws.amazon.com/lambda/home?region=${AWS_REGION}#/functions/${FUNCTION_NAME}

CloudWatch Logs:
https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group/\$252Faws\$252Flambda\$252F${FUNCTION_NAME}

S3 Bucket:
https://s3.console.aws.amazon.com/s3/buckets/${DATA_BUCKET}

EventBridge Rules:
https://console.aws.amazon.com/events/home?region=${AWS_REGION}#/eventbus/default/rules/${RULE_NAME}

EOF

cat DEPLOYMENT_SUMMARY_$(date +%Y%m%d).txt

echo ""
echo "✓ Deployment summary saved to: DEPLOYMENT_SUMMARY_$(date +%Y%m%d).txt"
```

---

## LinkedIn OAuth Configuration

### When: After LinkedIn approves your API application

**Duration**: 10 minutes

### Step 1: Update Secrets Manager

Once LinkedIn approves your application:

```bash
# Create credentials file locally
cat > .secrets/linkedin_credentials.json <<EOF
{
  "client_id": "YOUR_CLIENT_ID_FROM_LINKEDIN",
  "client_secret": "YOUR_CLIENT_SECRET_FROM_LINKEDIN"
}
EOF

# Secure the file
chmod 600 .secrets/linkedin_credentials.json
```

### Step 2: Run OAuth Flow

```bash
# Install required Python package
pip3 install requests

# Run OAuth setup script
python3 scripts/oauth_setup.py
```

**What happens**:
1. Opens browser to LinkedIn authorization page
2. You grant permissions
3. Script exchanges auth code for access token
4. Token saved locally and uploaded to AWS Secrets Manager

**Troubleshooting**:

If browser doesn't open:
```bash
# Manually copy the URL from terminal and open in browser
```

If you get "redirect_uri_mismatch" error:
```bash
# Ensure http://localhost:8000/callback is added in LinkedIn app settings
# Settings → Auth → OAuth 2.0 settings → Redirect URLs
```

### Step 3: Verify Token

```bash
# Get the access token
ACCESS_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id ${SECRET_NAME} \
  --region ${AWS_REGION} \
  --query SecretString \
  --output text | jq -r '.access_token')

# Test LinkedIn API call
curl -X GET 'https://api.linkedin.com/rest/adAccounts?q=search' \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H 'X-Restli-Protocol-Version: 2.0.0' \
  -H 'LinkedIn-Version: 202411'

# Should return JSON with your ad accounts
```

If successful, you'll see your LinkedIn ad account details!

---

## Campaign Setup

### Step 1: Create LinkedIn Ad Campaigns

**Duration**: 30 minutes (manual, in LinkedIn Campaign Manager)

1. **Log into LinkedIn Campaign Manager**
   - URL: https://www.linkedin.com/campaignmanager

2. **Create Campaign Group**
   - Click "Create" → "Campaign Group"
   - Name: "[COMPANY_NAME] - Q4 2024"
   - Objective: Choose based on goal (e.g., "Website visits", "Lead generation")

3. **Create Campaign**
   - Click "Create campaign"
   - Name: "[TARGET_AUDIENCE] - [GEO] - [OBJECTIVE]"
     Example: "Real Estate Investors - US - Lead Gen"

   **Targeting**:
   - Locations: [Target regions]
   - Job titles: [Relevant titles]
   - Industries: [Target industries]
   - Company size: [If applicable]

   **Budget**:
   - Daily budget: $50-100 (adjust based on total budget)
   - Bidding: "Maximum delivery" or "Cost cap"
   - Bid amount: $5-8 CPC (adjust based on industry)

   **Ad Format**: Single image ad (easiest to start)

4. **Note Campaign ID**
   - After creating campaign, look at URL:
     `https://www.linkedin.com/campaignmanager/accounts/[ACCOUNT_ID]/campaigns/[CAMPAIGN_ID]`
   - Copy the CAMPAIGN_ID number

5. **Repeat for Additional Campaigns**
   - Create 2-3 campaigns targeting different audiences
   - Note all campaign IDs

### Step 2: Update Lambda Configuration

```bash
# Set campaign IDs (comma-separated, no spaces)
CAMPAIGN_IDS="123456789,987654321,456789123"

# Update Lambda environment
aws lambda update-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --environment "Variables={
    BUCKET_NAME=${DATA_BUCKET},
    CAMPAIGN_IDS=${CAMPAIGN_IDS},
    SECRET_NAME=${SECRET_NAME}
  }" \
  --region ${AWS_REGION}

echo "✓ Lambda updated with campaign IDs: ${CAMPAIGN_IDS}"
```

---

## Testing & Verification

### Step 1: Manual Lambda Test

**Duration**: 5 minutes

```bash
# Invoke Lambda manually
aws lambda invoke \
  --function-name ${FUNCTION_NAME} \
  --region ${AWS_REGION} \
  /tmp/response.json

# View response
cat /tmp/response.json | jq .

# Expected output:
# {
#   "statusCode": 200,
#   "body": "{...successful data collection...}"
# }
```

### Step 2: Check CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/${FUNCTION_NAME} \
  --since 5m \
  --region ${AWS_REGION}

# Look for:
# ✓ Success emojis (✓)
# Campaign IDs being processed
# Data saved to S3
# No error messages (❌)
```

### Step 3: Verify S3 Data

```bash
# List S3 objects
aws s3 ls s3://${DATA_BUCKET}/raw/analytics/ --recursive

# Expected output:
# 2024-12-03 12:00:00  15234 raw/analytics/2024/12/03/campaign_123456789_1701598800.json

# Download and inspect one file
aws s3 cp s3://${DATA_BUCKET}/raw/analytics/2024/12/03/campaign_123456789_1701598800.json /tmp/sample.json

cat /tmp/sample.json | jq .
```

### Step 4: Verify CloudWatch Metrics

```bash
# Check for custom metrics
aws cloudwatch list-metrics \
  --namespace LinkedInAds/Collector \
  --region ${AWS_REGION}

# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace LinkedInAds/Collector \
  --metric-name TotalClicks \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region ${AWS_REGION}
```

### Step 5: Test EventBridge Schedule

```bash
# Check next execution time
aws events describe-rule \
  --name ${RULE_NAME} \
  --region ${AWS_REGION} \
  --query 'ScheduleExpression'

# Expected: "rate(6 hours)"

# Wait 6 hours or manually trigger
aws lambda invoke \
  --function-name ${FUNCTION_NAME} \
  --region ${AWS_REGION} \
  /tmp/test2.json
```

---

## Monitoring Setup

### Step 1: Subscribe to Alerts

```bash
# Add email subscription to SNS topic
ALERT_EMAIL="alerts@yourcompany.com"

aws sns subscribe \
  --topic-arn ${SNS_ARN} \
  --protocol email \
  --notification-endpoint ${ALERT_EMAIL} \
  --region ${AWS_REGION}

# Check inbox for confirmation email
# Click "Confirm subscription" link
```

### Step 2: Create CloudWatch Dashboard

```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "${COMPANY_SHORT}-linkedin-ads" \
  --dashboard-body file://<(cat <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["LinkedInAds/Collector", "TotalImpressions", {"stat": "Sum"}],
          [".", "TotalClicks", {"stat": "Sum"}]
        ],
        "period": 21600,
        "stat": "Sum",
        "region": "${AWS_REGION}",
        "title": "Impressions & Clicks",
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["LinkedInAds/Collector", "TotalCost", {"stat": "Sum"}]
        ],
        "period": 21600,
        "stat": "Sum",
        "region": "${AWS_REGION}",
        "title": "Ad Spend",
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["LinkedInAds/Collector", "CTR", {"stat": "Average"}]
        ],
        "period": 21600,
        "stat": "Average",
        "region": "${AWS_REGION}",
        "title": "Click-Through Rate",
        "yAxis": {"left": {"min": 0}}
      }
    }
  ]
}
EOF
) \
  --region ${AWS_REGION}

echo "Dashboard created: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${COMPANY_SHORT}-linkedin-ads"
```

### Step 3: Set Up Daily Reports (Optional)

Create a scheduled Lambda to email daily performance summaries:

```python
# Save as lambda/daily_report/handler.py
import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """Send daily performance report via email."""

    cloudwatch = boto3.client('cloudwatch')
    sns = boto3.client('sns')

    # Get yesterday's metrics
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    # Fetch metrics
    metrics = {
        'impressions': get_metric('TotalImpressions', start_time, end_time),
        'clicks': get_metric('TotalClicks', start_time, end_time),
        'cost': get_metric('TotalCost', start_time, end_time),
        'ctr': get_metric('CTR', start_time, end_time, stat='Average')
    }

    # Format email
    message = f"""
    LinkedIn Ads Daily Report - {start_time.date()}

    Impressions: {metrics['impressions']:,}
    Clicks: {metrics['clicks']:,}
    Cost: ${metrics['cost']:.2f}
    CTR: {metrics['ctr']:.2f}%
    CPC: ${metrics['cost']/metrics['clicks'] if metrics['clicks'] > 0 else 0:.2f}
    """

    # Send via SNS
    sns.publish(
        TopicArn='YOUR_SNS_TOPIC_ARN',
        Subject=f'LinkedIn Ads Report - {start_time.date()}',
        Message=message
    )

    return {'statusCode': 200}

def get_metric(name, start, end, stat='Sum'):
    cw = boto3.client('cloudwatch')
    response = cw.get_metric_statistics(
        Namespace='LinkedInAds/Collector',
        MetricName=name,
        StartTime=start,
        EndTime=end,
        Period=86400,
        Statistics=[stat]
    )
    return response['Datapoints'][0][stat] if response['Datapoints'] else 0
```

---

## Data Analytics Configuration

### After 24 hours of data collection

**Duration**: 30 minutes

### Step 1: Create Athena Database

```bash
# Create Athena query execution bucket
ATHENA_BUCKET="${COMPANY_SHORT}-athena-results"
aws s3 mb s3://${ATHENA_BUCKET} --region ${AWS_REGION}

# Create database
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS linkedin_ads" \
  --result-configuration "OutputLocation=s3://${ATHENA_BUCKET}/" \
  --region ${AWS_REGION}
```

### Step 2: Create Athena Tables

```bash
# Run table creation scripts
for SQL_FILE in athena/*.sql; do
  echo "Executing: $SQL_FILE"

  QUERY=$(cat $SQL_FILE | sed "s/your-company-linkedin-ads-automation/${DATA_BUCKET}/g")

  aws athena start-query-execution \
    --query-string "$QUERY" \
    --result-configuration "OutputLocation=s3://${ATHENA_BUCKET}/" \
    --region ${AWS_REGION}

  sleep 5
done

echo "✓ Athena tables created"
```

### Step 3: Test Queries

```bash
# Simple query to verify data
QUERY="SELECT COUNT(*) as total_records FROM linkedin_ads.raw_analytics"

EXECUTION_ID=$(aws athena start-query-execution \
  --query-string "$QUERY" \
  --result-configuration "OutputLocation=s3://${ATHENA_BUCKET}/" \
  --region ${AWS_REGION} \
  --query 'QueryExecutionId' \
  --output text)

# Wait for completion
sleep 10

# Get results
aws athena get-query-results \
  --query-execution-id $EXECUTION_ID \
  --region ${AWS_REGION}
```

---

## Customization Guide

### Adjust Collection Frequency

**Current**: Every 6 hours

**To change to hourly**:
```bash
aws events put-rule \
  --name ${RULE_NAME} \
  --schedule-expression "rate(1 hour)" \
  --region ${AWS_REGION}
```

**To change to daily**:
```bash
aws events put-rule \
  --name ${RULE_NAME} \
  --schedule-expression "rate(1 day)" \
  --region ${AWS_REGION}
```

**To change to specific times** (e.g., 9 AM UTC daily):
```bash
aws events put-rule \
  --name ${RULE_NAME} \
  --schedule-expression "cron(0 9 * * ? *)" \
  --region ${AWS_REGION}
```

### Customize Alarm Thresholds

**Change high spend threshold** (default $100/day):
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "${COMPANY_SHORT}-linkedin-high-spend" \
  --threshold 200 \
  --region ${AWS_REGION}
  # ... other parameters same as original
```

**Change low CTR threshold** (default 1%):
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "${COMPANY_SHORT}-linkedin-low-ctr" \
  --threshold 0.5 \
  --region ${AWS_REGION}
  # ... other parameters same
```

### Add Additional Campaigns

```bash
# Get current campaign IDs
CURRENT_IDS=$(aws lambda get-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --region ${AWS_REGION} \
  --query 'Environment.Variables.CAMPAIGN_IDS' \
  --output text)

# Add new campaign
NEW_CAMPAIGN_ID="999888777"
UPDATED_IDS="${CURRENT_IDS},${NEW_CAMPAIGN_ID}"

# Update Lambda
aws lambda update-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --environment "Variables={
    BUCKET_NAME=${DATA_BUCKET},
    CAMPAIGN_IDS=${UPDATED_IDS},
    SECRET_NAME=${SECRET_NAME}
  }" \
  --region ${AWS_REGION}
```

### Customize Lambda Handler

Edit `lambda/collector/handler.py` to:

**Add custom metrics**:
```python
# Around line 180, add:
custom_metrics = {
    'ConversionRate': (total_conversions / total_clicks * 100) if total_clicks > 0 else 0,
    'UniqueImpressions': total_unique_impressions
}
send_cloudwatch_metrics(custom_metrics)
```

**Filter campaigns by performance**:
```python
# After fetching data, add filtering:
if analytics_data and 'elements' in analytics_data:
    for element in analytics_data['elements']:
        ctr = (element.get('clicks', 0) / element.get('impressions', 1)) * 100
        if ctr < 0.5:  # Skip low performers
            print(f"⚠️  Skipping low CTR creative: {element.get('pivotValue')}")
            continue
```

**Add Slack notifications**:
```python
import requests

def send_slack_notification(message):
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if webhook_url:
        requests.post(webhook_url, json={'text': message})

# In lambda_handler, after successful collection:
send_slack_notification(f"✓ Collected {total_clicks:,} clicks, ${total_cost:.2f} spend")
```

---

## Troubleshooting

### Issue: Lambda Timeout

**Symptom**: Lambda execution time > 120 seconds

**Solution**:
```bash
# Increase timeout to 5 minutes
aws lambda update-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --timeout 300 \
  --region ${AWS_REGION}
```

### Issue: 401 Unauthorized from LinkedIn

**Symptom**: API calls return 401 error

**Causes & Solutions**:

1. **Expired access token** (LinkedIn tokens expire after 60 days)
   ```bash
   # Regenerate token
   python3 scripts/oauth_setup.py
   ```

2. **Wrong secret name**
   ```bash
   # Verify secret name in Lambda environment
   aws lambda get-function-configuration \
     --function-name ${FUNCTION_NAME} \
     --query 'Environment.Variables.SECRET_NAME'
   ```

3. **Invalid credentials in Secrets Manager**
   ```bash
   # View current credentials (be careful with output)
   aws secretsmanager get-secret-value \
     --secret-id ${SECRET_NAME} \
     --region ${AWS_REGION}
   ```

### Issue: No Data in S3

**Symptom**: S3 bucket empty after Lambda execution

**Debugging steps**:

1. **Check Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/${FUNCTION_NAME} --since 1h --region ${AWS_REGION}
   ```

2. **Verify campaign IDs**:
   ```bash
   # Check if CAMPAIGN_IDS is set
   aws lambda get-function-configuration \
     --function-name ${FUNCTION_NAME} \
     --query 'Environment.Variables.CAMPAIGN_IDS'
   ```

3. **Test LinkedIn API manually**:
   ```bash
   ACCESS_TOKEN=$(aws secretsmanager get-secret-value \
     --secret-id ${SECRET_NAME} \
     --region ${AWS_REGION} \
     --query SecretString --output text | jq -r '.access_token')

   curl -v "https://api.linkedin.com/rest/adAnalytics?q=analytics&pivot=CREATIVE&campaigns[0]=urn:li:sponsoredCampaign:YOUR_CAMPAIGN_ID" \
     -H "Authorization: Bearer ${ACCESS_TOKEN}" \
     -H 'X-Restli-Protocol-Version: 2.0.0' \
     -H 'LinkedIn-Version: 202411'
   ```

4. **Check IAM permissions**:
   ```bash
   # Verify Lambda role has S3 permissions
   aws iam get-role-policy \
     --role-name ${ROLE_NAME} \
     --policy-name ${COMPANY_SHORT}-linkedin-collector-policy
   ```

### Issue: High AWS Costs

**Symptom**: Unexpected AWS bill

**Investigation**:

1. **Check costs by service**:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=2024-12-01,End=2024-12-31 \
     --granularity DAILY \
     --metrics UnblendedCost \
     --group-by Type=DIMENSION,Key=SERVICE
   ```

2. **Identify expensive resources**:
   - Check Lambda invocation count
   - Check S3 storage size
   - Check Athena query data scanned
   - Check CloudWatch Logs size

3. **Reduce costs**:
   ```bash
   # Reduce Lambda frequency
   aws events put-rule \
     --name ${RULE_NAME} \
     --schedule-expression "rate(12 hours)"

   # Reduce log retention
   aws logs put-retention-policy \
     --log-group-name /aws/lambda/${FUNCTION_NAME} \
     --retention-in-days 7

   # Add S3 lifecycle policy
   aws s3api put-bucket-lifecycle-configuration \
     --bucket ${DATA_BUCKET} \
     --lifecycle-configuration file://lifecycle.json
   ```

### Issue: EventBridge Not Triggering

**Symptom**: Lambda not running on schedule

**Solutions**:

1. **Check rule is enabled**:
   ```bash
   aws events describe-rule --name ${RULE_NAME} --region ${AWS_REGION}
   ```

2. **Enable rule if disabled**:
   ```bash
   aws events enable-rule --name ${RULE_NAME} --region ${AWS_REGION}
   ```

3. **Verify Lambda permission**:
   ```bash
   aws lambda get-policy --function-name ${FUNCTION_NAME} --region ${AWS_REGION}
   ```

4. **Check CloudWatch Events for errors**:
   ```bash
   aws logs tail /aws/events/${RULE_NAME} --since 1h --region ${AWS_REGION}
   ```

---

## Maintenance & Updates

### Monthly Tasks

**First week of month**:

1. **Review costs**:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=2024-12-01,End=2024-12-31 \
     --granularity MONTHLY \
     --metrics UnblendedCost
   ```

2. **Review performance**:
   ```sql
   -- Run in Athena
   SELECT
     DATE_TRUNC('month', report_date) as month,
     SUM(impressions) as total_impressions,
     SUM(clicks) as total_clicks,
     AVG(ctr) as avg_ctr,
     SUM(cost) as total_cost
   FROM linkedin_ads.daily_summary
   GROUP BY DATE_TRUNC('month', report_date)
   ORDER BY month DESC
   LIMIT 3;
   ```

3. **Check for underperforming campaigns**:
   ```sql
   SELECT
     campaign_id,
     campaign_name,
     overall_ctr,
     overall_cpc,
     total_cost
   FROM linkedin_ads.campaign_totals
   WHERE overall_ctr < 1.0
   ORDER BY total_cost DESC;
   ```

**Mid-month**:

4. **Verify data collection**:
   ```bash
   # Should have ~120 data points (4 per day * 30 days)
   aws s3 ls s3://${DATA_BUCKET}/raw/analytics/ --recursive | wc -l
   ```

5. **Check alarm history**:
   ```bash
   aws cloudwatch describe-alarm-history \
     --alarm-name "${COMPANY_SHORT}-linkedin-collector-errors" \
     --start-date $(date -d '1 month ago' +%Y-%m-%d) \
     --region ${AWS_REGION}
   ```

### Quarterly Tasks

1. **Refresh LinkedIn OAuth token** (expires after 60 days):
   ```bash
   python3 scripts/oauth_setup.py
   ```

2. **Review and optimize Athena queries**:
   - Check query costs in CloudWatch Metrics
   - Optimize frequently-run queries
   - Consider creating materialized views

3. **Update Lambda dependencies**:
   ```bash
   cd lambda/collector
   pip3 install -r requirements.txt --upgrade -t .
   cd ../..
   zip -r collector.zip lambda/collector/

   aws lambda update-function-code \
     --function-name ${FUNCTION_NAME} \
     --zip-file fileb://collector.zip \
     --region ${AWS_REGION}
   ```

4. **Review and update alarm thresholds** based on actual performance

### Annual Tasks

1. **Security audit**:
   - Rotate IAM access keys
   - Review IAM permissions
   - Enable AWS Config if not already
   - Review CloudTrail logs

2. **Cost optimization review**:
   - Analyze S3 storage lifecycle
   - Review Lambda reserved concurrency
   - Consider Savings Plans for predictable spend

3. **Backup verification**:
   ```bash
   # Verify S3 versioning is enabled
   aws s3api get-bucket-versioning --bucket ${DATA_BUCKET}

   # Export critical data
   aws s3 sync s3://${DATA_BUCKET}/raw/ ./backup/
   ```

### Updating Code

**To update Lambda code**:

1. Make changes locally to `lambda/collector/handler.py`

2. Test locally:
   ```bash
   cd lambda/collector
   python3 -c "
   import handler
   import json
   result = handler.lambda_handler({}, None)
   print(json.dumps(result, indent=2))
   "
   ```

3. Deploy:
   ```bash
   zip -r ../../collector.zip .

   aws lambda update-function-code \
     --function-name ${FUNCTION_NAME} \
     --zip-file fileb://collector.zip \
     --region ${AWS_REGION}
   ```

4. Verify:
   ```bash
   aws lambda invoke \
     --function-name ${FUNCTION_NAME} \
     --region ${AWS_REGION} \
     /tmp/test.json

   cat /tmp/test.json
   ```

---

## Appendix

### A. Complete Environment Variables Reference

| Variable | Purpose | Example | Required |
|----------|---------|---------|----------|
| `BUCKET_NAME` | S3 bucket for data storage | `acme-linkedin-ads-automation` | Yes |
| `CAMPAIGN_IDS` | Comma-separated campaign IDs | `123456,789012` | Yes |
| `SECRET_NAME` | Secrets Manager secret name | `acme-linkedin-credentials` | Yes |
| `AWS_REGION` | AWS region | `us-east-2` | Yes (via Lambda config) |

### B. LinkedIn API Rate Limits

| Endpoint | Rate Limit | Notes |
|----------|-----------|-------|
| Ad Analytics | 1,000 requests/day | Development tier |
| Campaign Management | 500 requests/day | Development tier |
| Creative Operations | 100 requests/day | Development tier |

**Production tier** (after LinkedIn reviews usage):
- 10x higher limits
- Requires demonstrating consistent usage
- Apply after 30 days of stable operation

### C. AWS Service Limits

| Service | Default Limit | Can Increase? |
|---------|--------------|---------------|
| Lambda concurrent executions | 1,000 | Yes |
| Lambda function size | 50 MB (zipped), 250 MB (unzipped) | No |
| S3 bucket count | 100 | Yes |
| EventBridge rules | 300 per account | Yes |
| Secrets Manager secrets | 500,000 | Yes |

### D. Cost Estimation Formula

```
Monthly Infrastructure Cost =
  Lambda: ($0.20 per 1M requests) * (120 requests/month) = $0.00024
  + S3 Storage: ($0.023 per GB) * (Data GB)
  + S3 API: ($0.005 per 1K PUT) * (120 PUT/month) = $0.0006
  + Secrets Manager: $0.40 per secret
  + CloudWatch Logs: ($0.50 per GB) * (Log GB)
  + Athena: ($5 per TB scanned) * (Query TB)

Typical first month: ~$2-5
After 6 months: ~$10-20
After 1 year: ~$20-50
```

### E. Useful AWS CLI Commands Cheat Sheet

```bash
# List all Lambda functions
aws lambda list-functions --region ${AWS_REGION}

# Get Lambda logs (last hour)
aws logs tail /aws/lambda/${FUNCTION_NAME} --since 1h --region ${AWS_REGION}

# List S3 objects with sizes
aws s3 ls s3://${DATA_BUCKET}/ --recursive --human-readable

# Get current month's AWS costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost

# Describe all EventBridge rules
aws events list-rules --region ${AWS_REGION}

# Get secret value
aws secretsmanager get-secret-value --secret-id ${SECRET_NAME} --region ${AWS_REGION}

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name ${FUNCTION_NAME} \
  --environment "Variables={VAR1=value1,VAR2=value2}" \
  --region ${AWS_REGION}

# Test Lambda function
aws lambda invoke \
  --function-name ${FUNCTION_NAME} \
  --payload '{}' \
  /tmp/output.json \
  --region ${AWS_REGION}

# Get CloudWatch metric data
aws cloudwatch get-metric-data \
  --metric-data-queries file://query.json \
  --start-time $(date -u -d '1 week ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --region ${AWS_REGION}
```

### F. Quick Reference Links

| Resource | URL |
|----------|-----|
| LinkedIn Developer Portal | https://www.linkedin.com/developers/apps |
| LinkedIn Campaign Manager | https://www.linkedin.com/campaignmanager |
| LinkedIn API Documentation | https://learn.microsoft.com/en-us/linkedin/marketing/ |
| AWS Lambda Console | https://console.aws.amazon.com/lambda |
| AWS S3 Console | https://s3.console.aws.amazon.com |
| AWS CloudWatch Console | https://console.aws.amazon.com/cloudwatch |
| AWS Athena Console | https://console.aws.amazon.com/athena |
| AWS Secrets Manager | https://console.aws.amazon.com/secretsmanager |

---

## Summary Checklist

Use this checklist when replicating for a new company:

### Pre-Deployment
- [ ] Gather company information
- [ ] Set up AWS account
- [ ] Install required tools (AWS CLI, Python, Git)
- [ ] Configure AWS CLI credentials
- [ ] Create GitHub repository

### LinkedIn Setup
- [ ] Create LinkedIn developer application
- [ ] Request Advertising API access
- [ ] Request Conversions API access (optional)
- [ ] Save Client ID and Client Secret
- [ ] Wait for approval (5-10 days)

### Infrastructure Deployment
- [ ] Customize variable names for company
- [ ] Create S3 buckets (data + Terraform state)
- [ ] Create Secrets Manager secret
- [ ] Build Lambda deployment package
- [ ] Create IAM role
- [ ] Deploy Lambda function
- [ ] Set up EventBridge schedule
- [ ] Create SNS topic
- [ ] Create CloudWatch alarms
- [ ] Verify all resources created

### Configuration
- [ ] Run OAuth flow to get access token
- [ ] Create LinkedIn ad campaigns
- [ ] Update Lambda with campaign IDs
- [ ] Subscribe email to SNS alerts
- [ ] Test manual Lambda invocation
- [ ] Verify data in S3
- [ ] Check CloudWatch logs
- [ ] Wait 24 hours for first scheduled run

### Analytics Setup
- [ ] Create Athena database
- [ ] Create Athena tables and views
- [ ] Run sample queries
- [ ] Create CloudWatch dashboard
- [ ] Set up daily reports (optional)

### Monitoring
- [ ] Verify EventBridge triggers
- [ ] Confirm data collection every 6 hours
- [ ] Monitor CloudWatch metrics
- [ ] Review costs weekly
- [ ] Check alarm status

### Documentation
- [ ] Save deployment summary
- [ ] Document campaign IDs
- [ ] Record resource ARNs
- [ ] Note important URLs
- [ ] Create runbook for team

---

**Total Time Investment**:
- LinkedIn setup: 1 hour + 5-10 days waiting
- AWS infrastructure: 2-3 hours
- Testing & verification: 1-2 hours
- Documentation: 1 hour

**Ongoing Maintenance**: ~2 hours/month

---

This completes the replication guide. Following these steps exactly will result in a fully functional LinkedIn Ads automation system for any company.

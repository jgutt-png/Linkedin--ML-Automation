# LinkedIn Ads Automation Pipeline

> **📋 This is a TEMPLATE repository**
> All sensitive information has been replaced with placeholders.
> **→ See [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md) for customization instructions**

**Automated LinkedIn advertising optimization using AWS infrastructure and machine learning.**

---

## Overview

Self-optimizing ad system for **YOUR_COMPANY_NAME** (your product or service) that:
- Continuously collects performance data from LinkedIn Ads API
- Identifies winning patterns (copy, targeting, timing)
- Automatically generates and tests new ad variations
- Scales winners, kills losers - zero manual intervention

**Target Audience**: YOUR_TARGET_AUDIENCE (e.g., industry professionals, decision makers, B2B buyers)

---

## 🚀 Quick Start for Template Users

1. **Read the setup guide**: [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md)
2. **Replace placeholders** with your information:
   - `YOUR_COMPANY_NAME` → Your company
   - `YOUR_ACCOUNT_ID` → Your AWS account ID
   - `YOUR_PRODUCT_DESCRIPTION` → Your product details
   - `your-email@example.com` → Your email
3. **Configure Terraform**: Update `terraform/terraform.tfvars`
4. **Apply for LinkedIn API**: Follow [docs/LINKEDIN_API_SETUP.md](./docs/LINKEDIN_API_SETUP.md)
5. **Deploy**: Run `terraform apply`

---

## Project Status

- [x] LinkedIn Developer App Setup (Submitted - Pending Approval)
- [x] AWS Infrastructure (Phase 1) - DEPLOYED
- [x] Data Collection Pipeline - DEPLOYED
- [x] Analytics Dashboard (Athena) - DEPLOYED
- [x] ML Models - CODE COMPLETE (awaiting data for training)
- [x] Automated Optimization Loop - CODE COMPLETE (ready to activate)
- [x] AI Copy Generator (Claude API) - CODE COMPLETE

**Current State**: All code and infrastructure configurations are complete. The system is collecting data. ML models can be trained once sufficient data (30+ days) is accumulated.

---

## Documentation

- **[Template Setup Guide](./TEMPLATE_SETUP.md)** - **START HERE** for customization
- **[Quick Start](./QUICK_START.md)** - 30-minute setup guide
- **[LinkedIn API Setup](./docs/LINKEDIN_API_SETUP.md)** - Developer account and API access
- **[AWS Architecture](./docs/AWS_ARCHITECTURE.md)** - Complete technical implementation
- **[Implementation Guide](./docs/IMPLEMENTATION_GUIDE.md)** - Step-by-step build process

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   LinkedIn   │───▶│    Lambda    │───▶│      S3      │              │
│  │   Ads API    │    │  (Collector) │    │  (Raw Data)  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                             │                    │                      │
│                             │                    ▼                      │
│                      ┌──────────────┐    ┌──────────────┐              │
│                      │  EventBridge │    │    Athena    │              │
│                      │  (Scheduler) │    │  (Queries)   │              │
│                      └──────────────┘    └──────────────┘              │
│                                                  │                      │
│                                                  ▼                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   LinkedIn   │◀───│    Lambda    │◀───│  SageMaker   │              │
│  │   Ads API    │    │  (Executor)  │    │   (Models)   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Data Collection (Week 1)
- S3 bucket for raw LinkedIn API data
- Lambda function to pull analytics every 6 hours
- EventBridge scheduler
- Secrets Manager for OAuth tokens

### Phase 2: Analytics Dashboard (Week 2)
- Athena tables for querying performance data
- SQL queries for CTR, CPC, creative performance
- Basic reporting dashboard

### Phase 3: ML Models (Week 3-4)
- Creative scoring model (predict CTR)
- Bid optimizer (optimal CPC by context)
- Copy generator (LLM-based variations)

### Phase 4: Automated Optimization (Week 5+)
- Decision engine runs daily
- Auto-pause underperformers
- Auto-scale winners
- Dynamic bid adjustments
- Zero manual intervention

---

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Lambda | ~$1 |
| S3 | ~$1-5 |
| Athena | ~$5-10 |
| Secrets Manager | ~$0.40 |
| SageMaker | ~$10-50 |
| **Total** | **~$20-70/month** |

**Ad Budget**: $20,000/year ($1,667/month)
**Infrastructure Cost**: < 5% of ad spend

---

## Key Metrics

**Optimization Triggers:**
- CTR < 1% for 3 days → Pause creative
- CTR > 3% → Create similar variations
- CPC > $8 → Lower bid
- Weekend → Reduce budget 50%
- No impressions → Broaden targeting

---

## Technology Stack

- **Cloud**: AWS (Lambda, S3, Athena, SageMaker, EventBridge)
- **IaC**: Terraform
- **Language**: Python 3.11
- **API**: LinkedIn Marketing Developer Platform
- **ML**: scikit-learn, SageMaker
- **Analytics**: Athena, SQL
- **AI**: Claude API (Anthropic)

---

## Repository Structure

```
linkedin-automation/
├── README.md                          # This file
├── TEMPLATE_SETUP.md                  # Setup guide for template users
├── QUICK_START.md                     # Fast deployment guide
│
├── lambda/                            # Lambda Functions
│   ├── collector/                     # Data collection from LinkedIn API
│   ├── optimizer/                     # Main optimization engine
│   ├── copy_generator/                # AI ad copy generation (Claude)
│   ├── data_processor/                # ML training data preparation
│   └── token_rotator/                 # OAuth token refresh
│
├── sagemaker/                         # ML Model Training
│   ├── train_creative_scorer.py       # Creative CTR prediction
│   ├── train_bid_optimizer.py         # Bid optimization
│   └── requirements.txt
│
├── terraform/                         # Infrastructure as Code
│   ├── main.tf                       # Provider configuration
│   ├── variables.tf                  # Input variables
│   ├── terraform.tfvars.example      # Example configuration
│   ├── s3.tf                         # S3 buckets
│   ├── lambda_collector.tf           # Lambda resources
│   ├── eventbridge.tf                # Event schedulers
│   ├── secrets.tf                    # Secrets Manager
│   └── monitoring.tf                 # CloudWatch alarms
│
├── athena/                           # SQL Analytics
│   ├── 01_create_database.sql
│   ├── 02_create_raw_analytics_table.sql
│   ├── 03_create_views.sql
│   └── 04_sample_queries.sql
│
├── scripts/                          # Utility Scripts
│   ├── oauth_setup.py               # OAuth flow automation
│   └── README.md
│
└── docs/                             # Documentation
    ├── LINKEDIN_API_SETUP.md        # LinkedIn API application guide
    ├── AWS_ARCHITECTURE.md          # Technical architecture
    └── IMPLEMENTATION_GUIDE.md      # Implementation instructions
```

---

## Getting Started

### Quick Deployment (After Template Customization)

```bash
# 1. Deploy all infrastructure and Lambda functions
cd terraform
terraform init
terraform apply

# 2. Store API secrets
aws secretsmanager create-secret \
  --name linkedin-ads-automation-credentials \
  --secret-string file://.secrets/linkedin_credentials.json

# 3. Subscribe to daily reports
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:YOUR_ACCOUNT_ID:linkedin-ads-automation-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### After Data Collection (30+ days)

```bash
# Train ML models
cd sagemaker
python train_creative_scorer.py
python train_bid_optimizer.py

# Models will automatically be used by optimizer Lambda
```

**📖 Detailed Guide**: See [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md) for complete documentation.

---

## Expected Results

| Metric | Timeline | Expected Improvement |
|--------|----------|---------------------|
| CTR | 2 weeks | +20-40% |
| CPC | 2 weeks | -15-25% |
| Cost per conversion | 4 weeks | -30-40% |
| Time spent | Immediate | 90% reduction |

---

## Security Notes

✓ S3 buckets encrypted at rest (AES-256)
✓ S3 public access blocked
✓ Secrets in AWS Secrets Manager (not code)
✓ IAM roles with least-privilege permissions
✓ CloudWatch logging for audit trail
✓ OAuth token rotation every 60 days

---

## What's Included

✅ **Complete AWS Infrastructure** - Terraform configs for all resources
✅ **LinkedIn API Integration** - Full OAuth flow and data collection
✅ **Data Pipeline** - Automated collection every 6 hours
✅ **Analytics** - Athena database with pre-built queries
✅ **ML Optimization** - Creative scoring and bid optimization
✅ **AI Copy Generation** - Claude-powered ad variations
✅ **Monitoring** - CloudWatch dashboards and alerts
✅ **Documentation** - Comprehensive guides for setup and operation

---

## Support

- **Setup Issues**: See [TEMPLATE_SETUP.md](./TEMPLATE_SETUP.md)
- **LinkedIn API**: [docs/LINKEDIN_API_SETUP.md](./docs/LINKEDIN_API_SETUP.md)
- **AWS Architecture**: [docs/AWS_ARCHITECTURE.md](./docs/AWS_ARCHITECTURE.md)
- **Deployment**: [docs/IMPLEMENTATION_GUIDE.md](./docs/IMPLEMENTATION_GUIDE.md)

---

## License

MIT License - See LICENSE file for details

---

**Built with ❤️ for LinkedIn advertisers who want to automate and optimize at scale**

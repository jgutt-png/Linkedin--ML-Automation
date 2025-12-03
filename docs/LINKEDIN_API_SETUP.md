# LinkedIn API Setup Guide

Complete guide to obtaining LinkedIn Advertising API access for YOUR_COMPANY_NAME.

---

## Overview

**Goal**: Get Marketing Developer Platform (MDP) access to programmatically manage LinkedIn ad campaigns.

**Timeline**: 5-10 business days for approval after application submission.

---

## Step 1: Create LinkedIn Developer App

### URL
https://www.linkedin.com/developers/apps/new

### Required Information

| Field | Value |
|-------|-------|
| **App name** | YOUR_COMPANY_NAME Ads Manager |
| **LinkedIn Page** | Your company page (required) |
| **Privacy policy URL** | https://acquisitionatlas.com/privacy |
| **App logo** | 300x300px logo |
| **App description** | Automated ad campaign management and optimization for your product or service |

### Notes
- You must have a LinkedIn Company Page
- Privacy policy URL is required (can be your main website privacy page)
- Logo should be professional and represent your brand

---

## Step 2: Request Advertising API Access

### Product Selection

From the **Products** tab, select:

**✓ Advertising API** (Development Tier)
- Description: "Build marketing experiences to reach the right audiences"
- This gives you campaign management, analytics, and bid control

**Optional (for later)**:
- Conversions API - Track which clicks convert on your site

**Do NOT request**:
- Share on LinkedIn (social posting only)
- Lead Sync API (lead gen forms)
- Sign In with LinkedIn (OAuth login)

---

## Step 3: Complete Application Form

### Form Responses

#### **Where are most of your customers based?**
```
North America
```

#### **How many clients leverage the product you're planning to integrate the API with?**
```
N/A (Direct Customer)
```

#### **What % of your clients are B2B?**
```
N/A (Direct Customer)
```

#### **What category best describes the majority of your customers?**
```
Direct Customers
```

#### **What industries are most common among your customers?**
```
Real Estate Investment, Commercial Real Estate, Property Development, Real Estate Technology, Institutional Investment
```

---

### Business Details

#### **What is the primary use case for this integration?**
```
Direct Advertiser: to manage only owned and operated LinkedIn activity/data streams.
```

#### **How much digital ad spend is managed or reported on/via your product on an annual basis?**
```
20000
```
*(Dollar value only, no commas or symbols)*

#### **Tell us about your business and the product that will leverage API access:**
```
YOUR_COMPANY_NAME is a your product or service that provides property investors, developers, and institutional buyers with actionable market insights. We aggregate public records, market trends, and property analytics to help professionals identify high-value acquisition opportunities.

Our platform serves real estate investors seeking off-market deals, distressed properties, and emerging market opportunities across North America. We need API access to programmatically manage our LinkedIn advertising campaigns that target commercial real estate professionals, property investors, and institutional capital allocators.
```

#### **What is your intended use case? (select all that apply)**
```
☑ Campaign Management
☑ Reporting and ROI
```

#### **What do you plan to build with the APIs?**
```
We will build an automated campaign optimization system that:

1. Dynamically adjusts ad creative and targeting based on performance data (CTR, CPC, conversion rates)
2. Automatically pauses underperforming ads and scales winning variations
3. Optimizes bid strategies based on time-of-day and audience engagement patterns
4. Pulls real-time analytics to measure ROI and cost-per-acquisition
5. A/B tests ad copy variations to identify high-performing messaging for different real estate professional segments

This automation will allow us to efficiently reach our target audience of commercial real estate professionals while maintaining cost-effective customer acquisition.
```

#### **Do you have partnerships with any other platforms?**
```
☑ Other: "None currently - direct advertising only"
```

---

## Step 4: Wait for Approval

### What to Expect

- **Timeline**: 5-10 business days
- **Email notification**: LinkedIn will email when approved/rejected
- **Status check**: Monitor at https://www.linkedin.com/developers/apps

### If Rejected
- Usually due to vague use case description
- Reapply with more detail about automation and optimization
- Emphasize you're a direct advertiser, not building a platform

---

## Step 5: Get OAuth Credentials (After Approval)

### Navigate to App Settings

1. Go to https://www.linkedin.com/developers/apps
2. Select your app
3. Click **Auth** tab

### Save These Credentials

```
Client ID: 78xxxxxxxxxxxxx
Client Secret: xxxxxxxxxx (click "Show" to reveal)
```

**⚠️ SECURITY**: Never commit these to git. Store in AWS Secrets Manager.

---

## Step 6: Configure OAuth Redirect URL

### Add Redirect URI

Under **Auth** tab → **OAuth 2.0 settings**:

**For Production:**
```
https://yourdomain.com/linkedin/callback
```

**For Local Testing:**
```
http://localhost:8000/callback
```

---

## Step 7: Verify API Scopes

Under **Products** → **Advertising API** → **Permissions**:

Ensure these scopes are enabled:

```
✓ r_ads              (Read ad campaign data)
✓ rw_ads             (Create/modify campaigns)
✓ r_basicprofile     (User profile info)
✓ r_organization_social (Company page access)
```

---

## Step 8: Test API Access

### Generate Access Token

Use OAuth 2.0 flow to get access token. See `scripts/oauth_setup.py` for implementation.

### Test Request

```bash
curl -X GET 'https://api.linkedin.com/rest/adAccounts?q=search' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'X-Restli-Protocol-Version: 2.0.0' \
  -H 'LinkedIn-Version: 202411'
```

**Expected Response:**
```json
{
  "elements": [
    {
      "id": 123456789,
      "name": "YOUR_COMPANY_NAME Ad Account",
      "status": "ACTIVE"
    }
  ]
}
```

---

## Important Links

| Resource | URL |
|----------|-----|
| Developer Portal | https://www.linkedin.com/developers/apps |
| API Documentation | https://learn.microsoft.com/en-us/linkedin/marketing/ |
| Advertising API Docs | https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/ |
| OAuth 2.0 Guide | https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication |
| Rate Limits | https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits |

---

## Rate Limits

| Endpoint Type | Rate Limit |
|--------------|------------|
| Ad Analytics | 1,000 requests/day per app |
| Campaign Management | 500 requests/day per app |
| Creative Operations | 100 requests/day per app |

**Note**: These are Development Tier limits. Production tier has higher limits after LinkedIn reviews your usage.

---

## Next Steps

Once approved:
1. Store credentials in AWS Secrets Manager (see [AWS_ARCHITECTURE.md](./AWS_ARCHITECTURE.md))
2. Test OAuth flow with `scripts/oauth_setup.py`
3. Deploy Lambda data collector
4. Start gathering campaign data

---

## Troubleshooting

### Application Rejected
- **Issue**: Vague use case description
- **Fix**: Resubmit with detailed technical explanation
- **Emphasize**: You're a direct advertiser, not a platform

### Can't See Advertising API Product
- **Issue**: App not associated with Company Page
- **Fix**: Add company page in app settings

### OAuth Errors
- **Issue**: Invalid redirect URI
- **Fix**: Ensure redirect URL matches exactly in app settings

### 403 Forbidden on API Calls
- **Issue**: Token missing required scopes
- **Fix**: Regenerate token with all required scopes

---

## Contact LinkedIn Support

If stuck, contact LinkedIn Developer Support:
- **Portal**: https://www.linkedin.com/help/linkedin/ask/api
- **Email**: Via support portal only
- **Response Time**: 2-5 business days

---

## Security Best Practices

1. **Never commit credentials to git**
2. **Rotate access tokens every 60 days**
3. **Use AWS Secrets Manager for storage**
4. **Enable CloudTrail logging for API calls**
5. **Restrict IAM permissions to least privilege**

---

## Status Checklist

- [ ] Developer app created
- [ ] Advertising API access requested
- [ ] Application submitted with detailed use case
- [ ] Approval received (5-10 days)
- [ ] OAuth credentials saved in Secrets Manager
- [ ] Redirect URL configured
- [ ] API scopes verified
- [ ] Test API call successful
- [ ] Ready for Phase 1 implementation

# Scripts

Utility scripts for LinkedIn Ads automation setup and management.

---

## oauth_setup.py

Interactive OAuth 2.0 flow to authorize LinkedIn API access.

**Purpose**: Get access token after LinkedIn approves your API application.

**Usage**:
```bash
# 1. Create credentials file
mkdir -p .secrets
cat > .secrets/linkedin_credentials.json <<EOF
{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET"
}
EOF

# 2. Run OAuth flow
python3 scripts/oauth_setup.py
```

**What it does**:
1. Opens browser to LinkedIn authorization page
2. User grants permissions
3. Exchanges auth code for access token
4. Saves token locally to `.secrets/linkedin_credentials.json`
5. Uploads credentials to AWS Secrets Manager

**Prerequisites**:
- LinkedIn API application approved
- Client ID and Client Secret from LinkedIn
- AWS CLI configured
- Python 3.11+

**Output**:
- Access token saved to `.secrets/linkedin_credentials.json`
- Credentials uploaded to AWS Secrets Manager: `linkedin-ads-automation-credentials`

---

## Future Scripts

Additional scripts to be added:

- `test_api.py` - Test LinkedIn API connectivity
- `refresh_token.py` - Refresh expired access token
- `export_data.py` - Export S3 data to CSV
- `train_model.py` - Train creative scoring model locally

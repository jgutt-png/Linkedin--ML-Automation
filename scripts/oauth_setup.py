#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 Setup Script

Run this script once to authorize your LinkedIn developer app and get an access token.

Usage:
    1. Complete LinkedIn API application and get approved
    2. Get Client ID and Client Secret from LinkedIn Developer Portal
    3. Create .secrets/linkedin_credentials.json with client_id and client_secret
    4. Run this script: python3 scripts/oauth_setup.py
    5. Authorize in browser when prompted
    6. Access token will be saved and uploaded to AWS Secrets Manager
"""

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests
import sys
import os
import boto3

# Configuration
SECRETS_DIR = '.secrets'
CREDENTIALS_FILE = f'{SECRETS_DIR}/linkedin_credentials.json'
REDIRECT_URI = 'http://localhost:8000/callback'

# LinkedIn OAuth URLs
AUTH_URL = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'

# Required scopes for Advertising API and Conversions API
SCOPES = [
    'r_ads',                    # Read ads data
    'rw_ads',                   # Create/modify ads
    'r_basicprofile',           # User profile
    'r_organization_social',    # Company page access
    'w_member_social',          # Post on behalf of user
]


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to handle OAuth callback."""

    def do_GET(self):
        """Handle the OAuth callback from LinkedIn."""

        # Parse authorization code from callback
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'error' in params:
            error = params['error'][0]
            error_description = params.get('error_description', ['Unknown error'])[0]

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body>
                    <h1>Authorization Failed</h1>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                    <p>Please check your LinkedIn app settings and try again.</p>
                </body>
                </html>
            """.encode())

            print(f"\n❌ Authorization failed: {error}")
            print(f"   {error_description}")
            return

        if 'code' not in params:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                    <h1>Error</h1>
                    <p>No authorization code received.</p>
                </body>
                </html>
            """)
            return

        code = params['code'][0]
        print(f"\n✓ Authorization code received")

        try:
            # Load credentials
            with open(CREDENTIALS_FILE) as f:
                creds = json.load(f)

            client_id = creds['client_id']
            client_secret = creds['client_secret']

            # Exchange code for access token
            print(f"🔄 Exchanging authorization code for access token...")

            token_response = requests.post(TOKEN_URL, data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': REDIRECT_URI,
                'client_id': client_id,
                'client_secret': client_secret
            }, timeout=30)

            if token_response.status_code != 200:
                raise Exception(f"Token exchange failed: {token_response.text}")

            token_data = token_response.json()
            access_token = token_data['access_token']
            expires_in = token_data['expires_in']

            print(f"✓ Access token received!")
            print(f"  Token expires in: {expires_in} seconds ({expires_in/3600:.1f} hours)")

            # Save token to credentials file
            creds['access_token'] = access_token
            creds['expires_in'] = expires_in
            creds['obtained_at'] = datetime.now().isoformat()

            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump(creds, f, indent=2)

            print(f"💾 Saved to {CREDENTIALS_FILE}")

            # Upload to AWS Secrets Manager
            upload_to_aws(creds)

            # Success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            max-width: 600px;
                            margin: 50px auto;
                            padding: 20px;
                        }}
                        .success {{
                            background: #d4edda;
                            border: 1px solid #c3e6cb;
                            border-radius: 4px;
                            padding: 20px;
                            color: #155724;
                        }}
                        h1 {{ margin-top: 0; }}
                        code {{
                            background: #f8f9fa;
                            padding: 2px 6px;
                            border-radius: 3px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="success">
                        <h1>✓ Success!</h1>
                        <p>LinkedIn OAuth authorization complete.</p>
                        <ul>
                            <li>Access token saved locally</li>
                            <li>Credentials uploaded to AWS Secrets Manager</li>
                            <li>Token expires in {expires_in/3600:.1f} hours</li>
                        </ul>
                        <p>You can close this window and return to the terminal.</p>
                    </div>
                </body>
                </html>
            """.encode())

        except Exception as e:
            print(f"\n❌ Error: {e}")

            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
                <html>
                <body>
                    <h1>Error</h1>
                    <p>Failed to exchange authorization code for token.</p>
                    <p><code>{str(e)}</code></p>
                </body>
                </html>
            """.encode())

    def log_message(self, format, *args):
        """Suppress HTTP request logs."""
        pass


def upload_to_aws(credentials: dict) -> None:
    """Upload credentials to AWS Secrets Manager."""

    try:
        print(f"\n☁️  Uploading to AWS Secrets Manager...")

        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

        secret_name = 'linkedin-ads-automation-credentials'

        # Try to update existing secret
        try:
            secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(credentials)
            )
            print(f"✓ Updated existing secret: {secret_name}")

        except secrets_client.exceptions.ResourceNotFoundException:
            # Create new secret if it doesn't exist
            secrets_client.create_secret(
                Name=secret_name,
                Description='LinkedIn Ads API OAuth credentials',
                SecretString=json.dumps(credentials)
            )
            print(f"✓ Created new secret: {secret_name}")

    except Exception as e:
        print(f"⚠️  Warning: Could not upload to AWS: {e}")
        print(f"   You can manually update the secret later using:")
        print(f"   aws secretsmanager update-secret --secret-id {secret_name} --secret-string file://{CREDENTIALS_FILE}")


def main():
    """Main OAuth flow."""

    print("=" * 60)
    print("LinkedIn OAuth 2.0 Setup")
    print("=" * 60)

    # Check if credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ Error: Credentials file not found: {CREDENTIALS_FILE}")
        print(f"\nPlease create {CREDENTIALS_FILE} with your LinkedIn app credentials:")
        print(f"""
{{
  "client_id": "YOUR_CLIENT_ID_FROM_LINKEDIN",
  "client_secret": "YOUR_CLIENT_SECRET_FROM_LINKEDIN"
}}
        """)
        sys.exit(1)

    # Load credentials
    try:
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)

        if 'client_id' not in creds or 'client_secret' not in creds:
            print(f"❌ Error: Credentials file must contain client_id and client_secret")
            sys.exit(1)

        if creds['client_id'].startswith('YOUR_') or creds['client_id'].startswith('PLACEHOLDER'):
            print(f"❌ Error: Please replace placeholder values with actual LinkedIn credentials")
            sys.exit(1)

        client_id = creds['client_id']
        print(f"✓ Loaded credentials for Client ID: {client_id[:10]}...")

    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {CREDENTIALS_FILE}")
        sys.exit(1)

    # Build authorization URL
    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES)
    }

    auth_url = f"{AUTH_URL}?{urlencode(auth_params)}"

    print(f"\n📋 OAuth Flow Steps:")
    print(f"   1. Opening browser to LinkedIn authorization page")
    print(f"   2. After authorizing, you'll be redirected to localhost:8000")
    print(f"   3. Access token will be saved automatically")
    print(f"   4. Credentials will be uploaded to AWS Secrets Manager")
    print(f"\n🔐 Requesting scopes: {', '.join(SCOPES)}")
    print(f"\n🌐 Starting local server on http://localhost:8000...")

    # Start local server for callback
    server = HTTPServer(('localhost', 8000), OAuthCallbackHandler)

    # Open browser
    print(f"🚀 Opening browser...")
    webbrowser.open(auth_url)

    print(f"\n⏳ Waiting for authorization...")
    print(f"   (Listening for callback on http://localhost:8000/callback)")

    # Handle one request (the callback)
    server.handle_request()

    print(f"\n{'=' * 60}")
    print(f"✅ OAuth Setup Complete!")
    print(f"{'=' * 60}")
    print(f"\nNext steps:")
    print(f"  1. Verify credentials in AWS Secrets Manager")
    print(f"  2. Deploy Terraform infrastructure")
    print(f"  3. Test Lambda collector function")
    print(f"\n")


if __name__ == '__main__':
    from datetime import datetime
    main()

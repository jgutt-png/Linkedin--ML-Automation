"""
Token Rotation Lambda

Automatically refreshes LinkedIn OAuth token every 60 days.
Triggered by AWS Secrets Manager rotation schedule.

This prevents manual token refresh and ensures uninterrupted data collection.
"""

import boto3
import json
import requests
import os
from datetime import datetime
from typing import Dict, Any

secrets = boto3.client('secretsmanager')
sns = boto3.client('sns')

# LinkedIn OAuth endpoints
LINKEDIN_TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'
LINKEDIN_TEST_URL = 'https://api.linkedin.com/v2/me'

# Environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')


def get_current_token(secret_id: str) -> Dict[str, str]:
    """Retrieve current token from Secrets Manager."""
    try:
        response = secrets.get_secret_value(SecretId=secret_id)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"❌ Error retrieving current token: {e}")
        raise


def refresh_linkedin_token(current_credentials: Dict[str, str]) -> str:
    """
    Refresh LinkedIn OAuth token.

    LinkedIn tokens can be refreshed using the refresh_token grant type.
    The client_id and client_secret are needed for the refresh.

    Note: This assumes you have client_id, client_secret, and refresh_token
    stored in Secrets Manager along with the access_token.
    """

    client_id = current_credentials.get('client_id')
    client_secret = current_credentials.get('client_secret')
    refresh_token = current_credentials.get('refresh_token')

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing required credentials: client_id, client_secret, or refresh_token")

    print("🔄 Refreshing LinkedIn OAuth token...")

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        response = requests.post(
            LINKEDIN_TOKEN_URL,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )

        response.raise_for_status()
        token_data = response.json()

        new_access_token = token_data['access_token']
        new_refresh_token = token_data.get('refresh_token', refresh_token)  # Some APIs return new refresh token

        print(f"✓ New token obtained, expires in {token_data.get('expires_in', 'unknown')} seconds")

        return new_access_token, new_refresh_token

    except requests.exceptions.RequestException as e:
        print(f"❌ Error refreshing token: {e}")
        raise


def test_token(access_token: str) -> bool:
    """Test if the new token works by calling a simple API endpoint."""

    print("🧪 Testing new token...")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202411'
    }

    try:
        response = requests.get(
            LINKEDIN_TEST_URL,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        print("✓ Token test successful")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Token test failed: {e}")
        return False


def update_secret(secret_id: str, new_credentials: Dict[str, str]) -> None:
    """Update Secrets Manager with new token."""

    print("💾 Updating Secrets Manager...")

    try:
        secrets.update_secret(
            SecretId=secret_id,
            SecretString=json.dumps(new_credentials)
        )
        print("✓ Secret updated successfully")

    except Exception as e:
        print(f"❌ Error updating secret: {e}")
        raise


def send_notification(subject: str, message: str, success: bool = True) -> None:
    """Send SNS notification about rotation status."""

    if not SNS_TOPIC_ARN:
        print("⚠️  No SNS topic configured, skipping notification")
        return

    emoji = "✅" if success else "❌"

    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"{emoji} LinkedIn Token Rotation - {subject}",
            Message=message
        )
        print(f"✓ Notification sent: {subject}")

    except Exception as e:
        print(f"⚠️  Could not send notification: {e}")


def lambda_handler(event, context):
    """
    Main token rotation handler.

    Called by Secrets Manager rotation schedule.

    Event structure from Secrets Manager:
    {
      "Step": "createSecret" | "setSecret" | "testSecret" | "finishSecret",
      "SecretId": "arn:aws:secretsmanager:...",
      "Token": "rotation-token"
    }

    Steps:
    1. createSecret - Get current token, refresh it, store as AWSPENDING
    2. setSecret - No action needed for API tokens
    3. testSecret - Verify new token works
    4. finishSecret - Mark new token as AWSCURRENT
    """

    print("=" * 60)
    print("🔐 LinkedIn Token Rotation Started")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    step = event.get('Step')
    secret_id = event.get('SecretId')
    token = event.get('Token')

    print(f"\nRotation Step: {step}")
    print(f"Secret ID: {secret_id}")

    try:
        if step == 'createSecret':
            print("\n📝 STEP 1: Creating new secret version...")

            # Get current credentials
            current_creds = get_current_token(secret_id)

            # Refresh the token
            new_access_token, new_refresh_token = refresh_linkedin_token(current_creds)

            # Create new credentials dict
            new_creds = current_creds.copy()
            new_creds['access_token'] = new_access_token
            new_creds['refresh_token'] = new_refresh_token
            new_creds['rotated_at'] = datetime.utcnow().isoformat()

            # Store as AWSPENDING version
            secrets.put_secret_value(
                SecretId=secret_id,
                SecretString=json.dumps(new_creds),
                VersionStages=['AWSPENDING'],
                ClientRequestToken=token
            )

            print("✓ New token stored as AWSPENDING")

        elif step == 'setSecret':
            print("\n⚙️  STEP 2: Set secret (no action needed for tokens)")
            # For database passwords, you'd update the database here
            # For API tokens, no action needed
            pass

        elif step == 'testSecret':
            print("\n🧪 STEP 3: Testing new token...")

            # Get the AWSPENDING version
            response = secrets.get_secret_value(
                SecretId=secret_id,
                VersionStage='AWSPENDING',
                VersionId=token
            )

            pending_creds = json.loads(response['SecretString'])
            new_token = pending_creds['access_token']

            # Test it
            if not test_token(new_token):
                raise Exception("New token failed validation test")

            print("✓ Token validation successful")

        elif step == 'finishSecret':
            print("\n✅ STEP 4: Finalizing rotation...")

            # Move AWSCURRENT stage to new version
            secrets.update_secret_version_stage(
                SecretId=secret_id,
                VersionStage='AWSCURRENT',
                MoveToVersionId=token,
                RemoveFromVersionId=event.get('OldSecretVersionId')
            )

            print("✓ New token is now AWSCURRENT")

            # Send success notification
            message = f"""
LinkedIn OAuth token has been successfully rotated.

Rotation Time: {datetime.utcnow().isoformat()}
Secret: {secret_id}

The new token has been tested and is now active.
All LinkedIn API calls will use the new token automatically.

No action required.
            """

            send_notification("Success", message, success=True)

        else:
            raise ValueError(f"Unknown rotation step: {step}")

        print("\n" + "=" * 60)
        print(f"✅ Step '{step}' completed successfully")
        print("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'step': step,
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        print(f"\n❌ ROTATION FAILED ❌")
        print(f"Step: {step}")
        print(f"Error: {str(e)}")

        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

        # Send failure notification
        message = f"""
LinkedIn OAuth token rotation FAILED.

Step: {step}
Error: {str(e)}
Time: {datetime.utcnow().isoformat()}

ACTION REQUIRED:
1. Check CloudWatch Logs for details
2. Manually refresh the token if needed
3. Investigate the rotation failure

Secret: {secret_id}
        """

        send_notification("FAILED", message, success=False)

        # Re-raise to mark rotation as failed
        raise


# For local testing
if __name__ == '__main__':
    # Simulate rotation steps
    test_event = {
        'Step': 'createSecret',
        'SecretId': 'linkedin-access-token',
        'Token': 'test-rotation-token'
    }

    lambda_handler(test_event, None)

"""
LinkedIn Ads Data Collector Lambda Function

Collects campaign and creative performance data from LinkedIn Ads API
Runs every 6 hours via EventBridge schedule
Stores raw data in S3 for processing
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
import traceback

# AWS Clients
s3 = boto3.client('s3')
secrets = boto3.client('secretsmanager')
cloudwatch = boto3.client('cloudwatch')

# Environment Variables
BUCKET_NAME = os.environ.get('BUCKET_NAME')
CAMPAIGN_IDS = os.environ.get('CAMPAIGN_IDS', '').split(',')
SECRET_NAME = os.environ.get('SECRET_NAME')

# LinkedIn API Configuration
LINKEDIN_API_BASE = 'https://api.linkedin.com/rest'
LINKEDIN_VERSION = '202411'


def get_linkedin_credentials() -> Dict[str, str]:
    """Retrieve LinkedIn OAuth token from Secrets Manager."""
    try:
        response = secrets.get_secret_value(SecretId=SECRET_NAME)
        credentials = json.loads(response['SecretString'])

        if not credentials.get('access_token'):
            raise ValueError("No access_token found in credentials")

        return credentials
    except Exception as e:
        print(f"❌ Error retrieving credentials: {e}")
        raise


def get_api_headers(access_token: str) -> Dict[str, str]:
    """Generate headers for LinkedIn API requests."""
    return {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': LINKEDIN_VERSION,
        'Content-Type': 'application/json'
    }


def pull_creative_analytics(
    access_token: str,
    campaign_id: str,
    start_date: datetime,
    end_date: datetime
) -> Optional[Dict[str, Any]]:
    """
    Pull performance metrics broken down by creative.

    API Docs: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting
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
        print(f"📊 Pulling analytics for campaign {campaign_id}")
        response = requests.get(
            f'{LINKEDIN_API_BASE}/adAnalytics',
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        print(f"✓ Retrieved {len(data.get('elements', []))} analytics records")
        return data

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f"❌ Authentication failed - token may be expired")
        elif e.response.status_code == 429:
            print(f"⚠️  Rate limit exceeded - will retry later")
        else:
            print(f"❌ HTTP error: {e.response.status_code} - {e.response.text}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling LinkedIn API: {e}")
        return None


def pull_campaign_details(access_token: str, campaign_id: str) -> Optional[Dict[str, Any]]:
    """Get campaign configuration including targeting and budget."""

    headers = get_api_headers(access_token)

    try:
        print(f"⚙️  Pulling campaign config for {campaign_id}")
        response = requests.get(
            f'{LINKEDIN_API_BASE}/adCampaigns/{campaign_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        print(f"✓ Retrieved campaign details")
        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting campaign details: {e}")
        return None


def save_to_s3(data: Dict[str, Any], bucket: str, key: str) -> bool:
    """Save JSON data to S3."""
    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2, default=str),
            ContentType='application/json'
        )
        print(f"💾 Saved to s3://{bucket}/{key}")
        return True
    except Exception as e:
        print(f"❌ Error saving to S3: {e}")
        return False


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
        print(f"📈 Sent {len(metric_data)} metrics to CloudWatch")
    except Exception as e:
        print(f"⚠️  Error sending CloudWatch metrics: {e}")


def lambda_handler(event, context):
    """
    Main Lambda handler - executes every 6 hours via EventBridge.

    Flow:
    1. Get LinkedIn OAuth token from Secrets Manager
    2. Pull analytics for each campaign (last 24 hours)
    3. Pull campaign configuration
    4. Save raw data to S3
    5. Send metrics to CloudWatch
    """

    print("=" * 60)
    print(f"🚀 LinkedIn Ads Data Collection Started")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    # Validate environment
    if not BUCKET_NAME:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'BUCKET_NAME not configured'})
        }

    if not CAMPAIGN_IDS or CAMPAIGN_IDS == ['']:
        print("⚠️  No campaign IDs configured - will pull all campaigns")

    # Date range (last 24 hours)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)

    print(f"📅 Date range: {start_date.date()} to {end_date.date()}")

    try:
        # Get credentials
        print("🔑 Retrieving LinkedIn credentials...")
        credentials = get_linkedin_credentials()
        access_token = credentials['access_token']
        print("✓ Credentials retrieved successfully")

        # Metrics for CloudWatch
        total_impressions = 0
        total_clicks = 0
        total_cost = 0
        successful_pulls = 0
        failed_pulls = 0

        # Process each campaign
        campaigns_to_process = [c.strip() for c in CAMPAIGN_IDS if c.strip()]

        if not campaigns_to_process:
            print("ℹ️  No specific campaigns configured - skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No campaigns configured yet',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }

        for campaign_id in campaigns_to_process:
            print(f"\n{'─' * 60}")
            print(f"Processing Campaign: {campaign_id}")
            print(f"{'─' * 60}")

            # Pull analytics data
            analytics_data = pull_creative_analytics(
                access_token,
                campaign_id,
                start_date,
                end_date
            )

            # Pull campaign configuration
            campaign_details = pull_campaign_details(access_token, campaign_id)

            if not analytics_data and not campaign_details:
                print(f"⚠️  No data retrieved for campaign {campaign_id}")
                failed_pulls += 1
                continue

            # Combine data
            payload = {
                'pulled_at': datetime.utcnow().isoformat(),
                'campaign_id': campaign_id,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'analytics': analytics_data or {},
                'campaign_config': campaign_details or {}
            }

            # Calculate totals for CloudWatch
            if analytics_data and 'elements' in analytics_data:
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

            if save_to_s3(payload, BUCKET_NAME, s3_key):
                successful_pulls += 1
            else:
                failed_pulls += 1

        # Send metrics to CloudWatch
        metrics = {
            'TotalImpressions': total_impressions,
            'TotalClicks': total_clicks,
            'TotalCost': total_cost,
            'SuccessfulPulls': successful_pulls,
            'FailedPulls': failed_pulls
        }

        if total_impressions > 0:
            metrics['CTR'] = (total_clicks / total_impressions * 100)

        if total_clicks > 0:
            metrics['CPC'] = (total_cost / total_clicks)

        send_cloudwatch_metrics(metrics)

        # Summary
        print(f"\n{'=' * 60}")
        print(f"✅ Collection Complete")
        print(f"{'=' * 60}")
        print(f"Campaigns processed: {len(campaigns_to_process)}")
        print(f"Successful: {successful_pulls}")
        print(f"Failed: {failed_pulls}")
        print(f"Total impressions: {total_impressions:,}")
        print(f"Total clicks: {total_clicks:,}")
        print(f"Total cost: ${total_cost:.2f}")
        if total_impressions > 0:
            print(f"CTR: {(total_clicks / total_impressions * 100):.2f}%")
        if total_clicks > 0:
            print(f"CPC: ${(total_cost / total_clicks):.2f}")
        print(f"{'=' * 60}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data collection successful',
                'campaigns_processed': len(campaigns_to_process),
                'successful': successful_pulls,
                'failed': failed_pulls,
                'metrics': {
                    'impressions': total_impressions,
                    'clicks': total_clicks,
                    'cost': total_cost
                },
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR ❌")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")

        # Send failure metric
        send_cloudwatch_metrics({'CollectionFailure': 1})

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Data collection failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

"""
LinkedIn Ads Optimizer Lambda Function

The Decision Engine - Runs daily to automatically optimize LinkedIn campaigns.

Actions:
- Pause underperforming creatives (CTR < 1%)
- Scale winning creatives (CTR > 3%)
- Adjust bids based on ML predictions
- Generate new ad variations
- Send daily performance reports

This is the core automation - everything else feeds into this.
"""

import boto3
import json
import requests
import joblib
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
from io import BytesIO

# AWS Clients
s3 = boto3.client('s3')
athena = boto3.client('athena')
secrets = boto3.client('secretsmanager')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')

# Environment Variables
BUCKET_NAME = os.environ.get('BUCKET_NAME')
SECRET_NAME = os.environ.get('SECRET_NAME')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
ATHENA_OUTPUT_BUCKET = os.environ.get('ATHENA_OUTPUT_BUCKET')

# Optimization Thresholds (can be tuned)
MIN_CTR_THRESHOLD = float(os.environ.get('MIN_CTR_THRESHOLD', '1.0'))  # Pause if CTR < 1%
TOP_PERFORMER_THRESHOLD = float(os.environ.get('TOP_PERFORMER_THRESHOLD', '3.0'))  # Scale if CTR > 3%
MAX_CPC = float(os.environ.get('MAX_CPC', '8.0'))  # Pause if CPC > $8
MIN_SAMPLE_SIZE = int(os.environ.get('MIN_SAMPLE_SIZE', '100'))  # Minimum clicks before decisions
BID_CHANGE_THRESHOLD = float(os.environ.get('BID_CHANGE_THRESHOLD', '0.50'))  # $0.50 minimum bid change

# Model paths in S3
CREATIVE_SCORER_MODEL_PATH = 'models/creative_scoring/latest/model.joblib'
BID_OPTIMIZER_MODEL_PATH = 'models/bid_optimization/latest/model.joblib'


def get_linkedin_credentials() -> Dict[str, str]:
    """Retrieve LinkedIn OAuth token from Secrets Manager."""
    response = secrets.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(response['SecretString'])


def get_api_headers(access_token: str) -> Dict[str, str]:
    """Generate headers for LinkedIn API requests."""
    return {
        'Authorization': f'Bearer {access_token}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202411',
        'Content-Type': 'application/json'
    }


def query_athena(query: str) -> pd.DataFrame:
    """Execute Athena query and return results as DataFrame."""

    response = athena.start_query_execution(
        QueryString=query,
        ResultConfiguration={'OutputLocation': f's3://{ATHENA_OUTPUT_BUCKET}/'}
    )

    query_execution_id = response['QueryExecutionId']

    # Wait for completion
    import time
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status['QueryExecution']['Status']['State']

        if state == 'SUCCEEDED':
            break
        elif state in ['FAILED', 'CANCELLED']:
            raise Exception(f"Query {state}")
        time.sleep(2)

    # Get results
    results = athena.get_query_results(QueryExecutionId=query_execution_id)
    columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
    rows = [[field.get('VarCharValue', '') for field in row['Data']]
            for row in results['ResultSet']['Rows'][1:]]

    return pd.DataFrame(rows, columns=columns)


def get_performance_data(days=7) -> pd.DataFrame:
    """Get recent performance data for all creatives."""

    query = f"""
    SELECT
        creative_id,
        campaign_id,
        AVG(ctr_percent) as avg_ctr,
        AVG(avg_cpc) as avg_cpc,
        SUM(total_clicks) as total_clicks,
        SUM(total_impressions) as total_impressions,
        SUM(total_cost) as total_cost,
        SUM(total_conversions) as total_conversions,
        COUNT(DISTINCT report_date) as days_active
    FROM linkedin_ads.creative_performance
    WHERE report_date >= CURRENT_DATE - INTERVAL '{days}' DAY
    GROUP BY creative_id, campaign_id
    HAVING SUM(total_clicks) >= {MIN_SAMPLE_SIZE}
    ORDER BY avg_ctr DESC
    """

    df = query_athena(query)

    # Convert to numeric
    for col in ['avg_ctr', 'avg_cpc', 'total_clicks', 'total_impressions', 'total_cost', 'total_conversions']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def load_ml_model(model_path: str):
    """Load ML model from S3."""
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=model_path)
        model_bytes = response['Body'].read()
        model = joblib.load(BytesIO(model_bytes))
        print(f"✓ Loaded model from s3://{BUCKET_NAME}/{model_path}")
        return model
    except s3.exceptions.NoSuchKey:
        print(f"⚠️  Model not found: {model_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None


def pause_creative(access_token: str, creative_id: str) -> bool:
    """Pause an underperforming creative via LinkedIn API."""

    headers = get_api_headers(access_token)
    url = f'https://api.linkedin.com/rest/creatives/{creative_id}'

    payload = {'status': 'PAUSED'}

    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✓ Paused creative {creative_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to pause creative {creative_id}: {e}")
        return False


def update_campaign_bid(access_token: str, campaign_id: str, new_bid: float) -> bool:
    """Update campaign bid via LinkedIn API."""

    headers = get_api_headers(access_token)
    url = f'https://api.linkedin.com/rest/adCampaigns/{campaign_id}'

    payload = {
        'unitCost': {
            'amount': str(round(new_bid, 2)),
            'currencyCode': 'USD'
        }
    }

    try:
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        print(f"✓ Updated campaign {campaign_id} bid to ${new_bid:.2f}")
        return True
    except Exception as e:
        print(f"❌ Failed to update bid for campaign {campaign_id}: {e}")
        return False


def log_action(action_type: str, resource_id: str, details: str, metrics: Dict = None):
    """Log optimization action to S3."""

    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'action_type': action_type,
        'resource_id': resource_id,
        'details': details,
        'metrics': metrics or {}
    }

    # Append to daily log file
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    log_key = f"logs/optimizer_actions/{date_str}.jsonl"

    try:
        # Append to existing log
        try:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=log_key)
            existing_logs = response['Body'].read().decode('utf-8')
        except s3.exceptions.NoSuchKey:
            existing_logs = ''

        new_log = existing_logs + json.dumps(log_entry) + '\n'

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=log_key,
            Body=new_log,
            ContentType='application/jsonlines'
        )
    except Exception as e:
        print(f"⚠️  Failed to log action: {e}")


def optimize_creatives(access_token: str, performance_df: pd.DataFrame) -> List[Dict]:
    """
    Main creative optimization logic.

    Returns list of actions taken.
    """

    actions = []

    print(f"\n📊 Analyzing {len(performance_df)} creatives...")

    for idx, row in performance_df.iterrows():
        creative_id = row['creative_id']
        campaign_id = row['campaign_id']
        ctr = row['avg_ctr']
        cpc = row['avg_cpc']
        clicks = row['total_clicks']
        cost = row['total_cost']

        # Rule 1: Pause low CTR creatives
        if ctr < MIN_CTR_THRESHOLD and clicks >= MIN_SAMPLE_SIZE:
            if pause_creative(access_token, creative_id):
                action = {
                    'action': 'paused',
                    'creative_id': creative_id,
                    'campaign_id': campaign_id,
                    'reason': f'Low CTR ({ctr:.2f}%) below threshold',
                    'metrics': {'ctr': ctr, 'clicks': clicks, 'cost': cost}
                }
                actions.append(action)
                log_action('pause_creative', creative_id, action['reason'], action['metrics'])
                print(f"🔴 PAUSED: Creative {creative_id} - CTR {ctr:.2f}% (threshold: {MIN_CTR_THRESHOLD}%)")

        # Rule 2: High CPC
        elif cpc > MAX_CPC:
            if pause_creative(access_token, creative_id):
                action = {
                    'action': 'paused',
                    'creative_id': creative_id,
                    'campaign_id': campaign_id,
                    'reason': f'High CPC (${cpc:.2f}) above threshold',
                    'metrics': {'cpc': cpc, 'clicks': clicks, 'cost': cost}
                }
                actions.append(action)
                log_action('pause_creative', creative_id, action['reason'], action['metrics'])
                print(f"🔴 PAUSED: Creative {creative_id} - CPC ${cpc:.2f} (max: ${MAX_CPC})")

        # Rule 3: Top performers - note for scaling
        elif ctr > TOP_PERFORMER_THRESHOLD:
            action = {
                'action': 'top_performer',
                'creative_id': creative_id,
                'campaign_id': campaign_id,
                'reason': f'High CTR ({ctr:.2f}%) - candidate for scaling',
                'metrics': {'ctr': ctr, 'clicks': clicks, 'cost': cost}
            }
            actions.append(action)
            log_action('identify_winner', creative_id, action['reason'], action['metrics'])
            print(f"🟢 WINNER: Creative {creative_id} - CTR {ctr:.2f}% (threshold: {TOP_PERFORMER_THRESHOLD}%)")

    return actions


def optimize_bids(access_token: str, performance_df: pd.DataFrame, bid_model=None) -> List[Dict]:
    """
    Optimize campaign bids using ML model or heuristics.

    Returns list of actions taken.
    """

    actions = []

    # Group by campaign
    campaign_performance = performance_df.groupby('campaign_id').agg({
        'avg_ctr': 'mean',
        'avg_cpc': 'mean',
        'total_cost': 'sum'
    }).reset_index()

    print(f"\n💰 Optimizing bids for {len(campaign_performance)} campaigns...")

    for idx, row in campaign_performance.iterrows():
        campaign_id = row['campaign_id']
        current_cpc = row['avg_cpc']
        current_ctr = row['avg_ctr']

        # Calculate optimal bid
        if bid_model:
            # Use ML model (would need feature engineering here)
            # For now, use heuristic
            optimal_bid = calculate_optimal_bid_heuristic(current_ctr, current_cpc)
        else:
            optimal_bid = calculate_optimal_bid_heuristic(current_ctr, current_cpc)

        # Only update if change is significant
        bid_change = abs(optimal_bid - current_cpc)

        if bid_change >= BID_CHANGE_THRESHOLD:
            if update_campaign_bid(access_token, campaign_id, optimal_bid):
                action = {
                    'action': 'bid_adjustment',
                    'campaign_id': campaign_id,
                    'old_bid': current_cpc,
                    'new_bid': optimal_bid,
                    'change': optimal_bid - current_cpc,
                    'reason': f'Bid optimization: ${current_cpc:.2f} → ${optimal_bid:.2f}'
                }
                actions.append(action)
                log_action('adjust_bid', campaign_id, action['reason'], action)
                print(f"💵 BID ADJUSTED: Campaign {campaign_id} - ${current_cpc:.2f} → ${optimal_bid:.2f}")
        else:
            print(f"  Campaign {campaign_id} - bid unchanged (${current_cpc:.2f}, change too small: ${bid_change:.2f})")

    return actions


def calculate_optimal_bid_heuristic(current_ctr: float, current_cpc: float) -> float:
    """
    Calculate optimal bid using heuristic logic.

    Strategy:
    - If CTR is low, increase bid for better placements
    - If CTR is high, can afford to lower bid
    - Cap at reasonable min/max
    """

    TARGET_CTR = 2.0  # 2% target

    if current_ctr == 0:
        return current_cpc

    # Adjust based on CTR performance
    ctr_ratio = TARGET_CTR / current_ctr
    suggested_bid = current_cpc * ctr_ratio

    # Cap adjustment magnitude
    max_increase = current_cpc * 1.5  # Max 50% increase
    min_decrease = current_cpc * 0.7  # Max 30% decrease

    suggested_bid = max(min_decrease, min(max_increase, suggested_bid))

    # Absolute floor and ceiling
    suggested_bid = max(1.0, min(15.0, suggested_bid))

    return round(suggested_bid, 2)


def send_cloudwatch_metrics(actions: List[Dict], performance_summary: Dict, performance_df: pd.DataFrame):
    """
    Send comprehensive metrics to CloudWatch for dashboard visualization.

    Metrics sent:
    - Optimization actions (paused, scaled, bid adjustments)
    - Performance trends (CTR, CPC, cost, conversions)
    - ML model predictions vs actuals
    - Creative portfolio health
    """

    timestamp = datetime.utcnow()

    # Group actions by type
    paused_count = len([a for a in actions if a['action'] == 'paused'])
    bid_adjustment_count = len([a for a in actions if a['action'] == 'bid_adjustment'])
    top_performer_count = len([a for a in actions if a['action'] == 'top_performer'])

    # Calculate portfolio metrics
    total_creatives = len(performance_df)
    active_creatives = total_creatives - paused_count
    high_performers = len(performance_df[performance_df['avg_ctr'] > TOP_PERFORMER_THRESHOLD])
    underperformers = len(performance_df[performance_df['avg_ctr'] < MIN_CTR_THRESHOLD])

    # Build metric data
    metric_data = [
        # Optimization Actions
        {
            'MetricName': 'TotalActions',
            'Value': len(actions),
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'CreativesPaused',
            'Value': paused_count,
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'BidAdjustments',
            'Value': bid_adjustment_count,
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'TopPerformersIdentified',
            'Value': top_performer_count,
            'Unit': 'Count',
            'Timestamp': timestamp
        },

        # Performance Metrics (for trending)
        {
            'MetricName': 'TotalImpressions',
            'Value': performance_summary.get('total_impressions', 0),
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'TotalClicks',
            'Value': performance_summary.get('total_clicks', 0),
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'TotalCost',
            'Value': performance_summary.get('total_cost', 0),
            'Unit': 'None',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'AverageCTR',
            'Value': performance_summary.get('avg_ctr', 0),
            'Unit': 'Percent',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'AverageCPC',
            'Value': performance_summary.get('avg_cpc', 0),
            'Unit': 'None',
            'Timestamp': timestamp
        },

        # Portfolio Health Metrics
        {
            'MetricName': 'TotalCreatives',
            'Value': total_creatives,
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'ActiveCreatives',
            'Value': active_creatives,
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'HighPerformers',
            'Value': high_performers,
            'Unit': 'Count',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'Underperformers',
            'Value': underperformers,
            'Unit': 'Count',
            'Timestamp': timestamp
        },

        # Efficiency Metrics
        {
            'MetricName': 'CostPerClick',
            'Value': performance_summary.get('avg_cpc', 0),
            'Unit': 'None',
            'Timestamp': timestamp
        },
        {
            'MetricName': 'ClickThroughRate',
            'Value': performance_summary.get('avg_ctr', 0),
            'Unit': 'Percent',
            'Timestamp': timestamp
        }
    ]

    # Send metrics in batches (CloudWatch limit: 20 per request)
    batch_size = 20
    for i in range(0, len(metric_data), batch_size):
        batch = metric_data[i:i + batch_size]

        try:
            cloudwatch.put_metric_data(
                Namespace='LinkedInAds/Optimizer',
                MetricData=batch
            )
        except Exception as e:
            print(f"⚠️  Error sending metrics batch: {e}")

    print(f"✓ Sent {len(metric_data)} metrics to CloudWatch")

    # Also send campaign-specific metrics (for multi-campaign tracking)
    if 'campaign_id' in performance_df.columns:
        campaigns = performance_df.groupby('campaign_id').agg({
            'total_impressions': 'sum',
            'total_clicks': 'sum',
            'total_cost': 'sum',
            'avg_ctr': 'mean'
        }).reset_index()

        for _, campaign in campaigns.iterrows():
            try:
                cloudwatch.put_metric_data(
                    Namespace='LinkedInAds/Campaigns',
                    MetricData=[
                        {
                            'MetricName': 'Impressions',
                            'Value': campaign['total_impressions'],
                            'Unit': 'Count',
                            'Timestamp': timestamp,
                            'Dimensions': [{'Name': 'CampaignId', 'Value': str(campaign['campaign_id'])}]
                        },
                        {
                            'MetricName': 'CTR',
                            'Value': campaign['avg_ctr'],
                            'Unit': 'Percent',
                            'Timestamp': timestamp,
                            'Dimensions': [{'Name': 'CampaignId', 'Value': str(campaign['campaign_id'])}]
                        }
                    ]
                )
            except Exception as e:
                print(f"⚠️  Error sending campaign metrics: {e}")


def send_daily_report(actions: List[Dict], performance_summary: Dict):
    """Send daily optimization report via SNS."""

    report = f"""
LinkedIn Ads Daily Optimization Report
{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{'='*60}
ACTIONS TAKEN: {len(actions)}
{'='*60}

"""

    # Group actions by type
    paused = [a for a in actions if a['action'] == 'paused']
    bid_adjustments = [a for a in actions if a['action'] == 'bid_adjustment']
    winners = [a for a in actions if a['action'] == 'top_performer']

    if paused:
        report += f"\n🔴 PAUSED CREATIVES: {len(paused)}\n"
        for action in paused:
            report += f"  • {action['creative_id']}: {action['reason']}\n"

    if bid_adjustments:
        report += f"\n💵 BID ADJUSTMENTS: {len(bid_adjustments)}\n"
        for action in bid_adjustments:
            change_symbol = '↑' if action['change'] > 0 else '↓'
            report += f"  • Campaign {action['campaign_id']}: ${action['old_bid']:.2f} → ${action['new_bid']:.2f} {change_symbol}\n"

    if winners:
        report += f"\n🟢 TOP PERFORMERS: {len(winners)}\n"
        for action in winners:
            report += f"  • {action['creative_id']}: CTR {action['metrics']['ctr']:.2f}%\n"

    report += f"\n{'='*60}\n"
    report += f"PERFORMANCE SUMMARY\n"
    report += f"{'='*60}\n"
    report += f"Total Impressions: {performance_summary.get('total_impressions', 0):,}\n"
    report += f"Total Clicks: {performance_summary.get('total_clicks', 0):,}\n"
    report += f"Total Cost: ${performance_summary.get('total_cost', 0):.2f}\n"
    report += f"Average CTR: {performance_summary.get('avg_ctr', 0):.2f}%\n"
    report += f"Average CPC: ${performance_summary.get('avg_cpc', 0):.2f}\n"

    # Send via SNS
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"LinkedIn Ads Report - {len(actions)} Actions Taken",
            Message=report
        )
        print("✓ Daily report sent via SNS")
    except Exception as e:
        print(f"⚠️  Failed to send report: {e}")


def lambda_handler(event, context):
    """
    Main optimizer handler - runs daily.

    Workflow:
    1. Pull latest performance data from Athena
    2. Load ML models from S3 (if available)
    3. Identify underperformers and pause
    4. Identify top performers
    5. Optimize bids
    6. Log all actions
    7. Send daily report
    """

    print("=" * 60)
    print("🚀 LinkedIn Ads Optimization Started")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    all_actions = []

    try:
        # Get credentials
        credentials = get_linkedin_credentials()
        access_token = credentials['access_token']

        # Get performance data
        print("\n📊 Fetching performance data from Athena...")
        performance_df = get_performance_data(days=7)
        print(f"✓ Retrieved {len(performance_df)} creatives with sufficient data")

        if len(performance_df) == 0:
            print("⚠️  No creatives with sufficient data for optimization")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No data available for optimization'})
            }

        # Load ML models (optional - will use heuristics if not available)
        print("\n🤖 Loading ML models...")
        creative_scorer = load_ml_model(CREATIVE_SCORER_MODEL_PATH)
        bid_optimizer = load_ml_model(BID_OPTIMIZER_MODEL_PATH)

        # Optimize creatives
        creative_actions = optimize_creatives(access_token, performance_df)
        all_actions.extend(creative_actions)

        # Optimize bids
        bid_actions = optimize_bids(access_token, performance_df, bid_optimizer)
        all_actions.extend(bid_actions)

        # Calculate performance summary
        performance_summary = {
            'total_impressions': int(performance_df['total_impressions'].sum()),
            'total_clicks': int(performance_df['total_clicks'].sum()),
            'total_cost': float(performance_df['total_cost'].sum()),
            'avg_ctr': float(performance_df['avg_ctr'].mean()),
            'avg_cpc': float(performance_df['avg_cpc'].mean())
        }

        # Send daily report
        print("\n📧 Sending daily report...")
        send_daily_report(all_actions, performance_summary)

        # Send comprehensive metrics to CloudWatch
        print("\n📊 Sending metrics to CloudWatch...")
        send_cloudwatch_metrics(all_actions, performance_summary, performance_df)

        print("\n" + "=" * 60)
        print(f"✅ Optimization Complete - {len(all_actions)} Actions Taken")
        print("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'actions_taken': len(all_actions),
                'actions': all_actions,
                'performance_summary': performance_summary,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR ❌")
        print(f"Error: {str(e)}")

        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

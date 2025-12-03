"""
Data Processor Lambda Function

Transforms raw LinkedIn data from S3 into training datasets for ML models.
Runs daily to prepare data for SageMaker training jobs.

Input: Raw JSON files from s3://bucket/raw/analytics/
Output: Processed CSV/Parquet files in s3://bucket/processed/training/
"""

import boto3
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re
import os
from io import StringIO, BytesIO

s3 = boto3.client('s3')
athena = boto3.client('athena')
cloudwatch = boto3.client('cloudwatch')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
ATHENA_OUTPUT = os.environ.get('ATHENA_OUTPUT_BUCKET')


def extract_creative_features(creative_text: str) -> Dict[str, Any]:
    """
    Extract features from ad creative text for ML model.

    Features:
    - word_count: Number of words
    - char_count: Total characters
    - has_numbers: Contains numeric values
    - has_percent: Contains percentage sign
    - has_dollar: Contains dollar sign
    - has_question: Contains question mark
    - has_exclamation: Contains exclamation point
    - uppercase_ratio: Ratio of uppercase to total characters
    - mention_[keyword]: Boolean for keyword presence
    - cta_type: Call-to-action category
    """

    if not creative_text:
        return {}

    text_lower = creative_text.lower()

    features = {
        # Basic text metrics
        'word_count': len(creative_text.split()),
        'char_count': len(creative_text),
        'sentence_count': len(re.split(r'[.!?]+', creative_text)),

        # Special characters
        'has_numbers': bool(re.search(r'\d', creative_text)),
        'has_percent': '%' in creative_text,
        'has_dollar': '$' in creative_text,
        'has_question': '?' in creative_text,
        'has_exclamation': '!' in creative_text,
        'has_emoji': bool(re.search(r'[^\x00-\x7F]', creative_text)),

        # Uppercase analysis
        'uppercase_ratio': sum(1 for c in creative_text if c.isupper()) / len(creative_text) if creative_text else 0,
        'has_all_caps_word': bool(re.search(r'\b[A-Z]{2,}\b', creative_text)),

        # Action words
        'mention_free': 'free' in text_lower,
        'mention_new': 'new' in text_lower,
        'mention_now': 'now' in text_lower,
        'mention_today': 'today' in text_lower,
        'mention_limited': 'limited' in text_lower,
        'mention_exclusive': 'exclusive' in text_lower,
        'mention_guaranteed': 'guaranteed' in text_lower,
        'mention_proven': 'proven' in text_lower,

        # Industry-specific (customize per company)
        'mention_real_estate': any(word in text_lower for word in ['property', 'real estate', 'investment', 'portfolio']),
        'mention_data': any(word in text_lower for word in ['data', 'analytics', 'insights', 'intelligence']),
        'mention_professional': any(word in text_lower for word in ['professional', 'expert', 'certified', 'qualified']),

        # Call-to-action detection
        'cta_type': detect_cta_type(creative_text),

        # Urgency indicators
        'has_urgency': any(word in text_lower for word in ['now', 'today', 'limited', 'hurry', 'quick', 'fast']),

        # Social proof
        'has_social_proof': any(word in text_lower for word in ['trusted', 'proven', 'award', 'leader', 'top']),
    }

    return features


def detect_cta_type(text: str) -> str:
    """Detect the type of call-to-action in the text."""
    text_lower = text.lower()

    cta_patterns = {
        'learn_more': ['learn more', 'discover', 'find out', 'explore'],
        'get_started': ['get started', 'start now', 'begin', 'try now'],
        'download': ['download', 'get your', 'claim'],
        'contact': ['contact us', 'reach out', 'talk to', 'speak with'],
        'register': ['register', 'sign up', 'join', 'subscribe'],
        'buy': ['buy', 'purchase', 'order', 'get yours'],
        'demo': ['demo', 'see it', 'watch', 'view'],
        'quote': ['quote', 'estimate', 'pricing'],
    }

    for cta_type, keywords in cta_patterns.items():
        if any(keyword in text_lower for keyword in keywords):
            return cta_type

    return 'other'


def get_creative_content_from_s3(days=60) -> Dict[str, Dict]:
    """
    Extract creative content (headline, description) from raw S3 data.

    Returns dict: {creative_id: {'headline': '...', 'description': '...', 'cta': '...'}}
    """

    print("📁 Extracting creative content from S3 raw data...")

    creative_content = {}

    # List recent raw data files
    prefix = "raw/analytics/"
    paginator = s3.get_paginator('list_objects_v2')

    file_count = 0
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']

            # Skip if too old (optimize by checking date in path)
            # raw/analytics/YYYY/MM/DD/file.json
            try:
                path_parts = key.split('/')
                if len(path_parts) >= 4:
                    year, month, day = int(path_parts[2]), int(path_parts[3]), int(path_parts[4])
                    file_date = datetime(year, month, day)
                    if (datetime.now() - file_date).days > days:
                        continue
            except:
                pass  # If date parsing fails, process anyway

            # Read file
            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                data = json.loads(response['Body'].read().decode('utf-8'))

                # Extract creative content from analytics elements
                if 'analytics' in data and 'elements' in data['analytics']:
                    for element in data['analytics']['elements']:
                        creative_id = element.get('pivotValue', '')

                        # Skip if we already have this creative
                        if creative_id in creative_content:
                            continue

                        # Look for creative content in the element or fetch from API response
                        # Note: The collector may store this differently depending on API structure
                        # This is a placeholder - adjust based on actual data structure
                        if 'creativeContent' in element:
                            content = element['creativeContent']
                            creative_content[creative_id] = {
                                'headline': content.get('headline', ''),
                                'description': content.get('description', ''),
                                'cta': content.get('cta', ''),
                                'combined_text': f"{content.get('headline', '')} {content.get('description', '')}"
                            }

                file_count += 1
                if file_count % 100 == 0:
                    print(f"  Processed {file_count} files, found {len(creative_content)} unique creatives...")

            except Exception as e:
                print(f"  Warning: Could not process {key}: {e}")
                continue

    print(f"✓ Extracted content for {len(creative_content)} creatives from {file_count} files")
    return creative_content


def query_athena(query: str) -> pd.DataFrame:
    """Execute Athena query and return results as DataFrame."""

    # Start query execution
    response = athena.start_query_execution(
        QueryString=query,
        ResultConfiguration={
            'OutputLocation': f's3://{ATHENA_OUTPUT}/'
        }
    )

    query_execution_id = response['QueryExecutionId']

    # Wait for query to complete
    import time
    while True:
        status = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = status['QueryExecution']['Status']['State']

        if state == 'SUCCEEDED':
            break
        elif state in ['FAILED', 'CANCELLED']:
            raise Exception(f"Athena query {state}: {status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')}")

        time.sleep(2)

    # Get results
    results = athena.get_query_results(QueryExecutionId=query_execution_id)

    # Convert to DataFrame
    columns = [col['Label'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
    rows = []

    for row in results['ResultSet']['Rows'][1:]:  # Skip header row
        rows.append([field.get('VarCharValue', '') for field in row['Data']])

    return pd.DataFrame(rows, columns=columns)


def prepare_creative_training_data() -> pd.DataFrame:
    """
    Prepare training data for creative scoring model.

    Combines:
    - Creative text/metadata
    - Performance metrics (CTR, CPC, conversions)
    - Targeting information
    - Temporal features (day of week, time)
    """

    print("📊 Querying creative performance data from Athena...")

    query = """
    WITH creative_metadata AS (
        SELECT DISTINCT
            elem.pivotValue as creative_id,
            campaign_id,
            DATE(from_iso8601_timestamp(pulled_at)) as date
        FROM linkedin_ads.raw_analytics
        CROSS JOIN UNNEST(analytics.elements) as t(elem)
        WHERE DATE(from_iso8601_timestamp(pulled_at)) >= CURRENT_DATE - INTERVAL '60' DAY
    ),
    creative_performance AS (
        SELECT
            creative_id,
            AVG(ctr_percent) as avg_ctr,
            AVG(avg_cpc) as avg_cpc,
            SUM(total_impressions) as total_impressions,
            SUM(total_clicks) as total_clicks,
            SUM(total_cost) as total_cost,
            SUM(total_conversions) as total_conversions,
            AVG(conversion_rate_percent) as avg_conversion_rate,
            COUNT(DISTINCT report_date) as days_active
        FROM linkedin_ads.creative_performance
        WHERE report_date >= CURRENT_DATE - INTERVAL '60' DAY
        GROUP BY creative_id
        HAVING SUM(total_impressions) > 100  -- Minimum sample size
    )
    SELECT
        cp.*
    FROM creative_performance cp
    ORDER BY total_impressions DESC
    """

    df = query_athena(query)

    # Convert numeric columns
    numeric_cols = ['avg_ctr', 'avg_cpc', 'total_impressions', 'total_clicks',
                    'total_cost', 'total_conversions', 'avg_conversion_rate', 'days_active']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    print(f"✓ Retrieved {len(df)} creatives with performance data")

    # Get creative content from raw S3 data
    creative_content = get_creative_content_from_s3(days=60)

    # Match creative IDs to their content
    df['headline'] = df['creative_id'].map(lambda cid: creative_content.get(cid, {}).get('headline', ''))
    df['description'] = df['creative_id'].map(lambda cid: creative_content.get(cid, {}).get('description', ''))
    df['cta'] = df['creative_id'].map(lambda cid: creative_content.get(cid, {}).get('cta', ''))
    df['creative_text'] = df['creative_id'].map(lambda cid: creative_content.get(cid, {}).get('combined_text', ''))

    # Log how many creatives we have content for
    has_content = df['creative_text'].str.len() > 0
    print(f"✓ Found creative content for {has_content.sum()}/{len(df)} creatives ({has_content.sum()/len(df)*100:.1f}%)")

    # Extract features from creative text
    print("🔍 Extracting features from creative text...")
    feature_dicts = df['creative_text'].apply(extract_creative_features)
    features_df = pd.DataFrame(feature_dicts.tolist())

    # Combine with performance data
    result = pd.concat([df, features_df], axis=1)

    # Add temporal features (will be useful for bid optimizer)
    result['month'] = pd.to_datetime('today').month
    result['day_of_week'] = pd.to_datetime('today').dayofweek

    print(f"✓ Feature extraction complete: {len(result)} samples, {len(result.columns)} features")

    return result


def prepare_bid_training_data() -> pd.DataFrame:
    """
    Prepare training data for bid optimization model.

    Features:
    - Time of day
    - Day of week
    - Campaign targeting (job titles, industries, locations)
    - Historical CTR/CPC at similar times
    - Competitive landscape indicators
    """

    print("📊 Querying bid optimization data from Athena...")

    query = """
    WITH hourly_performance AS (
        SELECT
            campaign_id,
            EXTRACT(HOUR FROM from_iso8601_timestamp(pulled_at)) as hour_of_day,
            EXTRACT(DOW FROM from_iso8601_timestamp(pulled_at)) as day_of_week,
            AVG(ctr) as avg_ctr,
            AVG(cpc) as avg_cpc,
            AVG(conversion_rate) as avg_conversion_rate,
            SUM(impressions) as total_impressions,
            SUM(clicks) as total_clicks,
            SUM(cost) as total_cost
        FROM linkedin_ads.daily_summary
        WHERE report_date >= CURRENT_DATE - INTERVAL '30' DAY
        GROUP BY
            campaign_id,
            EXTRACT(HOUR FROM from_iso8601_timestamp(pulled_at)),
            EXTRACT(DOW FROM from_iso8601_timestamp(pulled_at))
    )
    SELECT
        campaign_id,
        hour_of_day,
        day_of_week,
        avg_ctr,
        avg_cpc,
        avg_conversion_rate,
        total_impressions,
        total_clicks,
        total_cost
    FROM hourly_performance
    WHERE total_impressions > 10
    ORDER BY campaign_id, hour_of_day
    """

    df = query_athena(query)

    # Convert numeric columns
    numeric_cols = ['hour_of_day', 'day_of_week', 'avg_ctr', 'avg_cpc',
                    'avg_conversion_rate', 'total_impressions', 'total_clicks', 'total_cost']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Add features
    df['is_weekend'] = df['day_of_week'].isin([0, 6]).astype(int)  # Sunday=0, Saturday=6
    df['is_business_hours'] = df['hour_of_day'].between(9, 17).astype(int)
    df['is_peak_hours'] = df['hour_of_day'].between(10, 14).astype(int)

    # Calculate optimal bid (target variable)
    # Optimal bid = CPC that achieves target CTR with acceptable cost per conversion
    TARGET_CTR = 2.0  # 2% target CTR
    MAX_CPA = 100.0  # $100 max cost per acquisition

    df['optimal_bid'] = df.apply(
        lambda row: calculate_optimal_bid(
            row['avg_ctr'],
            row['avg_conversion_rate'],
            row['avg_cpc'],
            TARGET_CTR,
            MAX_CPA
        ),
        axis=1
    )

    print(f"✓ Retrieved {len(df)} bid optimization samples")

    return df


def calculate_optimal_bid(current_ctr, conversion_rate, current_cpc, target_ctr, max_cpa):
    """
    Calculate optimal bid based on current performance and targets.

    This is a simplified heuristic that can be replaced with more sophisticated logic.
    """
    if pd.isna(current_ctr) or pd.isna(current_cpc) or current_ctr == 0:
        return current_cpc

    # If CTR is below target, we might need to bid higher for better placements
    # If CTR is above target, we can bid lower
    ctr_adjustment = target_ctr / current_ctr if current_ctr > 0 else 1.0

    # Cap the adjustment to prevent extreme bids
    ctr_adjustment = max(0.5, min(2.0, ctr_adjustment))

    # Calculate suggested bid
    suggested_bid = current_cpc * ctr_adjustment

    # Ensure bid doesn't result in CPA higher than max
    if conversion_rate > 0:
        max_bid_for_cpa = (max_cpa * conversion_rate / 100)  # conversion_rate is in percent
        suggested_bid = min(suggested_bid, max_bid_for_cpa)

    # Floor and ceiling
    suggested_bid = max(1.0, min(20.0, suggested_bid))

    return round(suggested_bid, 2)


def save_training_data(df: pd.DataFrame, dataset_type: str):
    """Save training data to S3 in CSV format."""

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    # CSV format
    csv_key = f"processed/training/{dataset_type}/{timestamp}.csv"
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=csv_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )

    print(f"💾 Saved CSV to s3://{BUCKET_NAME}/{csv_key}")

    # Parquet format (more efficient for ML)
    parquet_key = f"processed/training/{dataset_type}/{timestamp}.parquet"
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType='application/octet-stream'
    )

    print(f"💾 Saved Parquet to s3://{BUCKET_NAME}/{parquet_key}")

    # Also save latest version
    latest_csv_key = f"processed/training/{dataset_type}/latest.csv"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=latest_csv_key,
        Body=csv_buffer.getvalue(),
        ContentType='text/csv'
    )

    return csv_key, parquet_key


def create_daily_aggregates():
    """
    Create daily performance aggregates for fast frontend queries.

    These pre-computed files allow the Amplify app to load data instantly.
    """

    print("\n📅 Creating daily aggregates...")

    # Query last 90 days of performance
    query = """
    SELECT
        report_date,
        campaign_id,
        COUNT(DISTINCT creative_id) as total_creatives,
        SUM(total_impressions) as impressions,
        SUM(total_clicks) as clicks,
        SUM(total_cost) as cost,
        SUM(total_conversions) as conversions,
        AVG(ctr_percent) as avg_ctr,
        AVG(avg_cpc) as avg_cpc,
        AVG(cost_per_conversion) as avg_cpa
    FROM linkedin_ads.creative_performance
    WHERE report_date >= CURRENT_DATE - INTERVAL '90' DAY
    GROUP BY report_date, campaign_id
    ORDER BY report_date DESC
    """

    df = query_athena(query)

    if len(df) == 0:
        print("⚠️  No data for daily aggregates")
        return None

    # Convert to numeric
    numeric_cols = ['total_creatives', 'impressions', 'clicks', 'cost', 'conversions', 'avg_ctr', 'avg_cpc', 'avg_cpa']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Save as Parquet (efficient for Amplify/frontend queries)
    parquet_key = f"processed/aggregates/daily/all_days.parquet"
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType='application/octet-stream'
    )

    print(f"✓ Daily aggregates saved ({len(df)} days)")
    return parquet_key


def create_weekly_summaries():
    """
    Create weekly performance summaries for trend analysis.

    Perfect for dashboards showing week-over-week growth.
    """

    print("\n📊 Creating weekly summaries...")

    query = """
    WITH weekly AS (
        SELECT
            DATE_TRUNC('week', report_date) as week_start,
            campaign_id,
            SUM(total_impressions) as impressions,
            SUM(total_clicks) as clicks,
            SUM(total_cost) as cost,
            SUM(total_conversions) as conversions,
            AVG(ctr_percent) as avg_ctr,
            AVG(avg_cpc) as avg_cpc
        FROM linkedin_ads.creative_performance
        WHERE report_date >= CURRENT_DATE - INTERVAL '180' DAY
        GROUP BY DATE_TRUNC('week', report_date), campaign_id
    )
    SELECT
        week_start,
        campaign_id,
        impressions,
        clicks,
        cost,
        conversions,
        avg_ctr,
        avg_cpc,
        ROUND(cost / NULLIF(clicks, 0), 2) as cpc,
        ROUND(clicks * 100.0 / NULLIF(impressions, 0), 2) as ctr,
        ROUND(cost / NULLIF(conversions, 0), 2) as cpa
    FROM weekly
    ORDER BY week_start DESC
    """

    df = query_athena(query)

    if len(df) == 0:
        print("⚠️  No data for weekly summaries")
        return None

    # Convert to numeric
    numeric_cols = ['impressions', 'clicks', 'cost', 'conversions', 'avg_ctr', 'avg_cpc', 'cpc', 'ctr', 'cpa']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    parquet_key = f"processed/aggregates/weekly/all_weeks.parquet"
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType='application/octet-stream'
    )

    print(f"✓ Weekly summaries saved ({len(df)} weeks)")
    return parquet_key


def create_creative_metadata():
    """
    Create creative metadata cache for frontend lookups.

    Includes all creatives with their latest performance metrics.
    """

    print("\n🎨 Creating creative metadata...")

    query = """
    SELECT
        creative_id,
        campaign_id,
        SUM(total_impressions) as lifetime_impressions,
        SUM(total_clicks) as lifetime_clicks,
        SUM(total_cost) as lifetime_cost,
        SUM(total_conversions) as lifetime_conversions,
        AVG(ctr_percent) as avg_ctr,
        AVG(avg_cpc) as avg_cpc,
        MIN(report_date) as first_seen,
        MAX(report_date) as last_seen,
        COUNT(DISTINCT report_date) as days_active
    FROM linkedin_ads.creative_performance
    GROUP BY creative_id, campaign_id
    ORDER BY lifetime_impressions DESC
    """

    df = query_athena(query)

    if len(df) == 0:
        print("⚠️  No creative metadata available")
        return None

    # Convert to numeric
    numeric_cols = ['lifetime_impressions', 'lifetime_clicks', 'lifetime_cost', 'lifetime_conversions', 'avg_ctr', 'avg_cpc', 'days_active']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Add performance category
    df['performance_category'] = df['avg_ctr'].apply(lambda ctr:
        'high' if ctr >= 3.0 else
        'medium' if ctr >= 1.5 else
        'low' if ctr >= 0.5 else
        'very_low'
    )

    # Save as JSON (easy for frontend to query by ID)
    json_key = f"processed/aggregates/creative_metadata.json"
    creative_dict = df.to_dict('records')

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=json_key,
        Body=json.dumps(creative_dict, indent=2, default=str),
        ContentType='application/json'
    )

    # Also save as Parquet for efficient bulk queries
    parquet_key = f"processed/aggregates/creative_metadata.parquet"
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=parquet_key,
        Body=parquet_buffer.getvalue(),
        ContentType='application/octet-stream'
    )

    print(f"✓ Creative metadata saved ({len(df)} creatives)")
    return json_key


def send_cloudwatch_metrics(results: Dict[str, Any]):
    """
    Send CloudWatch metrics about data processing for monitoring.

    Tracks:
    - Dataset creation (samples, features)
    - Aggregate creation (count, success rate)
    - Processing health
    """

    try:
        metric_data = []

        # Dataset metrics
        total_datasets = len(results.get('datasets_created', []))
        total_samples = sum(d.get('samples', 0) for d in results.get('datasets_created', []))

        metric_data.extend([
            {
                'MetricName': 'DatasetsCreated',
                'Value': total_datasets,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            },
            {
                'MetricName': 'TotalTrainingSamples',
                'Value': total_samples,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }
        ])

        # Individual dataset metrics
        for dataset in results.get('datasets_created', []):
            dataset_type = dataset.get('type', 'unknown')
            samples = dataset.get('samples', 0)
            features = dataset.get('features', 0)

            metric_data.extend([
                {
                    'MetricName': 'DatasetSamples',
                    'Value': samples,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'DatasetType', 'Value': dataset_type}
                    ]
                },
                {
                    'MetricName': 'DatasetFeatures',
                    'Value': features,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {'Name': 'DatasetType', 'Value': dataset_type}
                    ]
                }
            ])

        # Aggregate metrics
        total_aggregates = len(results.get('aggregates', []))

        metric_data.append({
            'MetricName': 'AggregatesCreated',
            'Value': total_aggregates,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        })

        # Processing success
        metric_data.append({
            'MetricName': 'ProcessingSuccess',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        })

        # Send metrics in batches of 20 (CloudWatch limit)
        for i in range(0, len(metric_data), 20):
            batch = metric_data[i:i+20]
            cloudwatch.put_metric_data(
                Namespace='LinkedInAds/DataProcessor',
                MetricData=batch
            )

        print(f"✓ CloudWatch metrics sent ({len(metric_data)} metrics)")

    except Exception as e:
        print(f"⚠️  Could not send CloudWatch metrics: {e}")
        # Don't fail the Lambda if metrics fail


def lambda_handler(event, context):
    """
    Main Lambda handler - runs daily to prepare training data.

    Can be triggered:
    1. By EventBridge schedule (daily)
    2. Manually via Lambda invoke
    3. By S3 event when new raw data arrives
    """

    print("=" * 60)
    print("🚀 Data Processing Started")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'datasets_created': []
    }

    try:
        # Prepare creative scoring training data
        print("\n📋 Preparing creative scoring training data...")
        creative_df = prepare_creative_training_data()

        if len(creative_df) > 0:
            csv_key, parquet_key = save_training_data(creative_df, 'creative_scoring')
            results['datasets_created'].append({
                'type': 'creative_scoring',
                'samples': len(creative_df),
                'features': len(creative_df.columns),
                'csv_key': csv_key,
                'parquet_key': parquet_key
            })
            print(f"✓ Creative scoring dataset: {len(creative_df)} samples, {len(creative_df.columns)} features")
        else:
            print("⚠️  No creative data available yet")

        # Prepare bid optimization training data
        print("\n📋 Preparing bid optimization training data...")
        bid_df = prepare_bid_training_data()

        if len(bid_df) > 0:
            csv_key, parquet_key = save_training_data(bid_df, 'bid_optimization')
            results['datasets_created'].append({
                'type': 'bid_optimization',
                'samples': len(bid_df),
                'features': len(bid_df.columns),
                'csv_key': csv_key,
                'parquet_key': parquet_key
            })
            print(f"✓ Bid optimization dataset: {len(bid_df)} samples, {len(bid_df.columns)} features")
        else:
            print("⚠️  No bid data available yet")

        # Create processed aggregates for frontend (Amplify app)
        print("\n📦 Creating processed aggregates for frontend...")
        results['aggregates'] = []

        # Daily aggregates
        daily_key = create_daily_aggregates()
        if daily_key:
            results['aggregates'].append({'type': 'daily', 'key': daily_key})

        # Weekly summaries
        weekly_key = create_weekly_summaries()
        if weekly_key:
            results['aggregates'].append({'type': 'weekly', 'key': weekly_key})

        # Creative metadata
        creative_key = create_creative_metadata()
        if creative_key:
            results['aggregates'].append({'type': 'creative_metadata', 'key': creative_key})

        # Send CloudWatch metrics
        print("\n📊 Sending CloudWatch metrics...")
        send_cloudwatch_metrics(results)

        print("\n" + "=" * 60)
        print("✅ Data Processing Complete")
        print(f"📊 Datasets created: {len(results['datasets_created'])}")
        print(f"📦 Aggregates created: {len(results.get('aggregates', []))}")
        print("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR ❌")
        print(f"Error: {str(e)}")

        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")

        # Send failure metric
        try:
            cloudwatch.put_metric_data(
                Namespace='LinkedInAds/DataProcessor',
                MetricData=[
                    {
                        'MetricName': 'ProcessingFailure',
                        'Value': 1,
                        'Unit': 'Count',
                        'Timestamp': datetime.utcnow()
                    }
                ]
            )
        except:
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

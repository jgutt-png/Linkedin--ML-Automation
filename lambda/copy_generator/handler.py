"""
Ad Copy Generator Lambda Function

Uses Claude API to generate new ad copy variations based on winning patterns.

Triggered by:
- Manual invocation
- Optimizer Lambda when top performers identified
- Scheduled weekly generation

Input: Winning creative IDs or patterns
Output: New ad copy variations ready to test
"""

import boto3
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from anthropic import Anthropic

# AWS Clients
s3 = boto3.client('s3')
secrets = boto3.client('secretsmanager')
athena = boto3.client('athena')

# Environment Variables
BUCKET_NAME = os.environ.get('BUCKET_NAME')
ANTHROPIC_API_KEY_SECRET = os.environ.get('ANTHROPIC_API_KEY_SECRET', 'anthropic-api-key')
ATHENA_OUTPUT_BUCKET = os.environ.get('ATHENA_OUTPUT_BUCKET')


def get_anthropic_api_key() -> str:
    """Retrieve Anthropic API key from Secrets Manager."""
    try:
        response = secrets.get_secret_value(SecretId=ANTHROPIC_API_KEY_SECRET)
        secret = json.loads(response['SecretString'])
        return secret.get('api_key', secret.get('anthropic_api_key', ''))
    except Exception as e:
        print(f"❌ Error retrieving Anthropic API key: {e}")
        raise


def get_winning_creatives(days=30, min_ctr=3.0) -> List[Dict]:
    """
    Query Athena for top-performing creatives.

    Returns creative IDs and their metrics.
    """

    query = f"""
    SELECT
        creative_id,
        campaign_id,
        AVG(ctr_percent) as avg_ctr,
        AVG(avg_cpc) as avg_cpc,
        SUM(total_clicks) as total_clicks,
        SUM(total_conversions) as total_conversions
    FROM linkedin_ads.creative_performance
    WHERE
        report_date >= CURRENT_DATE - INTERVAL '{days}' DAY
        AND ctr_percent >= {min_ctr}
    GROUP BY creative_id, campaign_id
    HAVING SUM(total_clicks) > 100
    ORDER BY avg_ctr DESC
    LIMIT 10
    """

    # Execute query
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
            raise Exception(f"Query failed: {state}")
        time.sleep(2)

    # Get results
    results = athena.get_query_results(QueryExecutionId=query_execution_id)

    creatives = []
    for row in results['ResultSet']['Rows'][1:]:  # Skip header
        creatives.append({
            'creative_id': row['Data'][0].get('VarCharValue', ''),
            'campaign_id': row['Data'][1].get('VarCharValue', ''),
            'avg_ctr': float(row['Data'][2].get('VarCharValue', 0)),
            'avg_cpc': float(row['Data'][3].get('VarCharValue', 0)),
            'total_clicks': int(row['Data'][4].get('VarCharValue', 0)),
            'total_conversions': int(row['Data'][5].get('VarCharValue', 0))
        })

    print(f"✓ Found {len(creatives)} winning creatives")
    return creatives


def analyze_winning_patterns(creatives: List[Dict]) -> Dict[str, Any]:
    """
    Analyze common patterns in winning creatives.

    This is a placeholder - in production, you'd fetch actual creative text
    from LinkedIn API or metadata storage.
    """

    patterns = {
        'avg_ctr': sum(c['avg_ctr'] for c in creatives) / len(creatives) if creatives else 0,
        'avg_cpc': sum(c['avg_cpc'] for c in creatives) / len(creatives) if creatives else 0,
        'total_conversions': sum(c['total_conversions'] for c in creatives),
        'sample_size': len(creatives)
    }

    # In production, analyze:
    # - Common words/phrases
    # - Headline structures
    # - Call-to-action types
    # - Emotional triggers
    # - Length patterns

    patterns['insights'] = [
        f"Top performers average {patterns['avg_ctr']:.2f}% CTR",
        f"Successful creatives maintain CPC around ${patterns['avg_cpc']:.2f}",
        f"Total conversions from these creatives: {patterns['total_conversions']}"
    ]

    return patterns


def generate_ad_copy_with_claude(
    product_info: str,
    target_audience: str,
    winning_patterns: Dict,
    num_variations: int = 5
) -> List[Dict[str, str]]:
    """
    Generate new ad copy variations using Claude API.

    Returns list of ad copy variations with headlines and descriptions.
    """

    print("🤖 Generating ad copy with Claude...")

    # Get API key
    api_key = get_anthropic_api_key()
    client = Anthropic(api_key=api_key)

    # Build prompt based on winning patterns
    prompt = f"""You are an expert LinkedIn advertising copywriter specializing in B2B marketing.

Your task is to generate {num_variations} highly effective LinkedIn ad copy variations.

CONTEXT:
Product/Service: {product_info}
Target Audience: {target_audience}

WINNING PATTERNS FROM TOP PERFORMERS:
- Average CTR of successful ads: {winning_patterns.get('avg_ctr', 0):.2f}%
- These ads generated {winning_patterns.get('total_conversions', 0)} total conversions
- Key insights: {', '.join(winning_patterns.get('insights', []))}

REQUIREMENTS:
1. Each variation should include:
   - A compelling headline (max 70 characters)
   - A description (max 150 characters)
   - A clear call-to-action

2. Use proven B2B copywriting techniques:
   - Lead with value proposition
   - Address specific pain points
   - Include social proof indicators
   - Create urgency without being pushy
   - Use specific numbers/data points when possible

3. Variations should test different angles:
   - Problem-solution approach
   - Benefit-focused
   - Social proof/credibility
   - Urgency/scarcity
   - Question-based engagement

4. Optimize for LinkedIn's professional audience:
   - Professional tone
   - Industry-relevant language
   - Decision-maker focus

OUTPUT FORMAT:
Return a JSON array with {num_variations} variations, each with this structure:
{{
  "headline": "Compelling headline here",
  "description": "Engaging description that expands on the headline",
  "cta": "Clear call-to-action",
  "angle": "Brief description of the copywriting angle used"
}}

Generate the variations now:"""

    # Call Claude API
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract JSON from response
        response_text = message.content[0].text

        # Try to parse JSON
        # Claude might wrap it in markdown code blocks
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()

        variations = json.loads(response_text)

        print(f"✓ Generated {len(variations)} ad copy variations")
        return variations

    except Exception as e:
        print(f"❌ Error generating copy with Claude: {e}")
        return []


def save_generated_copy(variations: List[Dict], metadata: Dict):
    """Save generated ad copy to S3 for review and deployment."""

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    key = f"generated_copy/{timestamp}.json"

    payload = {
        'generated_at': datetime.utcnow().isoformat(),
        'num_variations': len(variations),
        'metadata': metadata,
        'variations': variations
    }

    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(payload, indent=2),
            ContentType='application/json'
        )

        print(f"💾 Saved generated copy to s3://{BUCKET_NAME}/{key}")

        # Also save as "latest" for easy access
        latest_key = "generated_copy/latest.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=latest_key,
            Body=json.dumps(payload, indent=2),
            ContentType='application/json'
        )

        return key

    except Exception as e:
        print(f"❌ Error saving generated copy: {e}")
        return None


def lambda_handler(event, context):
    """
    Main copy generator handler.

    Can be triggered:
    1. Manually via Lambda invoke
    2. By optimizer Lambda when winners identified
    3. On schedule (e.g., weekly)

    Event parameters (optional):
    - product_info: Description of product/service
    - target_audience: Description of target audience
    - num_variations: Number of variations to generate (default: 5)
    """

    print("=" * 60)
    print("🚀 Ad Copy Generation Started")
    print(f"⏰ Timestamp: {datetime.utcnow().isoformat()}")
    print("=" * 60)

    try:
        # Get parameters from event or use defaults
        product_info = event.get('product_info',
            "YOUR_PRODUCT_DESCRIPTION that helps investors find off-market deals and distressed properties")

        target_audience = event.get('target_audience',
            "YOUR_TARGET_AUDIENCE (e.g., professionals in your target industry)")

        num_variations = event.get('num_variations', 5)

        # Get winning creatives
        print("\n📊 Analyzing winning creatives...")
        winning_creatives = get_winning_creatives(days=30, min_ctr=3.0)

        if not winning_creatives:
            print("⚠️  No winning creatives found with sufficient data")
            # Generate based on general best practices
            winning_patterns = {
                'avg_ctr': 2.5,
                'avg_cpc': 5.0,
                'total_conversions': 0,
                'insights': ["Using general best practices for LinkedIn B2B ads"]
            }
        else:
            # Analyze patterns
            winning_patterns = analyze_winning_patterns(winning_creatives)

        # Generate new copy variations
        print("\n✍️  Generating new ad copy variations...")
        variations = generate_ad_copy_with_claude(
            product_info=product_info,
            target_audience=target_audience,
            winning_patterns=winning_patterns,
            num_variations=num_variations
        )

        if not variations:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to generate ad copy'})
            }

        # Save to S3
        print("\n💾 Saving generated copy...")
        s3_key = save_generated_copy(variations, {
            'product_info': product_info,
            'target_audience': target_audience,
            'winning_patterns': winning_patterns
        })

        # Print samples
        print("\n📋 Generated Variations:")
        print("=" * 60)
        for i, var in enumerate(variations[:3], 1):  # Show first 3
            print(f"\nVariation {i} ({var.get('angle', 'N/A')}):")
            print(f"  Headline: {var.get('headline', 'N/A')}")
            print(f"  Description: {var.get('description', 'N/A')}")
            print(f"  CTA: {var.get('cta', 'N/A')}")

        print("\n" + "=" * 60)
        print(f"✅ Copy Generation Complete - {len(variations)} Variations Created")
        print("=" * 60)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'num_variations': len(variations),
                'variations': variations,
                's3_key': s3_key,
                'winning_patterns': winning_patterns,
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

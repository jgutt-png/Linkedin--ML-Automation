#!/bin/bash
set -e

# LinkedIn Ads ML Pipeline - Athena Database Setup
# Creates database, tables, and views for querying LinkedIn Ads data

# Configuration
REGION="${AWS_REGION:-us-east-2}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="linkedin-ads-data-${ACCOUNT_ID}"
ATHENA_OUTPUT="linkedin-ads-athena-results-${ACCOUNT_ID}"

echo "=========================================="
echo "Athena Database Setup"
echo "=========================================="
echo "Region: ${REGION}"
echo "Data Bucket: ${BUCKET_NAME}"
echo "Output Bucket: ${ATHENA_OUTPUT}"
echo ""

# Ensure Athena output bucket exists
if ! aws s3 ls "s3://${ATHENA_OUTPUT}" 2>/dev/null; then
  echo "Creating Athena output bucket..."
  aws s3 mb "s3://${ATHENA_OUTPUT}" --region "${REGION}"
fi

# Function to run Athena query
run_query() {
  local query=$1
  local description=$2

  echo "📊 ${description}..."

  # Start query execution
  QUERY_ID=$(aws athena start-query-execution \
    --query-string "${query}" \
    --result-configuration "OutputLocation=s3://${ATHENA_OUTPUT}/" \
    --region "${REGION}" \
    --query 'QueryExecutionId' \
    --output text)

  # Wait for completion
  while true; do
    STATUS=$(aws athena get-query-execution \
      --query-execution-id "${QUERY_ID}" \
      --region "${REGION}" \
      --query 'QueryExecution.Status.State' \
      --output text)

    if [ "${STATUS}" == "SUCCEEDED" ]; then
      echo "  ✓ Success"
      break
    elif [ "${STATUS}" == "FAILED" ] || [ "${STATUS}" == "CANCELLED" ]; then
      REASON=$(aws athena get-query-execution \
        --query-execution-id "${QUERY_ID}" \
        --region "${REGION}" \
        --query 'QueryExecution.Status.StateChangeReason' \
        --output text)
      echo "  ❌ Failed: ${REASON}"
      return 1
    fi

    sleep 2
  done
}

# Create database
echo ""
echo "Step 1: Creating Database"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

run_query "CREATE DATABASE IF NOT EXISTS linkedin_ads;" \
  "Creating linkedin_ads database"

echo ""
echo "Step 2: Creating Raw Analytics Table"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create external table for raw analytics data
RAW_TABLE_QUERY="
CREATE EXTERNAL TABLE IF NOT EXISTS linkedin_ads.raw_analytics (
  pulled_at STRING,
  campaign_id STRING,
  date_range STRUCT<
    start: STRING,
    end: STRING
  >,
  analytics STRUCT<
    elements: ARRAY<STRUCT<
      pivotValue: STRING,
      dateRange: STRUCT<
        start: STRUCT<day: INT, month: INT, year: INT>,
        end: STRUCT<day: INT, month: INT, year: INT>
      >,
      impressions: BIGINT,
      clicks: BIGINT,
      costInUsd: DOUBLE,
      externalWebsiteConversions: BIGINT,
      approximateUniqueImpressions: BIGINT
    >>
  >,
  campaign_config STRUCT<
    id: STRING,
    name: STRING,
    status: STRING,
    dailyBudget: STRUCT<amount: DOUBLE, currencyCode: STRING>,
    unitCost: STRUCT<amount: DOUBLE, currencyCode: STRING>
  >
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true'
)
LOCATION 's3://${BUCKET_NAME}/raw/analytics/'
"

run_query "${RAW_TABLE_QUERY}" "Creating raw_analytics table"

echo ""
echo "Step 3: Creating Performance Views"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create creative performance view
CREATIVE_PERF_VIEW="
CREATE OR REPLACE VIEW linkedin_ads.creative_performance AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  elem.pivotValue as creative_id,
  SUM(elem.impressions) as total_impressions,
  SUM(elem.clicks) as total_clicks,
  SUM(elem.costInUsd) as total_cost,
  SUM(elem.externalWebsiteConversions) as total_conversions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr_percent,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as avg_cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cost_per_conversion,
  ROUND(SUM(elem.externalWebsiteConversions) * 100.0 / NULLIF(SUM(elem.clicks), 0), 2) as avg_conversion_rate
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  elem.pivotValue
"

run_query "${CREATIVE_PERF_VIEW}" "Creating creative_performance view"

# Create daily summary view
DAILY_SUMMARY_VIEW="
CREATE OR REPLACE VIEW linkedin_ads.daily_summary AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  campaign_config.name as campaign_name,
  campaign_config.dailyBudget.amount as daily_budget,
  SUM(elem.impressions) as impressions,
  SUM(elem.clicks) as clicks,
  SUM(elem.costInUsd) as cost,
  SUM(elem.externalWebsiteConversions) as conversions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cpa
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  campaign_config.name,
  campaign_config.dailyBudget.amount
ORDER BY report_date DESC
"

run_query "${DAILY_SUMMARY_VIEW}" "Creating daily_summary view"

# Create hourly breakdown view (useful for temporal analysis)
HOURLY_VIEW="
CREATE OR REPLACE VIEW linkedin_ads.hourly_breakdown AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  HOUR(from_iso8601_timestamp(pulled_at)) as hour_of_day,
  CAST(EXTRACT(DOW FROM from_iso8601_timestamp(pulled_at)) AS INTEGER) as day_of_week,
  campaign_id,
  elem.pivotValue as creative_id,
  SUM(elem.impressions) as impressions,
  SUM(elem.clicks) as clicks,
  SUM(elem.costInUsd) as cost,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as cpc
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  HOUR(from_iso8601_timestamp(pulled_at)),
  EXTRACT(DOW FROM from_iso8601_timestamp(pulled_at)),
  campaign_id,
  elem.pivotValue
"

run_query "${HOURLY_VIEW}" "Creating hourly_breakdown view"

echo ""
echo "Step 4: Testing Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test query - check if tables exist
TEST_QUERY="
SELECT
  table_name,
  table_type
FROM information_schema.tables
WHERE table_schema = 'linkedin_ads'
ORDER BY table_name
"

echo "📋 Verifying tables and views..."
QUERY_ID=$(aws athena start-query-execution \
  --query-string "${TEST_QUERY}" \
  --result-configuration "OutputLocation=s3://${ATHENA_OUTPUT}/" \
  --region "${REGION}" \
  --query 'QueryExecutionId' \
  --output text)

# Wait for results
sleep 3

RESULTS=$(aws athena get-query-results \
  --query-execution-id "${QUERY_ID}" \
  --region "${REGION}" \
  --query 'ResultSet.Rows[*].Data[0].VarCharValue' \
  --output text)

echo ""
echo "Created objects:"
echo "${RESULTS}" | while read -r line; do
  if [ -n "$line" ] && [ "$line" != "table_name" ]; then
    echo "  ✓ ${line}"
  fi
done

echo ""
echo "=========================================="
echo "✅ Athena Setup Complete!"
echo "=========================================="
echo ""
echo "Database: linkedin_ads"
echo ""
echo "Tables:"
echo "  • raw_analytics (external table → S3)"
echo ""
echo "Views:"
echo "  • creative_performance (performance by creative)"
echo "  • daily_summary (daily campaign totals)"
echo "  • hourly_breakdown (temporal patterns)"
echo ""
echo "Test with sample query:"
echo "  aws athena start-query-execution \\"
echo "    --query-string \"SELECT * FROM linkedin_ads.creative_performance LIMIT 10\" \\"
echo "    --result-configuration OutputLocation=s3://${ATHENA_OUTPUT}/ \\"
echo "    --region ${REGION}"
echo ""
echo "Or use AWS Console:"
echo "  https://${REGION}.console.aws.amazon.com/athena/home?region=${REGION}#/query-editor"
echo ""

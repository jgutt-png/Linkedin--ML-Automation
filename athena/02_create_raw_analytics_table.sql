-- Raw analytics data table
-- This table maps directly to the JSON files stored in S3

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
    unitCost: STRUCT<amount: DOUBLE, currencyCode: STRING>,
    targeting: STRUCT<
      includedTargetingFacets: STRUCT<
        locations: ARRAY<STRING>,
        staffCountRanges: ARRAY<STRING>,
        industries: ARRAY<STRING>
      >
    >
  >
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES (
  'ignore.malformed.json' = 'true',
  'case.insensitive' = 'true'
)
LOCATION 's3://your-company-linkedin-ads-automation/raw/analytics/'
TBLPROPERTIES (
  'has_encrypted_data'='false',
  'classification'='json'
);

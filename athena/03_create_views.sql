-- View: Performance by creative
-- Aggregated metrics for each creative across all time periods

CREATE OR REPLACE VIEW linkedin_ads.creative_performance AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  elem.pivotValue as creative_id,
  SUM(elem.impressions) as total_impressions,
  SUM(elem.clicks) as total_clicks,
  SUM(elem.costInUsd) as total_cost,
  SUM(elem.externalWebsiteConversions) as total_conversions,
  SUM(elem.approximateUniqueImpressions) as unique_impressions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr_percent,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as avg_cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cost_per_conversion,
  ROUND(SUM(elem.externalWebsiteConversions) * 100.0 / NULLIF(SUM(elem.clicks), 0), 2) as conversion_rate_percent
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
WHERE elem.impressions IS NOT NULL
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  elem.pivotValue;


-- View: Daily campaign summary
-- Daily aggregated performance by campaign

CREATE OR REPLACE VIEW linkedin_ads.daily_summary AS
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  campaign_id,
  campaign_config.name as campaign_name,
  campaign_config.status as campaign_status,
  campaign_config.dailyBudget.amount as daily_budget,
  campaign_config.unitCost.amount as unit_cost,
  SUM(elem.impressions) as impressions,
  SUM(elem.clicks) as clicks,
  SUM(elem.costInUsd) as cost,
  SUM(elem.externalWebsiteConversions) as conversions,
  SUM(elem.approximateUniqueImpressions) as unique_impressions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as ctr,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as cpa,
  ROUND(SUM(elem.externalWebsiteConversions) * 100.0 / NULLIF(SUM(elem.clicks), 0), 2) as conversion_rate
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
WHERE elem.impressions IS NOT NULL
GROUP BY
  DATE(from_iso8601_timestamp(pulled_at)),
  campaign_id,
  campaign_config.name,
  campaign_config.status,
  campaign_config.dailyBudget.amount,
  campaign_config.unitCost.amount
ORDER BY report_date DESC;


-- View: Campaign totals
-- All-time performance by campaign

CREATE OR REPLACE VIEW linkedin_ads.campaign_totals AS
SELECT
  campaign_id,
  campaign_config.name as campaign_name,
  MIN(DATE(from_iso8601_timestamp(pulled_at))) as first_seen,
  MAX(DATE(from_iso8601_timestamp(pulled_at))) as last_seen,
  COUNT(DISTINCT DATE(from_iso8601_timestamp(pulled_at))) as days_active,
  SUM(elem.impressions) as total_impressions,
  SUM(elem.clicks) as total_clicks,
  SUM(elem.costInUsd) as total_cost,
  SUM(elem.externalWebsiteConversions) as total_conversions,
  ROUND(SUM(elem.clicks) * 100.0 / NULLIF(SUM(elem.impressions), 0), 2) as overall_ctr,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.clicks), 0), 2) as overall_cpc,
  ROUND(SUM(elem.costInUsd) / NULLIF(SUM(elem.externalWebsiteConversions), 0), 2) as overall_cpa,
  ROUND(SUM(elem.externalWebsiteConversions) * 100.0 / NULLIF(SUM(elem.clicks), 0), 2) as overall_conversion_rate
FROM linkedin_ads.raw_analytics
CROSS JOIN UNNEST(analytics.elements) as t(elem)
WHERE elem.impressions IS NOT NULL
GROUP BY
  campaign_id,
  campaign_config.name;

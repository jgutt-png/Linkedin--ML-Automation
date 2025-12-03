-- Sample Queries for LinkedIn Ads Analytics
-- Copy and paste these into Athena console or use via boto3

-- ============================================================================
-- PERFORMANCE ANALYSIS
-- ============================================================================

-- Top performing creatives (last 7 days)
SELECT
  creative_id,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  AVG(ctr_percent) as avg_ctr,
  AVG(avg_cpc) as avg_cpc,
  SUM(total_conversions) as conversions,
  AVG(cost_per_conversion) as avg_cpa
FROM linkedin_ads.creative_performance
WHERE report_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY creative_id
HAVING SUM(total_clicks) > 10  -- Minimum sample size
ORDER BY avg_ctr DESC
LIMIT 10;


-- Underperforming creatives (last 3 days)
-- These should be paused
SELECT
  creative_id,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  AVG(ctr_percent) as avg_ctr,
  AVG(avg_cpc) as avg_cpc,
  SUM(total_cost) as total_spent
FROM linkedin_ads.creative_performance
WHERE report_date >= CURRENT_DATE - INTERVAL '3' DAY
GROUP BY creative_id
HAVING
  SUM(total_clicks) > 100 AND  -- Minimum sample size
  AVG(ctr_percent) < 1.0       -- CTR below 1%
ORDER BY total_spent DESC;


-- Daily performance trend
SELECT
  report_date,
  SUM(impressions) as total_impressions,
  SUM(clicks) as total_clicks,
  SUM(cost) as total_cost,
  SUM(conversions) as total_conversions,
  AVG(ctr) as avg_ctr,
  AVG(cpc) as avg_cpc,
  AVG(cpa) as avg_cpa
FROM linkedin_ads.daily_summary
WHERE report_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY report_date
ORDER BY report_date DESC;


-- ============================================================================
-- BUDGET & PACING
-- ============================================================================

-- Budget pacing check (today)
SELECT
  campaign_id,
  campaign_name,
  daily_budget,
  SUM(cost) as actual_spend,
  ROUND((SUM(cost) / NULLIF(daily_budget, 0)) * 100, 1) as pacing_percent,
  CASE
    WHEN SUM(cost) < daily_budget * 0.8 THEN 'Under-pacing'
    WHEN SUM(cost) > daily_budget * 1.1 THEN 'Over-pacing'
    ELSE 'On track'
  END as status
FROM linkedin_ads.daily_summary
WHERE report_date = CURRENT_DATE
GROUP BY campaign_id, campaign_name, daily_budget;


-- Weekly spend by campaign
SELECT
  campaign_id,
  campaign_name,
  DATE_TRUNC('week', report_date) as week,
  SUM(cost) as weekly_spend,
  SUM(conversions) as weekly_conversions,
  ROUND(SUM(cost) / NULLIF(SUM(conversions), 0), 2) as weekly_cpa
FROM linkedin_ads.daily_summary
WHERE report_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY campaign_id, campaign_name, DATE_TRUNC('week', report_date)
ORDER BY week DESC, weekly_spend DESC;


-- ============================================================================
-- OPTIMIZATION INSIGHTS
-- ============================================================================

-- Creatives ready to scale (high performance)
SELECT
  creative_id,
  campaign_id,
  SUM(total_impressions) as impressions,
  SUM(total_clicks) as clicks,
  AVG(ctr_percent) as avg_ctr,
  AVG(avg_cpc) as avg_cpc,
  SUM(total_conversions) as conversions,
  AVG(conversion_rate_percent) as conversion_rate
FROM linkedin_ads.creative_performance
WHERE
  report_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY creative_id, campaign_id
HAVING
  SUM(total_clicks) > 100 AND      -- Sufficient data
  AVG(ctr_percent) > 3.0 AND       -- High CTR
  AVG(avg_cpc) < 8.0 AND           -- Reasonable CPC
  SUM(total_conversions) > 2       -- At least some conversions
ORDER BY avg_ctr DESC;


-- Expensive creatives with low conversion
SELECT
  creative_id,
  campaign_id,
  SUM(total_cost) as total_spent,
  SUM(total_clicks) as clicks,
  SUM(total_conversions) as conversions,
  AVG(avg_cpc) as avg_cpc,
  AVG(conversion_rate_percent) as conversion_rate
FROM linkedin_ads.creative_performance
WHERE
  report_date >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY creative_id, campaign_id
HAVING
  SUM(total_cost) > 100 AND           -- Spent significant amount
  (SUM(total_conversions) = 0 OR      -- No conversions
   AVG(conversion_rate_percent) < 2)  -- Or very low conversion rate
ORDER BY total_spent DESC;


-- ============================================================================
-- CAMPAIGN HEALTH
-- ============================================================================

-- Campaign overview with health metrics
SELECT
  campaign_name,
  days_active,
  total_impressions,
  total_clicks,
  total_cost,
  total_conversions,
  overall_ctr,
  overall_cpc,
  overall_cpa,
  CASE
    WHEN overall_ctr > 2.5 THEN 'Excellent'
    WHEN overall_ctr > 1.5 THEN 'Good'
    WHEN overall_ctr > 0.8 THEN 'Fair'
    ELSE 'Needs improvement'
  END as ctr_rating,
  CASE
    WHEN overall_cpc < 5 THEN 'Excellent'
    WHEN overall_cpc < 8 THEN 'Good'
    WHEN overall_cpc < 12 THEN 'Fair'
    ELSE 'Too expensive'
  END as cpc_rating
FROM linkedin_ads.campaign_totals
ORDER BY total_cost DESC;


-- Day of week performance analysis
SELECT
  EXTRACT(DOW FROM report_date) as day_of_week,
  CASE EXTRACT(DOW FROM report_date)
    WHEN 0 THEN 'Sunday'
    WHEN 1 THEN 'Monday'
    WHEN 2 THEN 'Tuesday'
    WHEN 3 THEN 'Wednesday'
    WHEN 4 THEN 'Thursday'
    WHEN 5 THEN 'Friday'
    WHEN 6 THEN 'Saturday'
  END as day_name,
  COUNT(*) as data_points,
  AVG(ctr) as avg_ctr,
  AVG(cpc) as avg_cpc,
  AVG(conversion_rate) as avg_conversion_rate
FROM linkedin_ads.daily_summary
WHERE report_date >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY EXTRACT(DOW FROM report_date)
ORDER BY EXTRACT(DOW FROM report_date);


-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- Check for missing data
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  COUNT(*) as pull_count,
  COUNT(DISTINCT campaign_id) as unique_campaigns,
  SUM(CASE WHEN analytics.elements IS NULL OR CARDINALITY(analytics.elements) = 0 THEN 1 ELSE 0 END) as empty_pulls
FROM linkedin_ads.raw_analytics
WHERE DATE(from_iso8601_timestamp(pulled_at)) >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY DATE(from_iso8601_timestamp(pulled_at))
ORDER BY report_date DESC;


-- Verify data collection frequency
SELECT
  DATE(from_iso8601_timestamp(pulled_at)) as report_date,
  COUNT(*) as pulls_per_day,
  MIN(pulled_at) as first_pull,
  MAX(pulled_at) as last_pull
FROM linkedin_ads.raw_analytics
WHERE DATE(from_iso8601_timestamp(pulled_at)) >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY DATE(from_iso8601_timestamp(pulled_at))
ORDER BY report_date DESC;

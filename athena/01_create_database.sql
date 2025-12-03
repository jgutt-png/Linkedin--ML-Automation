-- Create database for LinkedIn ads analytics
CREATE DATABASE IF NOT EXISTS linkedin_ads
COMMENT 'LinkedIn advertising performance data'
LOCATION 's3://your-company-linkedin-ads-automation/athena/';

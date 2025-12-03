# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name         = "${var.project_name}-alerts"
  display_name = "LinkedIn Ads Automation Alerts"
}

# SNS Email subscription (optional - requires email confirmation)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Alarm: Lambda collector failures
resource "aws_cloudwatch_metric_alarm" "collector_errors" {
  alarm_name          = "${var.project_name}-collector-errors"
  alarm_description   = "Alert when data collector Lambda fails"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 3600
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.collector.function_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# CloudWatch Alarm: Collection failures
resource "aws_cloudwatch_metric_alarm" "collection_failures" {
  alarm_name          = "${var.project_name}-collection-failures"
  alarm_description   = "Alert when data collection from LinkedIn fails"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CollectionFailure"
  namespace           = "LinkedInAds/Collector"
  period              = 21600  # 6 hours
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# CloudWatch Alarm: High daily ad spend
resource "aws_cloudwatch_metric_alarm" "high_daily_spend" {
  alarm_name          = "${var.project_name}-high-daily-spend"
  alarm_description   = "Alert when daily ad spend exceeds threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TotalCost"
  namespace           = "LinkedInAds/Collector"
  period              = 86400  # 24 hours
  statistic           = "Sum"
  threshold           = 100  # $100/day
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# CloudWatch Alarm: Low CTR
resource "aws_cloudwatch_metric_alarm" "low_ctr" {
  alarm_name          = "${var.project_name}-low-ctr"
  alarm_description   = "Alert when average CTR drops below 1%"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CTR"
  namespace           = "LinkedInAds/Collector"
  period              = 21600  # 6 hours
  statistic           = "Average"
  threshold           = 1.0
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# CloudWatch Alarm: High CPC
resource "aws_cloudwatch_metric_alarm" "high_cpc" {
  alarm_name          = "${var.project_name}-high-cpc"
  alarm_description   = "Alert when average CPC exceeds $8"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPC"
  namespace           = "LinkedInAds/Collector"
  period              = 21600  # 6 hours
  statistic           = "Average"
  threshold           = 8.0
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["LinkedInAds/Collector", "TotalImpressions", { stat = "Sum" }],
            [".", "TotalClicks", { stat = "Sum" }],
          ]
          period = 21600
          stat   = "Sum"
          region = var.aws_region
          title  = "Impressions & Clicks"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["LinkedInAds/Collector", "TotalCost", { stat = "Sum" }]
          ]
          period = 21600
          stat   = "Sum"
          region = var.aws_region
          title  = "Ad Spend ($)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["LinkedInAds/Collector", "CTR", { stat = "Average" }]
          ]
          period = 21600
          stat   = "Average"
          region = var.aws_region
          title  = "CTR (%)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["LinkedInAds/Collector", "CPC", { stat = "Average" }]
          ]
          period = 21600
          stat   = "Average"
          region = var.aws_region
          title  = "CPC ($)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum", FunctionName = aws_lambda_function.collector.function_name }],
            [".", "Errors", { stat = "Sum", FunctionName = aws_lambda_function.collector.function_name }],
          ]
          period = 21600
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Executions"
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '/aws/lambda/${aws_lambda_function.collector.function_name}' | fields @timestamp, @message | filter @message like /✓|❌/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Collection Events"
          stacked = false
        }
      }
    ]
  })
}

# Outputs
output "sns_topic_arn" {
  description = "ARN of SNS topic for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

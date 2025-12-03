# EventBridge Rule - Schedule data collection
resource "aws_cloudwatch_event_rule" "collector_schedule" {
  name                = "${var.project_name}-collector-schedule"
  description         = "Trigger LinkedIn data collection every 6 hours"
  schedule_expression = var.collection_schedule
}

# EventBridge Target - Lambda Collector
resource "aws_cloudwatch_event_target" "collector" {
  rule      = aws_cloudwatch_event_rule.collector_schedule.name
  target_id = "linkedin-ads-collector"
  arn       = aws_lambda_function.collector.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "eventbridge_collector" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.collector_schedule.arn
}

# EventBridge Rule - Schedule optimizer (daily)
resource "aws_cloudwatch_event_rule" "optimizer_schedule" {
  name                = "${var.project_name}-optimizer-schedule"
  description         = "Trigger LinkedIn ad optimization daily"
  schedule_expression = var.optimizer_schedule
}

# EventBridge Target - Lambda Optimizer (will be created later)
# Commented out until optimizer Lambda is ready
# resource "aws_cloudwatch_event_target" "optimizer" {
#   rule      = aws_cloudwatch_event_rule.optimizer_schedule.name
#   target_id = "linkedin-ads-optimizer"
#   arn       = aws_lambda_function.optimizer.arn
# }

# Output EventBridge details
output "collector_schedule_arn" {
  description = "ARN of the collector EventBridge rule"
  value       = aws_cloudwatch_event_rule.collector_schedule.arn
}

output "optimizer_schedule_arn" {
  description = "ARN of the optimizer EventBridge rule"
  value       = aws_cloudwatch_event_rule.optimizer_schedule.arn
}

# IAM Role for Lambda Collector
resource "aws_iam_role" "lambda_collector" {
  name = "${var.project_name}-collector-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda Collector
resource "aws_iam_role_policy" "lambda_collector" {
  name = "${var.project_name}-collector-policy"
  role = aws_iam_role.lambda_collector.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.linkedin_ads.arn,
          "${aws_s3_bucket.linkedin_ads.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.linkedin_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group for Collector
resource "aws_cloudwatch_log_group" "lambda_collector" {
  name              = "/aws/lambda/${var.project_name}-collector"
  retention_in_days = 14
}

# Lambda Function - Data Collector
resource "aws_lambda_function" "collector" {
  filename         = "${path.module}/../collector.zip"
  function_name    = "${var.project_name}-collector"
  role            = aws_iam_role.lambda_collector.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  source_code_hash = fileexists("${path.module}/../collector.zip") ? filebase64sha256("${path.module}/../collector.zip") : null

  environment {
    variables = {
      BUCKET_NAME  = aws_s3_bucket.linkedin_ads.id
      CAMPAIGN_IDS = var.campaign_ids
      SECRET_NAME  = aws_secretsmanager_secret.linkedin_credentials.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_collector
  ]
}

# Lambda Function URL (for manual triggers)
resource "aws_lambda_function_url" "collector" {
  function_name      = aws_lambda_function.collector.function_name
  authorization_type = "AWS_IAM"
}

# Output Lambda details
output "collector_lambda_arn" {
  description = "ARN of the collector Lambda function"
  value       = aws_lambda_function.collector.arn
}

output "collector_lambda_name" {
  description = "Name of the collector Lambda function"
  value       = aws_lambda_function.collector.function_name
}

output "collector_function_url" {
  description = "Function URL for manual collector invocation"
  value       = aws_lambda_function_url.collector.function_url
}

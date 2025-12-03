variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "linkedin-ads-automation"
}

variable "campaign_ids" {
  description = "Comma-separated list of LinkedIn campaign IDs to track"
  type        = string
  default     = ""  # Will be set after campaigns are created
}

variable "collection_schedule" {
  description = "EventBridge schedule expression for data collection"
  type        = string
  default     = "rate(6 hours)"
}

variable "optimizer_schedule" {
  description = "EventBridge schedule expression for optimization (cron format)"
  type        = string
  default     = "cron(0 9 * * ? *)"  # 9 AM UTC daily
}

variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
  default     = ""
}

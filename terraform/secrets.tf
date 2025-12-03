# Secrets Manager for LinkedIn OAuth credentials
resource "aws_secretsmanager_secret" "linkedin_credentials" {
  name        = "${var.project_name}-credentials"
  description = "LinkedIn Ads API OAuth credentials and access tokens"

  recovery_window_in_days = 7

  tags = {
    Purpose = "LinkedIn API Authentication"
  }
}

# Placeholder secret value (will be updated manually after OAuth flow)
resource "aws_secretsmanager_secret_version" "linkedin_credentials_placeholder" {
  secret_id = aws_secretsmanager_secret.linkedin_credentials.id
  secret_string = jsonencode({
    client_id     = "PLACEHOLDER_UPDATE_AFTER_APPROVAL"
    client_secret = "PLACEHOLDER_UPDATE_AFTER_APPROVAL"
    access_token  = "PLACEHOLDER_UPDATE_AFTER_OAUTH"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Output secret ARN
output "linkedin_credentials_arn" {
  description = "ARN of LinkedIn credentials secret"
  value       = aws_secretsmanager_secret.linkedin_credentials.arn
  sensitive   = true
}

output "linkedin_credentials_name" {
  description = "Name of LinkedIn credentials secret"
  value       = aws_secretsmanager_secret.linkedin_credentials.name
}

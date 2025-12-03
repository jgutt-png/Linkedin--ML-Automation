# S3 Bucket for LinkedIn ads data
resource "aws_s3_bucket" "linkedin_ads" {
  bucket = "your-company-${var.project_name}"
}

# Enable versioning
resource "aws_s3_bucket_versioning" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policies
resource "aws_s3_bucket_lifecycle_configuration" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  # Delete raw data after 90 days
  rule {
    id     = "delete-old-raw-data"
    status = "Enabled"

    filter {
      prefix = "raw/"
    }

    expiration {
      days = 90
    }
  }

  # Archive processed data
  rule {
    id     = "archive-processed-data"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "linkedin_ads" {
  bucket = aws_s3_bucket.linkedin_ads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Output bucket name
output "s3_bucket_name" {
  description = "Name of the S3 bucket for LinkedIn ads data"
  value       = aws_s3_bucket.linkedin_ads.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.linkedin_ads.arn
}

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "your-company-terraform-state"
    key    = "linkedin-automation/terraform.tfstate"
    region = "us-east-2"  # Change to your preferred region
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "LinkedIn Ads Automation"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Company     = var.company_name  # Set in terraform.tfvars
    }
  }
}

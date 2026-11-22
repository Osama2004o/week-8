terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Offline dry-run mode lets `terraform plan` succeed without AWS credentials.
  # Set `offline_plan_mode = false` when deploying to a real AWS account.
  access_key                  = var.offline_plan_mode ? "mock_access_key" : null
  secret_key                  = var.offline_plan_mode ? "mock_secret_key" : null
  skip_credentials_validation = var.offline_plan_mode
  skip_metadata_api_check     = var.offline_plan_mode
  skip_requesting_account_id  = var.offline_plan_mode

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Application = "agentic-hybrid-rag"
    }
  }
}

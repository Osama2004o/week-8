variable "name_prefix" {
  description = "Resource name prefix (<project>-<env>)."
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 documents bucket for scoping ECS task IAM permissions."
  type        = string
}

variable "secret_recovery_window_days" {
  description = "Recovery window in days for Secrets Manager secrets."
  type        = number
}

variable "openrouter_api_key" {
  description = "OpenRouter API key value (optional during offline planning)."
  type        = string
  sensitive   = true
}

variable "redis_auth_token" {
  description = "Redis AUTH token value (optional during offline planning)."
  type        = string
  sensitive   = true
}

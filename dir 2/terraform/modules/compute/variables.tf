variable "name_prefix" {
  description = "Resource name prefix (<project>-<env>)."
  type        = string
}

variable "aws_region" {
  description = "AWS region for CloudWatch log configuration."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the ALB target group resides."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the Application Load Balancer."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS Fargate tasks."
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID attached to the ALB."
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security group ID attached to ECS tasks."
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "IAM role ARN for ECS task execution (ECR pulls, logs, secrets)."
  type        = string
}

variable "ecs_task_role_arn" {
  description = "IAM role ARN assumed by the application container at runtime."
  type        = string
}

variable "openrouter_secret_arn" {
  description = "Secrets Manager ARN containing OPENROUTER_API_KEY."
  type        = string
}

variable "redis_secret_arn" {
  description = "Secrets Manager ARN containing REDIS_PASSWORD."
  type        = string
}

variable "efs_file_system_id" {
  description = "EFS file system ID for persistent vector and upload volumes."
  type        = string
}

variable "efs_chroma_access_point_id" {
  description = "EFS access point ID for ChromaDB."
  type        = string
}

variable "efs_uploads_access_point_id" {
  description = "EFS access point ID for OCR image uploads."
  type        = string
}

variable "s3_documents_bucket_name" {
  description = "S3 bucket name for raw document storage."
  type        = string
}

variable "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint hostname."
  type        = string
}

variable "redis_port" {
  description = "Redis TCP port."
  type        = number
}

variable "redis_db" {
  description = "Redis logical database index."
  type        = number
}

variable "container_port" {
  description = "Container TCP port exposed behind the ALB."
  type        = number
}

variable "container_image_tag" {
  description = "Container image tag to run from ECR."
  type        = string
}

variable "ecs_task_cpu" {
  description = "ECS Fargate CPU units."
  type        = number
}

variable "ecs_task_memory" {
  description = "ECS Fargate memory in MiB."
  type        = number
}

variable "desired_count" {
  description = "Number of ECS Fargate tasks."
  type        = number
}

variable "health_check_path" {
  description = "ALB target group health check HTTP path."
  type        = string
}

variable "llm_model" {
  description = "OpenRouter model identifier."
  type        = string
}

variable "embedding_device" {
  description = "Embedding device ('cpu' or 'cuda')."
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
}

output "vpc_id" {
  description = "ID of the dedicated VPC."
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets."
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets."
  value       = module.networking.private_subnet_ids
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing the Hybrid RAG Docker image."
  value       = module.compute.ecr_repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS Fargate cluster."
  value       = module.compute.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service running the Hybrid RAG application."
  value       = module.compute.ecs_service_name
}

output "alb_dns_name" {
  description = "Public DNS name of the Application Load Balancer."
  value       = module.compute.alb_dns_name
}

output "cloudwatch_log_group_name" {
  description = "CloudWatch Log Group receiving ECS container logs."
  value       = module.compute.cloudwatch_log_group_name
}

output "efs_file_system_id" {
  description = "EFS file system ID used for persistent ChromaDB storage and OCR image uploads."
  value       = module.storage.efs_file_system_id
}

output "s3_documents_bucket_name" {
  description = "S3 bucket name for archiving raw documents and knowledge-base assets."
  value       = module.storage.s3_bucket_name
}

output "redis_primary_endpoint" {
  description = "Primary ElastiCache Redis endpoint address (wired to REDIS_HOST)."
  value       = module.cache.redis_primary_endpoint
}

output "redis_port" {
  description = "ElastiCache Redis TCP port (wired to REDIS_PORT)."
  value       = module.cache.redis_port
}

output "secrets_manager_arns" {
  description = "ARNs of AWS Secrets Manager secrets for OpenRouter API key and Redis password."
  value = {
    openrouter_api_key = module.security.openrouter_secret_arn
    redis_password     = module.security.redis_secret_arn
  }
}

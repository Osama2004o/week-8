output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS Task Execution IAM role."
  value       = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS Task runtime IAM role."
  value       = aws_iam_role.ecs_task.arn
}

output "openrouter_secret_arn" {
  description = "ARN of the Secrets Manager secret for OPENROUTER_API_KEY."
  value       = aws_secretsmanager_secret.openrouter_api_key.arn
}

output "redis_secret_arn" {
  description = "ARN of the Secrets Manager secret for REDIS_PASSWORD."
  value       = aws_secretsmanager_secret.redis_password.arn
}

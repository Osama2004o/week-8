# -----------------------------------------------------------------------------
# AWS Secrets Manager Secrets
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "openrouter_api_key" {
  name                    = "${var.name_prefix}/openrouter-api-key"
  description             = "OpenRouter API key used by Retriever, Analyst, and Answer agents"
  recovery_window_in_days = var.secret_recovery_window_days

  tags = {
    Name = "${var.name_prefix}-openrouter-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "openrouter_api_key" {
  count = var.openrouter_api_key != "" ? 1 : 0

  secret_id     = aws_secretsmanager_secret.openrouter_api_key.id
  secret_string = var.openrouter_api_key
}

resource "aws_secretsmanager_secret" "redis_password" {
  name                    = "${var.name_prefix}/redis-password"
  description             = "Redis AUTH token for ElastiCache retrieval/response/semantic cache"
  recovery_window_in_days = var.secret_recovery_window_days

  tags = {
    Name = "${var.name_prefix}-redis-password"
  }
}

resource "aws_secretsmanager_secret_version" "redis_password" {
  count = var.redis_auth_token != "" ? 1 : 0

  secret_id     = aws_secretsmanager_secret.redis_password.id
  secret_string = var.redis_auth_token
}

# -----------------------------------------------------------------------------
# IAM Roles for ECS Fargate
# -----------------------------------------------------------------------------

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.name_prefix}-ecs-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.name_prefix}-ecs-exec-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_default" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.name_prefix}-secrets-read"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.openrouter_api_key.arn,
          aws_secretsmanager_secret.redis_password.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.name_prefix}-ecs-task-role"
  }
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.name_prefix}-s3-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

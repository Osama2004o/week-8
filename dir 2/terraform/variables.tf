# -----------------------------------------------------------------------------
# General & Provider Variables
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "Short lowercase project identifier used to prefix AWS resource names."
  type        = string
  default     = "hybrid-rag"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,16}[a-z0-9]$", var.project_name))
    error_message = "project_name must be 3-18 lowercase alphanumeric characters or hyphens, starting with a letter."
  }
}

variable "environment" {
  description = "Deployment environment name (dev, staging, or prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for deploying the Hybrid RAG infrastructure."
  type        = string
  default     = "us-east-1"
}

variable "offline_plan_mode" {
  description = "Enable offline dry-run planning without real AWS credentials (for IaC preparation and validation)."
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Networking Variables
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the dedicated application VPC."
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Two AWS availability zones for high-availability subnet placement."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly 2 availability zones must be provided."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets hosting the ALB and NAT Gateway."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly 2 public subnet CIDRs must be provided."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets hosting ECS tasks, EFS mount targets, and ElastiCache Redis."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly 2 private subnet CIDRs must be provided."
  }
}

variable "enable_nat_gateway" {
  description = "Provision a NAT Gateway so private ECS tasks can reach OpenRouter API, HuggingFace, and web loaders."
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Compute & Application Variables
# -----------------------------------------------------------------------------

variable "container_port" {
  description = "TCP port exposed by the containerized RAG application."
  type        = number
  default     = 8000

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535
    error_message = "container_port must be between 1 and 65535."
  }
}

variable "container_image_tag" {
  description = "Docker image tag in ECR to deploy on ECS Fargate."
  type        = string
  default     = "latest"
}

variable "ecs_task_cpu" {
  description = "CPU units for the ECS Fargate task (2048 = 2 vCPU recommended for SentenceTransformers, RapidOCR, and Faster-Whisper)."
  type        = number
  default     = 2048
}

variable "ecs_task_memory" {
  description = "Memory in MiB for the ECS Fargate task (4096 MiB minimum recommended for ML models and ChromaDB)."
  type        = number
  default     = 4096
}

variable "desired_count" {
  description = "Number of ECS Fargate tasks to run."
  type        = number
  default     = 1

  validation {
    condition     = var.desired_count >= 1
    error_message = "desired_count must be at least 1."
  }
}

variable "health_check_path" {
  description = "HTTP path polled by the ALB target group health check."
  type        = string
  default     = "/health"
}

variable "llm_model" {
  description = "Default LLM model identifier passed to the application (matches config/settings.py LLM_MODEL)."
  type        = string
  default     = "openrouter/free"
}

variable "embedding_device" {
  description = "Compute device for SentenceTransformer embeddings (cpu for Fargate, cuda for GPU instances)."
  type        = string
  default     = "cpu"

  validation {
    condition     = contains(["cpu", "cuda"], var.embedding_device)
    error_message = "embedding_device must be 'cpu' or 'cuda'."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain ECS container logs in CloudWatch Logs."
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# Storage Variables (S3 & EFS)
# -----------------------------------------------------------------------------

variable "efs_performance_mode" {
  description = "EFS performance mode for ChromaDB persistence and uploaded images."
  type        = string
  default     = "generalPurpose"

  validation {
    condition     = contains(["generalPurpose", "maxIO"], var.efs_performance_mode)
    error_message = "efs_performance_mode must be 'generalPurpose' or 'maxIO'."
  }
}

variable "enable_s3_versioning" {
  description = "Enable S3 object versioning on the source document archive bucket."
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Cache Variables (ElastiCache Redis)
# -----------------------------------------------------------------------------

variable "redis_node_type" {
  description = "ElastiCache Redis node type for retrieval cache, response cache, session memory, and semantic cache."
  type        = string
  default     = "cache.t3.small"
}

variable "redis_engine_version" {
  description = "Redis engine version for ElastiCache."
  type        = string
  default     = "7.1"
}

variable "redis_parameter_group_name" {
  description = "ElastiCache Redis parameter group name."
  type        = string
  default     = "default.redis7"
}

variable "redis_port" {
  description = "TCP port for Redis connections (matches config/settings.py REDIS_PORT)."
  type        = number
  default     = 6379
}

variable "redis_db" {
  description = "Logical Redis database index (matches config/settings.py REDIS_DB)."
  type        = number
  default     = 0
}

variable "redis_num_cache_clusters" {
  description = "Number of cache nodes in the Redis replication group."
  type        = number
  default     = 1
}

# -----------------------------------------------------------------------------
# Secrets Variables (Supply via TF_VAR_* in real deployments)
# -----------------------------------------------------------------------------

variable "secret_recovery_window_days" {
  description = "Recovery window in days before Secrets Manager permanently deletes a secret (0 for immediate deletion)."
  type        = number
  default     = 7
}

variable "openrouter_api_key" {
  description = "OpenRouter API key stored in AWS Secrets Manager. Leave empty during offline planning."
  type        = string
  default     = ""
  sensitive   = true
}

variable "redis_auth_token" {
  description = "Optional Redis AUTH token stored in Secrets Manager (must be 16-128 characters if set)."
  type        = string
  default     = ""
  sensitive   = true
}

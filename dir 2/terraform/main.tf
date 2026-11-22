locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

# 1. Network foundation: VPC, public/private subnets, NAT Gateway, and security groups
module "networking" {
  source = "./modules/networking"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  enable_nat_gateway   = var.enable_nat_gateway
  container_port       = var.container_port
  redis_port           = var.redis_port
}

# 2. Persistent storage: S3 document archive + EFS for ChromaDB and image uploads
module "storage" {
  source = "./modules/storage"

  name_prefix           = local.name_prefix
  private_subnet_ids    = module.networking.private_subnet_ids
  efs_security_group_id = module.networking.efs_security_group_id
  efs_performance_mode  = var.efs_performance_mode
  enable_s3_versioning  = var.enable_s3_versioning
}

# 3. Identity & secrets: IAM roles for ECS and Secrets Manager entries for API keys
module "security" {
  source = "./modules/security"

  name_prefix                 = local.name_prefix
  s3_bucket_arn               = module.storage.s3_bucket_arn
  secret_recovery_window_days = var.secret_recovery_window_days
  openrouter_api_key          = var.openrouter_api_key
  redis_auth_token            = var.redis_auth_token
}

# 4. In-memory cache & session store: ElastiCache Redis in private subnets
module "cache" {
  source = "./modules/cache"

  name_prefix                = local.name_prefix
  private_subnet_ids         = module.networking.private_subnet_ids
  redis_security_group_id    = module.networking.redis_security_group_id
  redis_node_type            = var.redis_node_type
  redis_engine_version       = var.redis_engine_version
  redis_parameter_group_name = var.redis_parameter_group_name
  redis_port                 = var.redis_port
  redis_num_cache_clusters   = var.redis_num_cache_clusters
  redis_auth_token           = var.redis_auth_token
}

# 5. Container compute: ECR repository, CloudWatch logs, ALB, and ECS Fargate service
module "compute" {
  source = "./modules/compute"

  name_prefix                     = local.name_prefix
  aws_region                      = var.aws_region
  vpc_id                          = module.networking.vpc_id
  public_subnet_ids               = module.networking.public_subnet_ids
  private_subnet_ids              = module.networking.private_subnet_ids
  alb_security_group_id           = module.networking.alb_security_group_id
  ecs_security_group_id           = module.networking.ecs_security_group_id
  ecs_task_execution_role_arn     = module.security.ecs_task_execution_role_arn
  ecs_task_role_arn               = module.security.ecs_task_role_arn
  openrouter_secret_arn           = module.security.openrouter_secret_arn
  redis_secret_arn                = module.security.redis_secret_arn
  efs_file_system_id              = module.storage.efs_file_system_id
  efs_chroma_access_point_id      = module.storage.efs_chroma_access_point_id
  efs_uploads_access_point_id     = module.storage.efs_uploads_access_point_id
  s3_documents_bucket_name        = module.storage.s3_bucket_name
  redis_primary_endpoint          = module.cache.redis_primary_endpoint
  redis_port                      = var.redis_port
  redis_db                        = var.redis_db
  container_port                  = var.container_port
  container_image_tag             = var.container_image_tag
  ecs_task_cpu                    = var.ecs_task_cpu
  ecs_task_memory                 = var.ecs_task_memory
  desired_count                   = var.desired_count
  health_check_path               = var.health_check_path
  llm_model                       = var.llm_model
  embedding_device                = var.embedding_device
  log_retention_days              = var.log_retention_days
}

variable "name_prefix" {
  description = "Resource name prefix (<project>-<env>)."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the ElastiCache subnet group."
  type        = list(string)
}

variable "redis_security_group_id" {
  description = "Security group ID allowing Redis access from ECS tasks."
  type        = string
}

variable "redis_node_type" {
  description = "ElastiCache Redis node instance type."
  type        = string
}

variable "redis_engine_version" {
  description = "Redis engine version."
  type        = string
}

variable "redis_parameter_group_name" {
  description = "ElastiCache Redis parameter group."
  type        = string
}

variable "redis_port" {
  description = "TCP port for Redis."
  type        = number
}

variable "redis_num_cache_clusters" {
  description = "Number of cache nodes in the replication group."
  type        = number
}

variable "redis_auth_token" {
  description = "Optional AUTH token for Redis transit encryption."
  type        = string
  sensitive   = true
}

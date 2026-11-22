resource "aws_elasticache_subnet_group" "redis" {
  name        = "${var.name_prefix}-redis-subnets"
  description = "Private subnets for the Hybrid RAG ElastiCache Redis cluster"
  subnet_ids  = var.private_subnet_ids

  tags = {
    Name = "${var.name_prefix}-redis-subnets"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.name_prefix}-redis"
  description                = "Redis cache and session memory store for Agentic Hybrid RAG"
  engine                     = "redis"
  engine_version             = var.redis_engine_version
  node_type                  = var.redis_node_type
  num_cache_clusters         = var.redis_num_cache_clusters
  automatic_failover_enabled = var.redis_num_cache_clusters > 1
  port                       = var.redis_port
  parameter_group_name       = var.redis_parameter_group_name
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [var.redis_security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token != "" ? var.redis_auth_token : null

  tags = {
    Name = "${var.name_prefix}-redis"
  }
}

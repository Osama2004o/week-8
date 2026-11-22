output "redis_primary_endpoint" {
  description = "Primary endpoint address of the ElastiCache Redis replication group."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Port on which ElastiCache Redis accepts connections."
  value       = aws_elasticache_replication_group.redis.port
}

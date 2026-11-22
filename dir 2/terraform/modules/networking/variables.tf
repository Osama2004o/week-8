variable "name_prefix" {
  description = "Resource name prefix (<project>-<env>)."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
}

variable "availability_zones" {
  description = "List of two availability zones."
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks."
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks."
  type        = list(string)
}

variable "enable_nat_gateway" {
  description = "Whether to provision a NAT Gateway for private subnets."
  type        = bool
}

variable "container_port" {
  description = "Container port exposed behind the ALB."
  type        = number
}

variable "redis_port" {
  description = "Redis TCP port."
  type        = number
}

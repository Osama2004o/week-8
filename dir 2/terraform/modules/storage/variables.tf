variable "name_prefix" {
  description = "Resource name prefix (<project>-<env>)."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EFS mount targets."
  type        = list(string)
}

variable "efs_security_group_id" {
  description = "Security group ID attached to EFS mount targets."
  type        = string
}

variable "efs_performance_mode" {
  description = "EFS performance mode."
  type        = string
}

variable "enable_s3_versioning" {
  description = "Enable S3 object versioning."
  type        = bool
}

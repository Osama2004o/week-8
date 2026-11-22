output "s3_bucket_name" {
  description = "Name of the S3 bucket for document storage."
  value       = aws_s3_bucket.documents.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket for document storage."
  value       = aws_s3_bucket.documents.arn
}

output "efs_file_system_id" {
  description = "ID of the EFS file system."
  value       = aws_efs_file_system.rag_data.id
}

output "efs_chroma_access_point_id" {
  description = "EFS access point ID for ChromaDB persistence."
  value       = aws_efs_access_point.chroma_db.id
}

output "efs_uploads_access_point_id" {
  description = "EFS access point ID for uploaded OCR images."
  value       = aws_efs_access_point.image_uploads.id
}

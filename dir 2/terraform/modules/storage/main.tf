# -----------------------------------------------------------------------------
# S3 Bucket for Source Documents & Knowledge Base Backups
# -----------------------------------------------------------------------------

resource "aws_s3_bucket" "documents" {
  bucket = "${var.name_prefix}-documents"

  tags = {
    Name = "${var.name_prefix}-documents"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = var.enable_s3_versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# EFS File System for Persistent ChromaDB Vectors & OCR Image Uploads
# -----------------------------------------------------------------------------

resource "aws_efs_file_system" "rag_data" {
  creation_token   = "${var.name_prefix}-efs"
  encrypted        = true
  performance_mode = var.efs_performance_mode
  throughput_mode  = "bursting"

  tags = {
    Name = "${var.name_prefix}-efs"
  }
}

resource "aws_efs_mount_target" "rag_data" {
  count = length(var.private_subnet_ids)

  file_system_id  = aws_efs_file_system.rag_data.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [var.efs_security_group_id]
}

resource "aws_efs_access_point" "chroma_db" {
  file_system_id = aws_efs_file_system.rag_data.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/chroma_db"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name = "${var.name_prefix}-chroma-ap"
  }
}

resource "aws_efs_access_point" "image_uploads" {
  file_system_id = aws_efs_file_system.rag_data.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/uploads"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name = "${var.name_prefix}-uploads-ap"
  }
}

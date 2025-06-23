resource "aws_s3_bucket" "main" {
  bucket        = "${var.name}-documents-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# bucket for storing llm logs
resource "aws_s3_bucket" "llm_logs" {
  bucket        = "${var.name}-llm-logs-${local.account_id}"
  force_destroy = true
}

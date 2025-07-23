# deliver kb sync logs to s3
resource "awscc_logs_delivery_source" "kb_logs" {
  name         = "${var.name}-kb-logs"
  log_type     = "APPLICATION_LOGS"
  resource_arn = aws_bedrockagent_knowledge_base.main.arn
  tags = [for k, v in var.tags : {
    key   = k
    value = v
  }]
}

resource "awscc_logs_delivery_destination" "kb_logs" {
  name                     = "${var.name}-kb-logs"
  destination_resource_arn = aws_s3_bucket.kb_logs.arn
  tags = [for k, v in var.tags : {
    key   = k
    value = v
  }]
}

resource "awscc_logs_delivery" "kb_logs" {
  delivery_source_name     = awscc_logs_delivery_source.kb_logs.name
  delivery_destination_arn = awscc_logs_delivery_destination.kb_logs.arn
  tags = [for k, v in var.tags : {
    key   = k
    value = v
  }]
}

resource "aws_s3_bucket" "kb_logs" {
  bucket = "${var.name}-kb-logs-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "kb_logs" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

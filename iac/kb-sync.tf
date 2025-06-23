# schedule a KB sync every hour
resource "aws_scheduler_schedule" "main" {
  name                = "${var.name}-kb-sync"
  schedule_expression = "rate(5 minutes)"
  state               = "ENABLED"

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:bedrockagent:startIngestionJob"
    role_arn = aws_iam_role.event_bridge_scheduler.arn

    input = jsonencode({
      KnowledgeBaseId = aws_bedrockagent_knowledge_base.main.id
      DataSourceId    = aws_bedrockagent_data_source.main.data_source_id
    })
  }

  flexible_time_window {
    mode = "OFF"
  }
}

resource "aws_iam_role" "event_bridge_scheduler" {
  name = "${var.name}-event-bridge-scheduler-role"

  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "scheduler.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  EOF
}

data "aws_iam_policy_document" "kb_sync" {
  statement {
    effect    = "Allow"
    actions   = ["bedrock:StartIngestionJob"]
    resources = [aws_bedrockagent_knowledge_base.main.arn]
  }
}

resource "aws_iam_role_policy" "event_bridge_scheduler" {
  role   = aws_iam_role.event_bridge_scheduler.name
  policy = data.aws_iam_policy_document.kb_sync.json
}

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

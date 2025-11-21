
resource "aws_sqs_queue" "main" {
  name                       = "${var.name}-events"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 86400 # 1 day
  receive_wait_time_seconds  = 10    # Enable long polling
  visibility_timeout_seconds = 180   # Visibility timeout for processing

  # Configure the DLQ redrive policy
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3 # Send to DLQ after 3 failed processing attempts
  })

  tags = var.tags
}

# SQS queue policy to allow Lambda to receive messages
resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      }
    ]
  })
}

# Dead Letter Queue for failed message processing
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-events-dlq"
  delay_seconds             = 0
  max_message_size          = 262144
  message_retention_seconds = 1209600 # 14 days (maximum retention)
  receive_wait_time_seconds = 10      # Enable long polling

  tags = merge(var.tags, {
    purpose = "dead-letter-queue"
  })
}

# DLQ policy to allow Lambda to receive messages from the DLQ if needed
resource "aws_sqs_queue_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.dlq.arn
      }
    ]
  })
}

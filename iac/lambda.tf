# Configure Docker provider to use AWS ECR
provider "docker" {
  registry_auth {
    address  = "${local.account_id}.dkr.ecr.${local.region}.amazonaws.com"
    username = "AWS"
    password = data.aws_ecr_authorization_token.token.password
  }
}

# Build and push the Lambda container image using Docker provider
resource "docker_image" "lambda_image" {
  name = "${aws_ecr_repository.lambda.repository_url}:latest"

  build {
    context    = "${path.module}/.."
    dockerfile = "events/Dockerfile"
    platform   = "linux/arm64"
  }

  depends_on = [aws_ecr_repository.lambda]
}

# Push the image to ECR
resource "docker_registry_image" "lambda_registry_image" {
  name          = docker_image.lambda_image.name
  keep_remotely = true

  depends_on = [docker_image.lambda_image]
}

resource "aws_lambda_function" "message_processor" {
  function_name = "${var.name}-events"
  description   = "Lambda function to process async events"

  # Use container image instead of zip file
  package_type = "Image"
  image_uri    = docker_registry_image.lambda_registry_image.name

  architectures = ["arm64"]
  timeout       = 120
  memory_size   = 256
  role          = aws_iam_role.lambda_role.arn

  # VPC configuration to run in the same VPC as the database
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.main.url,

      # database connection info
      POSTGRES_HOST         = module.aurora_postgres.cluster_endpoint
      POSTGRES_DB           = local.database_name
      DB_SECRET_ARN         = local.aurora_secret_arn,
      SCRIBE_SUMMARY_ID     = awscc_bedrock_prompt.interview_summary.id,
      DOCUMENT_GENERATOR_ID = awscc_bedrock_prompt.interview_pdfgen.id,
      S3_BUCKET_NAME        = aws_s3_bucket.main.id,
      KNOWLEDGE_BASE_ID     = aws_bedrockagent_knowledge_base.main.id,
      DATA_SOURCE_ID        = aws_bedrockagent_data_source.main.data_source_id,
    }
  }

  tags = var.tags

  # Ensure the image is built and pushed before creating the Lambda function
  depends_on = [docker_registry_image.lambda_registry_image]

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# IAM role for the Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for Lambda to access SQS and CloudWatch Logs
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.name}-lambda-policy"
  description = "Policy for Lambda to access SQS and CloudWatch Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.main.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.lambda.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [local.aurora_secret_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:GetPrompt"]
        Resource = ["${local.bedrock_arn_root}:prompt/*"]
      },
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "${local.bedrock_arn_root}:inference-profile/us.${local.model_id_sonnet_3_5}",
        ]
      },
      {
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:${local.inference_region1}::foundation-model/${local.model_id_sonnet_3_5}",
          "arn:aws:bedrock:${local.inference_region2}::foundation-model/${local.model_id_sonnet_3_5}",
          "arn:aws:bedrock:${local.inference_region3}::foundation-model/${local.model_id_sonnet_3_5}",
        ]
        Condition = {
          StringLike = {
            "bedrock:InferenceProfileArn" = [
              "${local.bedrock_arn_root}:inference-profile/us.${local.model_id_sonnet_3_5}",
            ]
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:DeleteObject",
        ]
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:StartIngestionJob"]
        Resource = [aws_bedrockagent_knowledge_base.main.arn]
      },
    ]
  })
}

# Attach the policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Event source mapping to trigger Lambda from SQS
resource "aws_lambda_event_source_mapping" "sqs_lambda_mapping" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.message_processor.function_name
  batch_size       = 1 # Process only one message at a time
}

# Security group for Lambda function
resource "aws_security_group" "lambda_sg" {
  name        = "${var.name}-lambda-sg"
  description = "Security group for Lambda function"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

# Allow Lambda to connect to the database
resource "aws_security_group_rule" "lambda_to_db" {
  type                     = "ingress"
  from_port                = module.aurora_postgres.cluster_port
  to_port                  = module.aurora_postgres.cluster_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lambda_sg.id
  security_group_id        = module.aurora_postgres.security_group_id
  description              = "Allow Lambda to connect to the database"
}

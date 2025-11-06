# Voice Mode Infrastructure for Nova Sonic Integration

locals {
  # Nova Sonic model configuration
  nova_sonic_model_id = "amazon.nova-sonic-v1:0"

  # Voice Lambda function configuration
  voice_lambda_name    = "${var.name}-voice"
  voice_lambda_timeout = 900 # 15 minutes for long voice sessions
  voice_lambda_memory  = 512 # Sufficient for audio processing

  image_tag = "latest"
}

# ECR repository for voice Lambda function
resource "aws_ecr_repository" "voice_lambda" {
  name = local.voice_lambda_name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# AppSync Events API for real-time voice communication
resource "aws_appsync_api" "voice_events" {
  name = "${var.name}-voice-events"

  # Authentication configuration for Events API
  event_config {
    auth_provider {
      auth_type = "AWS_IAM"
    }
    auth_provider {
      auth_type = "AMAZON_COGNITO_USER_POOLS"
      cognito_config {
        user_pool_id = aws_cognito_user_pool.main.id
        aws_region   = local.region
      }
    }
    connection_auth_mode {
      auth_type = "AWS_IAM"
    }
    connection_auth_mode {
      auth_type = "AMAZON_COGNITO_USER_POOLS"
    }
    default_publish_auth_mode {
      auth_type = "AWS_IAM"
    }
    default_publish_auth_mode {
      auth_type = "AMAZON_COGNITO_USER_POOLS"
    }
    default_subscribe_auth_mode {
      auth_type = "AWS_IAM"
    }
    default_subscribe_auth_mode {
      auth_type = "AMAZON_COGNITO_USER_POOLS"
    }
  }

  tags = var.tags
}

# Channel namespace for voice events
resource "aws_appsync_channel_namespace" "voice_events" {
  api_id = aws_appsync_api.voice_events.api_id
  name   = "nova-sonic-voice"

  # Channel authorization handler as a string
  code_handlers = <<EOF
import { util } from '@aws-appsync/utils';

export function onSubscribe(ctx) {
  // Allow all subscriptions for now - can add authorization later
  console.log('Subscription request for channel:', ctx.info.channel.path);
}
EOF

  # Authentication modes for publishing and subscribing
  publish_auth_mode {
    auth_type = "AWS_IAM"
  }
  publish_auth_mode {
    auth_type = "AMAZON_COGNITO_USER_POOLS"
  }
  subscribe_auth_mode {
    auth_type = "AWS_IAM"
  }
  subscribe_auth_mode {
    auth_type = "AMAZON_COGNITO_USER_POOLS"
  }

  tags = var.tags
}

# IAM role for AppSync Events API
resource "aws_iam_role" "appsync_events_role" {
  name = "${var.name}-appsync-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "appsync.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM policy for AppSync Events API
resource "aws_iam_policy" "appsync_events_policy" {
  name        = "${var.name}-appsync-events-policy"
  description = "Policy for AppSync Events API to invoke Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.voice_processor.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Attach policy to AppSync Events role
resource "aws_iam_role_policy_attachment" "appsync_events_policy_attachment" {
  role       = aws_iam_role.appsync_events_role.name
  policy_arn = aws_iam_policy.appsync_events_policy.arn
}

# Build and push the Voice Lambda container image using Docker provider
resource "docker_image" "voice_lambda_image" {
  name = "${aws_ecr_repository.voice_lambda.repository_url}:${local.image_tag}"

  build {
    context = "${path.module}/../voice"
    platform = "linux/arm64"
  }

  depends_on = [aws_ecr_repository.voice_lambda]
}

# Push the voice image to ECR
resource "docker_registry_image" "voice_lambda_registry_image" {
  name          = docker_image.voice_lambda_image.name
  keep_remotely = true

  depends_on = [docker_image.voice_lambda_image]
}

# Voice processing Lambda function
resource "aws_lambda_function" "voice_processor" {
  function_name = local.voice_lambda_name
  description   = "Lambda function to process Nova Sonic voice interactions"

  # Use container image
  package_type = "Image"
  image_uri    = docker_registry_image.voice_lambda_registry_image.name

  architectures = ["arm64"]
  timeout       = local.voice_lambda_timeout
  memory_size   = local.voice_lambda_memory
  role          = aws_iam_role.voice_lambda_role.arn

  # VPC configuration to run in the same VPC as the database
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.voice_lambda_sg.id]
  }

  environment {
    variables = {
      LOG_LEVEL = "warn"

      # Database connection info
      POSTGRES_HOST = module.aurora_postgres.cluster_endpoint
      POSTGRES_DB   = local.database_name
      DB_SECRET_ARN = local.aurora_secret_arn

      # AppSync Events API configuration
      APPSYNC_EVENTS_ENDPOINT = "https://${aws_appsync_api.voice_events.dns["HTTP"]}"

      # Nova Sonic model configuration
      NOVA_SONIC_MODEL_ID = local.nova_sonic_model_id
    }
  }

  tags = var.tags

  # Ensure the image is built and pushed before creating the Lambda function
  depends_on = [docker_registry_image.voice_lambda_registry_image]

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# IAM role for the Voice Lambda function
resource "aws_iam_role" "voice_lambda_role" {
  name = "${var.name}-voice-lambda-role"

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

# IAM policy for Voice Lambda function
resource "aws_iam_policy" "voice_lambda_policy" {
  name        = "${var.name}-voice-lambda-policy"
  description = "Policy for Voice Lambda to access Nova Sonic, AppSync Events, and database"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
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
        Resource = aws_ecr_repository.voice_lambda.arn
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
        # Nova Sonic model access
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${local.region}::foundation-model/${local.nova_sonic_model_id}",
          "arn:aws:bedrock:us-east-1::foundation-model/${local.nova_sonic_model_id}",
          "arn:aws:bedrock:us-west-2::foundation-model/${local.nova_sonic_model_id}"
        ]
      },
      {
        # AppSync Events API access
        Effect = "Allow"
        Action = [
          "appsync:EventConnect",
          "appsync:EventPublish",
          "appsync:EventSubscribe"
        ]
        Resource = [
          "${aws_appsync_api.voice_events.api_arn}",
          "${aws_appsync_api.voice_events.api_arn}/*"
        ]
      }
    ]
  })
}

# Attach the policy to the Voice Lambda role
resource "aws_iam_role_policy_attachment" "voice_lambda_policy_attachment" {
  role       = aws_iam_role.voice_lambda_role.name
  policy_arn = aws_iam_policy.voice_lambda_policy.arn
}

# Security group for Voice Lambda function
resource "aws_security_group" "voice_lambda_sg" {
  name        = "${var.name}-voice-lambda-sg"
  description = "Security group for Voice Lambda function"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

# Allow Voice Lambda to connect to the database
resource "aws_security_group_rule" "voice_lambda_to_db" {
  type                     = "ingress"
  from_port                = module.aurora_postgres.cluster_port
  to_port                  = module.aurora_postgres.cluster_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.voice_lambda_sg.id
  security_group_id        = module.aurora_postgres.security_group_id
  description              = "Allow Voice Lambda to connect to the database"
}

# AppSync Events API doesn't use traditional GraphQL data sources and resolvers
# Event handling is done through the Lambda function directly

# Lambda permission for AppSync Events to invoke the function
resource "aws_lambda_permission" "appsync_events_invoke_voice_lambda" {
  statement_id  = "AllowAppSyncEventsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.voice_processor.function_name
  principal     = "appsync.amazonaws.com"
  source_arn    = aws_appsync_api.voice_events.api_arn
}

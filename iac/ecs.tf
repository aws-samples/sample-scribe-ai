locals {
  session_key_secret_name = "${var.name}-session-key"
}

data "aws_secretsmanager_secret" "session_key" {
  name = local.session_key_secret_name
}

module "ecs_cluster" {
  source  = "terraform-aws-modules/ecs/aws//modules/cluster"
  version = "~> 5.6"

  cluster_name = var.name

  fargate_capacity_providers = {
    FARGATE      = {}
    FARGATE_SPOT = {}
  }

  tags = var.tags
}

resource "aws_service_discovery_http_namespace" "main" {
  name        = var.name
  description = "CloudMap namespace for ${var.name}"
  tags        = var.tags
}

module "ecs_service" {
  source  = "terraform-aws-modules/ecs/aws//modules/service"
  version = "~> 5.6"

  name        = var.name
  cluster_arn = module.ecs_cluster.arn

  cpu    = 1024
  memory = 2048

  # Set ARM64 architecture for the task
  runtime_platform = {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  # supports external task def deployments
  # by ignoring changes to task definition and desired count
  ignore_task_definition_changes = true
  desired_count                  = 2

  # keep 2 at a minimum when autoscaling
  autoscaling_min_capacity = 2

  # Task Definition
  enable_execute_command = false

  # Service Connect Configuration
  service_connect_configuration = {
    enabled   = true
    namespace = aws_service_discovery_http_namespace.main.arn

    service = {
      port_name      = "http"
      discovery_name = var.name
      client_alias = {
        dns_name = var.name
        port     = var.container_port
      }
    }
  }

  container_definitions = {
    (var.container_name) = {

      image = var.image

      port_mappings = [
        {
          name          = "http",
          protocol      = "tcp",
          containerPort = var.container_port
        }
      ]

      environment = [
        {
          "name" : "LOG_LEVEL",
          "value" : "INFO",
        },
        {
          "name" : "PORT",
          "value" : var.container_port
        },
        {
          "name" : "HEALTHCHECK",
          "value" : var.health_check
        },
        {
          "name" : "POSTGRES_DB"
          "value" : local.database_name
        },
        {
          "name" : "POSTGRES_HOST"
          "value" : module.aurora_postgres.cluster_endpoint
        },
        {
          "name" : "KNOWLEDGE_BASE_ID",
          "value" : aws_bedrockagent_knowledge_base.main.id
        },
        {
          "name" : "DB_SECRET_ARN",
          "value" : local.aurora_secret_arn
        },
        {
          "name" : "OTEL_RESOURCE_ATTRIBUTES",
          "value" : "service.namespace=${var.name},service.name=orchestrator"
        },
        {
          "name" : "AWS_COGNITO_DOMAIN",
          "value" : local.cognito_domain,
        },
        {
          "name" : "AWS_COGNITO_USER_POOL_ID",
          "value" : aws_cognito_user_pool.main.id,
        },
        {
          "name" : "AWS_COGNITO_APP_CLIENT_ID",
          "value" : aws_cognito_user_pool_client.client.id,
        },
        {
          "name" : "AWS_COGNITO_APP_CLIENT_SECRET",
          "value" : aws_cognito_user_pool_client.client.client_secret,
        },
        {
          "name" : "AWS_COGNITO_REDIRECT_URL",
          "value" : "${local.https_endpoint}/${local.callback_path}",
        },
        {
          "name" : "S3_BUCKET_NAME",
          "value" : aws_s3_bucket.main.id,
        },
        {
          "name" : "KB_GENERATOR_ID",
          "value" : awscc_bedrock_prompt.kb_generator.id,
        },
        {
          "name" : "PROMPT_INTERVIEW_USER",
          "value" : awscc_bedrock_prompt.interview_user.id,
        },
        {
          "name" : "PROMPT_INTERVIEW_SYSTEM",
          "value" : awscc_bedrock_prompt.interview_system.id,
        },
        {
          "name" : "PROMPT_CHAT_SYSTEM",
          "value" : awscc_bedrock_prompt.chat_system.id,
        },
        {
          "name" : "PROMPT_CHAT_USER",
          "value" : awscc_bedrock_prompt.chat_user.id,
        },
        {
          "name" : "PROMPT_CHAT_REWORD",
          "value" : awscc_bedrock_prompt.chat_reword.id,
        },
        {
          "name" : "SCRIBE_SUMMARY_ID",
          "value" : awscc_bedrock_prompt.scribe_summary.id,
        },
        {
          "name" : "DOCUMENT_GENERATOR_ID",
          "value" : awscc_bedrock_prompt.document_generator.id,
        },
        {
          "name" : "FLASK_SECRET_KEY_NAME",
          "value" : local.session_key_secret_name,
        },
        {
          "name" : "SQS_QUEUE_URL",
          "value" : aws_sqs_queue.main.url,
        },
      ]

      readonly_root_filesystem = false

      dependsOn = [
        {
          containerName = "otel"
          condition     = "HEALTHY"
        }
      ]
    },
    otel = {
      image   = "public.ecr.aws/aws-observability/aws-otel-collector:v0.41.2"
      command = ["--config=/etc/ecs/ecs-default-config.yaml"]
      healthCheck = {
        command     = ["/healthcheck"]
        interval    = 5
        timeout     = 6
        retries     = 5
        startPeriod = 1
      }
    },
  }

  subnet_ids = module.vpc.private_subnets

  security_group_rules = {
    ingress_api_gateway = {
      type                     = "ingress"
      from_port                = var.container_port
      to_port                  = var.container_port
      protocol                 = "tcp"
      description              = "Service port"
      source_security_group_id = aws_security_group.vpc_link.id
    }
    egress_all = {
      type        = "egress"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  tasks_iam_role_name        = "${var.name}-tasks"
  tasks_iam_role_description = "role for ${var.name}"

  tasks_iam_role_statements = [
    {
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [local.aurora_secret_arn]
    },
    {
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [data.aws_secretsmanager_secret.session_key.arn]
    },
    {
      actions   = ["bedrock:Retrieve"]
      resources = ["${local.bedrock_arn_root}:knowledge-base/*"]
    },
    {
      actions   = ["bedrock:GetPrompt"]
      resources = ["${local.bedrock_arn_root}:prompt/*"]
    },
    {
      # inference profile access
      actions = ["bedrock:InvokeModel"]
      resources = [
        "${local.bedrock_arn_root}:inference-profile/us.${local.model_id_haiku_3_5}",
        "${local.bedrock_arn_root}:inference-profile/us.${local.model_id_sonnet_3_5}",
      ]
    },
    {
      # underlying bedrock access restricted to inference profile
      actions = ["bedrock:InvokeModel"]
      resources = [
        "arn:aws:bedrock:${local.inference_region1}::foundation-model/${local.model_id_haiku_3_5}",
        "arn:aws:bedrock:${local.inference_region2}::foundation-model/${local.model_id_haiku_3_5}",
        "arn:aws:bedrock:${local.inference_region3}::foundation-model/${local.model_id_haiku_3_5}",
      ]
      conditions = [{
        test     = "StringLike"
        variable = "bedrock:InferenceProfileArn"
        values = [
          "${local.bedrock_arn_root}:inference-profile/us.${local.model_id_haiku_3_5}",
        ]
      }]
    },
    {
      actions = [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ]
      resources = ["*"]
    },
    {
      actions   = ["cognito-idp:ListUsers"]
      resources = [aws_cognito_user_pool.main.arn]
    },
    {
      actions = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      resources = [
        aws_s3_bucket.main.arn,
        "${aws_s3_bucket.main.arn}/*"
      ]
    },
    {
      actions = [
        "sqs:sendmessage",
      ]
      resources = [
        aws_sqs_queue.main.arn,
      ]
    },
  ]

  tags = var.tags
}

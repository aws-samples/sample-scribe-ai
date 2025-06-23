locals {
  aurora_cluster_arn  = module.aurora_postgres.cluster_arn
  database_name       = module.aurora_postgres.cluster_database_name
  aurora_secret_arn   = module.aurora_postgres.cluster_master_user_secret[0].secret_arn
  bedrock_user        = "bedrock_user"
  bedrock_user_secret = aws_secretsmanager_secret.kb_creds.arn

  # kb table info
  schema         = "bedrock_integration"
  table          = "bedrock_kb"
  pkey_field     = "id"
  vector_field   = "embedding"
  text_field     = "chunks"
  metadata_field = "metadata"
}

module "aurora_postgres" {
  source = "terraform-aws-modules/rds-aurora/aws"

  name                        = var.name
  engine                      = data.aws_rds_engine_version.postgres.engine
  engine_version              = data.aws_rds_engine_version.postgres.version
  engine_mode                 = "provisioned"
  storage_encrypted           = true
  database_name               = "postgres"
  master_username             = "postgres"
  manage_master_user_password = true
  enable_http_endpoint        = true

  serverlessv2_scaling_configuration = {
    min_capacity = 0.5
    max_capacity = 2
  }

  instance_class = "db.serverless"
  instances = {
    "1" = {}
  }

  # networking
  vpc_id                 = module.vpc.vpc_id
  subnets                = module.vpc.private_subnets
  create_db_subnet_group = true
  security_group_rules = {
    ingress = {
      type                     = "ingress"
      description              = "restricts ingress to app container"
      source_security_group_id = module.ecs_service.security_group_id
    }
    egress = {
      type        = "egress"
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  backup_retention_period = 7
  monitoring_interval     = 60
  apply_immediately       = true
  skip_final_snapshot     = true
}

# credentials that bedrock kb uses
resource "aws_secretsmanager_secret" "kb_creds" {
  name_prefix             = "${var.name}-kb-creds"
  recovery_window_in_days = 0
}

resource "random_password" "kb_password" {
  length  = 16
  special = false
}

# create a secret in AWS Secrets Manager using username and password
resource "aws_secretsmanager_secret_version" "v1" {
  secret_id = aws_secretsmanager_secret.kb_creds.id
  secret_string = jsonencode({
    username = local.bedrock_user
    password = random_password.kb_password.result
  })
}

resource "null_resource" "postgres_setup" {
  provisioner "local-exec" {
    command = "./database.sh"
    environment = {
      AWS_REGION  = data.aws_region.current.name
      CLUSTER_ARN = local.aurora_cluster_arn
      DB_NAME     = local.database_name
      DB_USER     = local.bedrock_user
      DB_PASSWORD = random_password.kb_password.result
      ADMIN       = local.aurora_secret_arn
      USER        = local.bedrock_user_secret
      SCHEMA      = local.schema
      TABLE       = local.table
      PKEY        = local.pkey_field
      VECTOR      = local.vector_field
      TEXT        = local.text_field
      METADATA    = local.metadata_field
    }
  }

  # need the database ready before updating schema
  depends_on = [module.aurora_postgres]
}

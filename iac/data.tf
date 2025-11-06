locals {
  region     = data.aws_region.current.id
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {}

data "aws_rds_engine_version" "postgres" {
  engine  = "aurora-postgresql"
  version = "15.12"
}

# Get ECR authorization token
data "aws_ecr_authorization_token" "token" {}

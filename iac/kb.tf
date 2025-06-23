locals {
  embedding_model_arn = "arn:aws:bedrock:${local.region}::foundation-model/amazon.titan-embed-g1-text-02"
}

resource "aws_bedrockagent_knowledge_base" "main" {
  name        = var.name
  description = "kb for ${var.name}"
  role_arn    = aws_iam_role.bedrock_kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn
    }
  }

  storage_configuration {
    type = "RDS"
    rds_configuration {
      credentials_secret_arn = local.bedrock_user_secret
      database_name          = local.database_name
      resource_arn           = local.aurora_cluster_arn
      table_name             = "${local.schema}.${local.table}"
      field_mapping {
        metadata_field    = local.metadata_field
        primary_key_field = local.pkey_field
        text_field        = local.text_field
        vector_field      = local.vector_field
      }
    }
  }

  # ensure that the postgres bedrock schema/table
  # is created before the knowledge base is created
  depends_on = [null_resource.postgres_setup]
}

resource "aws_bedrockagent_data_source" "main" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = aws_s3_bucket.main.bucket
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.main.arn
    }
  }
  data_deletion_policy = "RETAIN"
}

resource "aws_iam_role" "bedrock_kb_role" {
  name               = "BedrockExecutionRoleForKnowledgeBase-${var.name}"
  assume_role_policy = data.aws_iam_policy_document.kb_assume.json
}

resource "aws_iam_role_policy" "kb" {
  role   = aws_iam_role.bedrock_kb_role.name
  policy = data.aws_iam_policy_document.kb.json
}

data "aws_iam_policy_document" "kb_assume" {
  statement {
    sid     = "AmazonBedrockKnowledgeBaseTrustPolicy"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock:${local.region}:${local.account_id}:knowledge-base/*"]
    }
  }
}

data "aws_iam_policy_document" "kb" {
  statement {
    sid       = "BedrockInvokeModelStatement"
    effect    = "Allow"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }

  statement {
    sid       = "RdsDescribeStatementID"
    effect    = "Allow"
    actions   = ["rds:DescribeDBClusters"]
    resources = [local.aurora_cluster_arn]
  }

  statement {
    sid    = "DataAPIStatementID"
    effect = "Allow"
    actions = [
      "rds-data:BatchExecuteStatement",
      "rds-data:ExecuteStatement",
    ]
    resources = [local.aurora_cluster_arn]
  }

  statement {
    sid       = "S3ListBucketStatement"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.main.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }

  statement {
    sid       = "S3GetObjectStatement"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.main.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }

  statement {
    sid       = "SecretsManagerGetStatement"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [local.bedrock_user_secret]
  }
}

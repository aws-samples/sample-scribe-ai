output "name" {
  description = "The name of the application"
  value       = var.name
}

output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "ecs_cluster_name" {
  description = "The name of the ecs cluster that was created or referenced"
  value       = module.ecs_cluster.name
}

output "ecs_cluster_arn" {
  description = "The arn of the ecs cluster that was created or referenced"
  value       = module.ecs_cluster.arn
}

output "ecs_service_name" {
  description = "The arn of the fargate ecs service that was created"
  value       = module.ecs_service.name
}

output "api_gateway_id" {
  description = "The ID of the API Gateway"
  value       = aws_apigatewayv2_api.main.id
}

output "api_gateway_endpoint" {
  description = "The API Gateway endpoint"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "endpoint" {
  description = "The web application endpoint"
  value       = local.https_endpoint
}

output "db_cluster_endpoint" {
  description = "The write endpoint for the database cluster"
  value       = module.aurora_postgres.cluster_endpoint
}

output "db_cluster_arn" {
  description = "The ARN of the database cluster"
  value       = local.aurora_cluster_arn
}

output "db_creds_secret_arn" {
  description = "The ARN of the secret that contains the database credentials"
  value       = local.aurora_secret_arn
}

output "db_creds_bedrock_secret_arn" {
  description = "The name of the secret that contains the database credentials for Bedrock"
  value       = local.bedrock_user_secret
}

output "bedrock_knowledge_base_id" {
  description = "the id of the created bedrock knowledge base"
  value       = aws_bedrockagent_knowledge_base.main.id
}

output "bedrock_knowledge_base_data_source_id" {
  description = "the id of the created bedrock knowledge base data source"
  value       = aws_bedrockagent_data_source.main.data_source_id
}

output "s3_bucket_name" {
  description = "The name of the s3 bucket that was created"
  value       = aws_s3_bucket.main.bucket
}

output "cognito_domain" {
  description = "The domain of the cognito user pool"
  value       = local.cognito_domain
}
output "client_secret" {
  description = "The client secret of the cognito user pool client"
  value       = aws_cognito_user_pool_client.client.client_secret
  sensitive   = true
}

output "app_client_id" {
  description = "The client ID of the cognito user pool client"
  value       = aws_cognito_user_pool_client.client.id
}

output "user_pool_id" {
  description = "The id of the cognito user pool"
  value       = aws_cognito_user_pool.main.id
}

output "scribe_summary_id" {
  description = "The id of the created scribe summary"
  value       = awscc_bedrock_prompt.scribe_summary.id
}

output "kb_generator_id" {
  description = "The id of the created knowledge base generator"
  value       = awscc_bedrock_prompt.kb_generator.id
}

output "document_generator_id" {
  description = "The id of the created knowledge base generator"
  value       = awscc_bedrock_prompt.document_generator.id
}

output "prompt_interview_user" {
  description = "User prompt used to start an interview"
  value       = awscc_bedrock_prompt.interview_user.id
}

output "prompt_interview_system" {
  description = "System prompt used for interview"
  value       = awscc_bedrock_prompt.interview_system.id
}

output "prompt_chat_system" {
  description = "System prompt used for chatbot"
  value       = awscc_bedrock_prompt.chat_system.id
}

output "prompt_chat_user" {
  description = "User prompt used for chatbot"
  value       = awscc_bedrock_prompt.chat_user.id
}

output "prompt_chat_reword" {
  description = "Reword prompt used for chatbot"
  value       = awscc_bedrock_prompt.chat_reword.id
}

output "session_key_secret_name" {
  description = "Name of the Flask secret session key in Secrets Manager"
  value       = "${var.name}-session-key"
}

# SQS and Lambda outputs
output "sqs_queue_url" {
  description = "The URL of the SQS queue"
  value       = aws_sqs_queue.main.url
}

output "sqs_queue_arn" {
  description = "The ARN of the SQS queue"
  value       = aws_sqs_queue.main.arn
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.message_processor.arn
}

output "lambda_ecr_repository_url" {
  description = "URL of the Lambda ECR repository"
  value       = aws_ecr_repository.lambda.repository_url
}

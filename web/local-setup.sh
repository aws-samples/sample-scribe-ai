#!/bin/zsh
set -e

# Script to set up local environment for Scribe application
# This script extracts Cognito configuration from Terraform outputs

# Navigate to the infrastructure directory
cd ../iac

echo "Extracting configuration from Terraform outputs..."

# Extract Cognito configuration
COGNITO_DOMAIN=$(terraform output -raw cognito_domain 2>/dev/null || echo "")
USER_POOL_ID=$(terraform output -raw user_pool_id 2>/dev/null || echo "")
CLIENT_ID=$(terraform output -raw app_client_id 2>/dev/null || echo "")
CLIENT_SECRET=$(terraform output -raw client_secret 2>/dev/null || echo "")

KNOWLEDGE_BASE_ID=$(terraform output -raw bedrock_knowledge_base_id 2>/dev/null || echo "")
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
ENDPOINT=$(terraform output -raw endpoint 2>/dev/null || echo "")
SCRIBE_SUMMARY_ID=$(terraform output -raw scribe_summary_id 2>/dev/null || echo "")
KB_GENERATOR_ID=$(terraform output -raw kb_generator_id 2>/dev/null || echo "")
DOCUMENT_GENERATOR_ID=$(terraform output -raw document_generator_id 2>/dev/null || echo "")
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
PROMPT_INTERVIEW_USER=$(terraform output -raw prompt_interview_user 2>/dev/null || echo "")
PROMPT_INTERVIEW_SYSTEM=$(terraform output -raw prompt_interview_system 2>/dev/null || echo "")
PROMPT_INTERVIEW_VOICE=$(terraform output -raw prompt_interview_voice 2>/dev/null || echo "")
PROMPT_CHAT_SYSTEM=$(terraform output -raw prompt_chat_system 2>/dev/null || echo "")
PROMPT_CHAT_USER=$(terraform output -raw prompt_chat_user 2>/dev/null || echo "")
PROMPT_CHAT_REWORD=$(terraform output -raw prompt_chat_reword 2>/dev/null || echo "")
FLASK_SECRET_KEY_NAME=$(terraform output -raw session_key_secret_name 2>/dev/null || echo "")
SQS_QUEUE_URL=$(terraform output -raw sqs_queue_url 2>/dev/null || echo "")
APPSYNC_EVENTS_ENDPOINT=$(terraform output -raw appsync_events_endpoint 2>/dev/null || echo "")
VOICE_LAMBDA_FUNCTION_NAME=$(terraform output -raw voice_lambda_function_arn 2>/dev/null | sed 's/.*function://' || echo "")

# Create .env file
cd ..
mkdir -p web
cat << EOF > web/.env
LOG_LEVEL=INFO

# Database Configuration
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# AWS Configuration
AWS_REGION="${AWS_REGION}"
AWS_DEFAULT_REGION="${AWS_REGION}"
KNOWLEDGE_BASE_ID="${KNOWLEDGE_BASE_ID}"
S3_BUCKET_NAME="${S3_BUCKET_NAME}"
FLASK_SECRET_KEY_NAME="${FLASK_SECRET_KEY_NAME}"
SQS_QUEUE_URL="${SQS_QUEUE_URL}"
APPSYNC_EVENTS_ENDPOINT="${APPSYNC_EVENTS_ENDPOINT}"
VOICE_LAMBDA_FUNCTION_NAME="${VOICE_LAMBDA_FUNCTION_NAME}"

# Cognito Authentication Configuration
AWS_COGNITO_DOMAIN="${COGNITO_DOMAIN}"
AWS_COGNITO_USER_POOL_ID="${USER_POOL_ID}"
AWS_COGNITO_APP_CLIENT_ID="${CLIENT_ID}"
AWS_COGNITO_APP_CLIENT_SECRET="${CLIENT_SECRET}"
AWS_COGNITO_REDIRECT_URL=http://localhost:8080/auth/callback

# Bedrock Prompt Configuration
SCRIBE_SUMMARY_ID="${SCRIBE_SUMMARY_ID}"
KB_GENERATOR_ID="${KB_GENERATOR_ID}"
DOCUMENT_GENERATOR_ID="${DOCUMENT_GENERATOR_ID}"
PROMPT_INTERVIEW_USER="${PROMPT_INTERVIEW_USER}"
PROMPT_INTERVIEW_SYSTEM="${PROMPT_INTERVIEW_SYSTEM}"
PROMPT_INTERVIEW_VOICE="${PROMPT_INTERVIEW_VOICE}"
PROMPT_CHAT_SYSTEM="${PROMPT_CHAT_SYSTEM}"
PROMPT_CHAT_USER="${PROMPT_CHAT_USER}"
PROMPT_CHAT_REWORD="${PROMPT_CHAT_REWORD}"
EOF

echo "Local environment setup complete!"
echo "----------------------------------------"
echo "Configuration written to web/.env file"

if [ -z "$KNOWLEDGE_BASE_ID" ]; then
  echo "WARNING: KNOWLEDGE_BASE_ID is empty. Make sure to set it manually."
fi

if [ -z "$SCRIBE_SUMMARY_ID" ]; then
  echo "WARNING: Scribe Summary ID is empty. Make sure to set it manually."
fi

if [ -z "$KB_GENERATOR_ID" ]; then
  echo "WARNING: Knowledge Base Generator ID is empty. Make sure to set it manually."
fi

if [ -z "$DOCUMENT_GENERATOR_ID" ]; then
  echo "WARNING: Document Generator ID is empty. Make sure to set it manually."
fi

if [ -z "$S3_BUCKET_NAME" ]; then
  echo "WARNING: S3_BUCKET_NAME is empty. Make sure to set it manually."
fi

if [ -z "$COGNITO_DOMAIN" ] || [ -z "$USER_POOL_ID" ] || [ -z "$APP_CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
  echo "WARNING: Some Cognito configuration values are missing."
  echo "Make sure Terraform has been applied and outputs are available."
fi

if [ -z "$FLASK_SECRET_KEY_NAME" ]; then
  echo "WARNING: FLASK_SECRET_KEY_NAME is empty. Make sure to set it manually."
fi

echo "----------------------------------------"
echo "To run the application locally:"
echo "1. Make sure Docker Desktop is running"
echo "2. Run 'cd web && make baseimage' (if you haven't already)"
echo "3. Run 'cd web && make up'"
echo "----------------------------------------"

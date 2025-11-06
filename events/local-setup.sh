#!/bin/zsh
set -e

# Script to set up local environment for Scribe application
# This script extracts Cognito configuration from Terraform outputs

# Navigate to the infrastructure directory
cd ../iac

echo "Extracting configuration from Terraform outputs..."

AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

SCRIBE_SUMMARY_ID=$(terraform output -raw scribe_summary_id 2>/dev/null || echo "")
KB_GENERATOR_ID=$(terraform output -raw kb_generator_id 2>/dev/null || echo "")
DOCUMENT_GENERATOR_ID=$(terraform output -raw document_generator_id 2>/dev/null || echo "")
PROMPT_INTERVIEW_USER=$(terraform output -raw prompt_interview_user 2>/dev/null || echo "")
PROMPT_INTERVIEW_SYSTEM=$(terraform output -raw prompt_interview_system 2>/dev/null || echo "")
PROMPT_CHAT_SYSTEM=$(terraform output -raw prompt_chat_system 2>/dev/null || echo "")
PROMPT_CHAT_USER=$(terraform output -raw prompt_chat_user 2>/dev/null || echo "")
PROMPT_CHAT_REWORD=$(terraform output -raw prompt_chat_reword 2>/dev/null || echo "")
S3_BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")
AWS_COGNITO_USER_POOL_ID=$(terraform output -raw user_pool_id 2>/dev/null || echo "")

# Create .env file
cd ..
cat << EOF > events/.env
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# AWS Configuration
AWS_REGION="${AWS_REGION}"
AWS_DEFAULT_REGION="${AWS_REGION}"

# S3 Configuration
S3_BUCKET_NAME="${S3_BUCKET_NAME}"

# Cognito Configuration
AWS_COGNITO_USER_POOL_ID="${AWS_COGNITO_USER_POOL_ID}"

# Bedrock Prompt Configuration
SCRIBE_SUMMARY_ID="${SCRIBE_SUMMARY_ID}"
KB_GENERATOR_ID="${KB_GENERATOR_ID}"
DOCUMENT_GENERATOR_ID="${DOCUMENT_GENERATOR_ID}"
PROMPT_INTERVIEW_USER="${PROMPT_INTERVIEW_USER}"
PROMPT_INTERVIEW_SYSTEM="${PROMPT_INTERVIEW_SYSTEM}"
PROMPT_CHAT_SYSTEM="${PROMPT_CHAT_SYSTEM}"
PROMPT_CHAT_USER="${PROMPT_CHAT_USER}"
PROMPT_CHAT_REWORD="${PROMPT_CHAT_REWORD}"
EOF

echo "Local environment setup complete!"
echo "----------------------------------------"
echo "Configuration written to web/.env file"

if [ -z "$SCRIBE_SUMMARY_ID" ]; then
  echo "WARNING: Scribe Summary ID is empty. Make sure to set it manually."
fi

if [ -z "$KB_GENERATOR_ID" ]; then
  echo "WARNING: Knowledge Base Generator ID is empty. Make sure to set it manually."
fi

if [ -z "$DOCUMENT_GENERATOR_ID" ]; then
  echo "WARNING: Document Generator ID is empty. Make sure to set it manually."
fi

echo "----------------------------------------"
echo "To run the application locally:"
echo "1. Make sure Docker Desktop is running"
echo "3. Run 'cd events && make up'"
echo "----------------------------------------"

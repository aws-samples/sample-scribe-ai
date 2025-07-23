# Technology Stack

## Infrastructure
- **Cloud Platform**: AWS
- **Infrastructure as Code**: Terraform (>= 1.0)
- **Container Orchestration**: ECS Fargate
- **Database**: Aurora PostgreSQL Serverless
- **Storage**: S3
- **Authentication**: AWS Cognito
- **LLM Services**: AWS Bedrock
- **Monitoring**: AWS X-Ray with OpenTelemetry
- **Message Queue**: SQS

## Backend
- **Language**: Python 3.x
- **Web Framework**: Flask
- **WSGI Server**: Gunicorn
- **Database Client**: psycopg[binary]
- **AWS SDK**: boto3
- **Authentication**: authlib
- **Document Generation**: reportlab
- **Markdown Processing**: markdown2, html2text, beautifulsoup4
- **Observability**: aws-opentelemetry-distro, opentelemetry-instrumentation-psycopg

## Development Tools
- **Containerization**: Docker Desktop
- **Package Management**: pip with requirements.txt and piplock.txt
- **Build System**: Make
- **CLI Tools**: AWS CLI, jq, Terraform CLI

## Common Commands

### Initial Setup
```bash
# Deploy infrastructure
cd iac
terraform init -backend-config="bucket=${BUCKET}" -backend-config="key=${APP_NAME}.tfstate"
terraform apply

# Deploy web application
cd ../web
make baseimage && make deploy

# Deploy events (if code changes)
cd ../events
make deploy
```

### Local Development
```bash
# Setup local environment
./local-setup.sh

# Install dependencies
make install <package-name>

# Build base image (after installing dependencies)
cd web && make baseimage

# Run locally with Docker Compose
cd web && make up

# Stop local environment
cd web && make down
```

### Database Operations
```bash
# Apply database migrations to Aurora
cd iac
export CLUSTER_ARN=$(terraform output -raw db_cluster_arn)
export ADMIN=$(terraform output -raw db_creds_secret_arn)
export DB_NAME=postgres
./db-migrate.sh
```

### Terraform Operations
```bash
# Always run pre-commit checks before committing Terraform changes
cd iac
make check
```

## Architecture Patterns

- **Shared Code**: Common Python modules in `/shared` directory, symlinked into `/web/shared` and `/events/shared`
- **Event-Driven**: Asynchronous processing using SQS and Lambda
- **Microservices**: Separate web and events services
- **Configuration**: Environment variables with fallback defaults
- **Observability**: OpenTelemetry auto-instrumentation for Flask, PostgreSQL, and boto3
- **Security**: Cognito integration with role-based access control
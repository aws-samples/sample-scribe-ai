# Voice Mode Infrastructure

This directory contains the infrastructure and Lambda function code for Nova Sonic voice mode integration in Scribe AI.

## Overview

The voice mode feature enables users to conduct interviews using natural voice conversation instead of text-only interactions. It leverages AWS Nova Sonic speech-to-speech AI model through AWS Bedrock.

## Architecture Components

### Infrastructure (Terraform)

- **AppSync Events API**: Real-time bidirectional communication between client and Lambda
- **Voice Lambda Function**: Processes Nova Sonic voice interactions
- **ECR Repository**: Container registry for the Voice Lambda function
- **IAM Roles & Policies**: Permissions for Nova Sonic, AppSync Events, and database access
- **Security Groups**: VPC connectivity for Lambda-to-RDS communication

### Lambda Function

- **Runtime**: Node.js 18 on ARM64 architecture
- **Container**: Docker-based deployment for better dependency management
- **Memory**: 512MB (configurable)
- **Timeout**: 15 minutes for long voice sessions

### Database Extensions

- **voice_mode**: Boolean column to track voice-enabled interviews
- **voice_session_metadata**: JSONB column for session tracking and metadata

## Files Structure

```
voice/
├── Dockerfile              # Container configuration for Lambda
├── package.json            # Node.js dependencies
├── index.js               # Lambda entry point
├── src/
│   ├── nova-stream-handler.js    # Main voice processing logic
│   ├── database-manager.js       # PostgreSQL operations
│   └── appsync-events-client.js  # AppSync Events integration
├── Makefile               # Build and deployment commands
└── README.md             # This file
```

## Environment Variables

The Lambda function uses the following environment variables:

- `POSTGRES_HOST`: Aurora PostgreSQL cluster endpoint
- `POSTGRES_DB`: Database name
- `DB_SECRET_ARN`: ARN of database credentials secret
- `APPSYNC_EVENTS_ENDPOINT`: AppSync Events API endpoint
- `NOVA_SONIC_MODEL_ID`: Bedrock Nova Sonic model identifier
- `AWS_REGION`: AWS region

## Deployment

The voice infrastructure is deployed as part of the main Terraform configuration:

```bash
cd iac
terraform apply
```

This will:

1. Create the AppSync Events API
2. Build and push the Lambda container image
3. Deploy the Voice Lambda function
4. Apply database schema changes
5. Configure IAM permissions

## Development

To work on the voice Lambda function locally:

```bash
cd voice
make dev-setup
```

## Next Steps

This infrastructure foundation supports the following upcoming tasks:

- Task 4: Implement NovaStream class for bidirectional streaming
- Task 5: Build AppSync Events integration layer
- Task 6: Create PostgreSQL integration for transcription storage

## Security

- Lambda function runs in private VPC subnets
- Database access restricted to Lambda security group
- AppSync Events uses AWS IAM authentication
- Nova Sonic access limited to specific model ARNs

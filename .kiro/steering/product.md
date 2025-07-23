# Product Overview

Scribe AI is a knowledge capture assistant that transforms natural conversations with experts into structured, AI-ready documentation. It helps organizations preserve vital institutional knowledge while supporting digital transformation and AI initiatives.

## Core Capabilities

- **Knowledge Scope Configuration**: Define and manage knowledge domains and topics
- **Natural Language Conversation Capture**: Conduct structured interviews with subject matter experts
- **Human-in-the-Loop Review**: Review and approve captured knowledge before publication
- **Built-in Chatbot & API**: Query captured knowledge through web interface or REST API
- **Rich Document Generation**: Generate PDFs and structured documentation from conversations

## Key Features

- Deployable in under 15 minutes using Infrastructure as Code
- Auto-scaling architecture with ECS Fargate and Aurora Serverless
- LLM request/response logging to S3 for analysis and testing
- OpenTelemetry tracing support using AWS X-Ray
- Bedrock Knowledge Base integration for semantic search
- Cognito-based authentication with admin role management

## Architecture

The system follows an event-driven architecture with:
- Web application for user interactions and interviews
- Asynchronous event processing for knowledge base updates
- Bedrock integration for LLM capabilities and knowledge base search
- Aurora PostgreSQL for structured data storage
- S3 for document storage and LLM logging
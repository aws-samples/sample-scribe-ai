# Project Structure

## Root Directory Layout

```
.
├── web/          # Flask web application
├── events/       # Lambda event processing
├── shared/       # Common Python modules
├── iac/          # Terraform Infrastructure as Code
├── README.md     # Main project documentation
├── design.md     # System design documentation
└── architecture.png
```

## Web Application (`/web`)

```
web/
├── shared/           # Symlink to ../shared
├── templates/        # Jinja2 HTML templates
├── static/          # CSS, JS, favicon assets
├── requirements.txt  # Python dependencies
├── piplock.txt      # Locked dependency versions
├── Makefile         # Build and deployment commands
├── Dockerfile       # Multi-stage container build
├── Dockerfile.base  # Base image with dependencies
├── docker-compose.yml # Local development setup
├── app.py           # Flask application factory
├── main.py          # Application entry point
├── auth.py          # Cognito authentication
├── api.py           # REST API endpoints
├── chatbot.py       # Chat interface routes
├── interviews.py    # Interview management routes
├── admin.py         # Admin interface routes
├── reviews.py       # Review workflow routes
├── kb.py            # Knowledge base routes
└── docs.py          # Documentation routes
```

## Events Processing (`/events`)

```
events/
├── shared/              # Symlink to ../shared
├── events/              # Event handler modules
│   ├── event_processor.py
│   ├── interview_approved.py
│   └── interview_complete.py
├── requirements.txt     # Python dependencies
├── lambda_function.py   # Lambda entry point
├── main.py             # Local development entry
├── Dockerfile          # Container for Lambda
└── Makefile            # Build commands
```

## Shared Code (`/shared`)

```
shared/
├── config.py           # Environment configuration
├── events.py           # Event handling utilities
├── log.py              # Logging configuration
├── s3.py               # S3 utilities
├── pdf_generator.py    # PDF generation
├── data/               # Database layer
│   ├── data_models.py  # SQLAlchemy models
│   └── database.py     # Database client
├── llm/                # LLM integration
│   ├── bedrock_kb.py   # Knowledge base client
│   ├── bedrock_llm.py  # LLM client
│   └── orchestrator.py # LLM orchestration
└── prompts/            # LLM prompt templates
    ├── system_*.md     # System prompts
    ├── user_*.md       # User prompts
    └── interview_*.md  # Interview-specific prompts
```

## Infrastructure (`/iac`)

```
iac/
├── main.tf             # Main Terraform configuration
├── variables.tf        # Input variables
├── outputs.tf          # Output values
├── versions.tf         # Provider versions
├── terraform.tfvars    # Variable values
├── *.tf               # Resource definitions by service
│   ├── vpc.tf         # VPC and networking
│   ├── ecs.tf         # ECS cluster and services
│   ├── database.tf    # Aurora PostgreSQL
│   ├── cognito.tf     # Authentication
│   ├── bedrock.tf     # LLM services
│   ├── s3.tf          # Storage buckets
│   ├── sqs.tf         # Message queues
│   └── lambda.tf      # Event processing
├── .terraform/        # Terraform state and modules
└── Makefile           # Infrastructure commands
```

## Key Conventions

### File Organization
- **Route Modules**: Each major feature has its own Python module (e.g., `chatbot.py`, `interviews.py`)
- **Shared Dependencies**: Common code in `/shared` is symlinked, not copied
- **Template Structure**: HTML templates follow feature-based naming (`feature.action.html`)
- **Static Assets**: Organized by type (`css/`, `js/`, `favicon/`)

### Configuration Management
- **Environment Variables**: All configuration via environment variables
- **Secrets**: Sensitive data stored in AWS Secrets Manager
- **Defaults**: Fallback values in `shared/config.py`

### Database Patterns
- **Models**: SQLAlchemy models in `shared/data/data_models.py`
- **Client**: Database operations in `shared/data/database.py`
- **Migrations**: Manual SQL scripts executed via `db-migrate.sh`

### Deployment Structure
- **Infrastructure First**: Deploy Terraform before application code
- **Containerized Apps**: Both web and events use Docker containers
- **Separate Concerns**: Web app and event processing are independent services
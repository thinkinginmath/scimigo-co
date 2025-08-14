# Scimigo Curriculum Orchestrator

The Curriculum Orchestrator (CO) is the brain of SciMigo's learning platform, managing tracks/curricula, sessions, and orchestrating evaluations and tutoring across coding, math, and systems domains.

## Architecture Overview

```
[Frontend] → [CO API] → [Problem Bank]
                    ↓
            [Eval Service]
                    ↓
            [Tutor/LLM Service]
```

The CO serves as the single public gateway for:
- Track and curriculum management
- Session creation and progression
- Submission evaluation (routing to appropriate evaluators)
- Tutor orchestration with SSE streaming
- Personalized learning recommendations
- Spaced repetition review scheduling

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for local development)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/scimigo/curriculum-orchestrator.git
cd curriculum-orchestrator
```

2. Start the development environment:
```bash
docker-compose -f docker/docker-compose.dev.yml up
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- Adminer (DB UI) on port 8080
- API server on port 8000

3. Run database migrations:
```bash
docker-compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

4. Access the services:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Adminer: http://localhost:8080

### Manual Setup (without Docker)

1. Install dependencies:
```bash
pip install poetry
poetry install
```

2. Set environment variables:
```bash
export CO_DB_URL=postgresql+asyncpg://user:pass@localhost/scimigo_co
export CO_REDIS_URL=redis://localhost:6379/0
```

3. Run migrations:
```bash
alembic upgrade head
```

4. Start the server:
```bash
uvicorn co.server:app --reload --port 8000
```

## API Documentation

The API follows RESTful conventions with JSON payloads and JWT authentication.

### Key Endpoints

- `GET /v1/tracks` - List available learning tracks
- `POST /v1/sessions` - Create a new learning session
- `POST /v1/submissions` - Submit code/math for evaluation
- `POST /v1/tutor/messages` - Request tutoring assistance

Full OpenAPI specification: [openapi/co.v1.yaml](openapi/co.v1.yaml)

### Authentication

All endpoints require JWT Bearer tokens issued by `api.scimigo.com`:

```bash
curl -H "Authorization: Bearer <token>" https://co.scimigo.com/v1/tracks
```

## Development

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=co --cov-report=html

# Specific test file
poetry run pytest tests/unit/test_sessions.py -v
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/

# Lint
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

## Deployment

### AWS ECS Deployment

The service is configured for AWS ECS deployment with automatic CI/CD:

1. Push to `main` branch → Deploy to staging
2. Create git tag `v*` → Deploy to production

Required AWS resources:
- ECS Cluster
- ECR Repository
- RDS PostgreSQL
- ElastiCache Redis
- ALB with target groups

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CO_DB_URL` | PostgreSQL connection string | Required |
| `CO_REDIS_URL` | Redis connection string | Required |
| `CO_JWT_PUBLIC_KEY` | RSA public key for JWT verification | Required in prod |
| `CO_API_BASE` | Main API endpoint | `https://api.scimigo.com` |
| `CO_EVAL_BASE` | Evaluation service endpoint | Required |
| `CO_PROBLEM_BANK_BASE` | Problem bank internal API | Required |
| `CO_TUTOR_BASE` | Tutor/LLM service endpoint | Required |

## Service Integration

### Problem Bank
- Provides problem metadata and test bundles
- Hidden tests fetched server-side only
- Internal API authentication required

### Evaluation Service
- Secure code execution sandbox
- Math expression evaluation
- Returns pass/fail with timing metrics

### Tutor Service
- LLM-powered hint generation
- SSE streaming for real-time responses
- Context-aware assistance based on hint level

## Security

- JWT authentication for all public endpoints
- Hidden test bundles never exposed to clients
- Rate limiting: 60 requests/minute per user
- Maximum 2 concurrent SSE streams per user
- CORS configured for approved domains only

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run linting and tests
5. Submit a pull request

## License

Proprietary - SciMigo Inc.
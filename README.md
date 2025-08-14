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

- Docker & Docker Compose (recommended for local development)
- Python 3.11+ (for testing and code quality tools)
- Poetry (for dependency management)

### Local Development with Docker (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/scimigo/curriculum-orchestrator.git
cd curriculum-orchestrator
```

2. **Start the development environment:**
```bash
docker compose -f docker/docker-compose.dev.yml up -d
```

This starts:
- **PostgreSQL** on port 5432 (database: `scimigo_co`)
- **Redis** on port 6379 (caching and task queues)
- **Adminer** on port 8080 (database management UI)
- **API server** on port 8000 (auto-reload enabled)

3. **Run database migrations:**
```bash
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

4. **Verify setup:**
```bash
# Check migration status
docker compose -f docker/docker-compose.dev.yml exec api alembic current

# View API logs
docker compose -f docker/docker-compose.dev.yml logs -f api
```

5. **Access the services:**
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Database UI**: http://localhost:8080 (server: `postgres`, user: `scimigo`, password: `scimigo`)

6. **Stopping services:**
```bash
docker compose -f docker/docker-compose.dev.yml down
```

### Alternative: Local Python Setup

Only use this if you need to run tests outside Docker or prefer native Python development:

1. **Install Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Install dependencies:**
```bash
poetry install
```

3. **Set environment variables:**
```bash
export CO_DB_URL=postgresql+asyncpg://scimigo:scimigo@localhost:5432/scimigo_co
export CO_REDIS_URL=redis://localhost:6379/0
export CO_ENVIRONMENT=development
```

4. **Run migrations and start server:**
```bash
poetry run alembic upgrade head
poetry run uvicorn co.server:app --reload --port 8000
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

### Testing Strategy

We support multiple testing approaches depending on your workflow:

#### Option 1: Docker-based Testing (Recommended)

Best for: CI/CD consistency, isolated test environment

```bash
# Run tests in Docker (uses docker/docker-compose.test.yml)
make test-docker

# Or manually:
docker compose -f docker/docker-compose.test.yml up --build --remove-orphans test-runner --abort-on-container-exit
docker compose -f docker/docker-compose.test.yml down
```

The test environment uses:
- Separate test database (`scimigo_co_test`)
- Isolated test containers (postgres-test, redis-test)
- Dockerfile.test with all dev dependencies including pytest
- Automatic migration before tests

#### Option 2: Local Testing with Docker Services

Best for: Fast iteration, debugging, IDE integration

```bash
# Start only database services
docker compose -f docker/docker-compose.dev.yml up -d postgres redis

# Install local dependencies (one time)
poetry install

# Run tests locally against Docker services
export CO_DB_URL=postgresql+asyncpg://scimigo:scimigo@localhost:5432/scimigo_co_test
export CO_REDIS_URL=redis://localhost:6379/1  # Use DB 1 for tests
export CO_ENVIRONMENT=test

# Create test database
docker compose -f docker/docker-compose.dev.yml exec postgres createdb -U scimigo scimigo_co_test

# Run migrations
poetry run alembic upgrade head

# Run tests with various options
poetry run pytest                              # All tests
poetry run pytest --cov=co --cov-report=html  # With coverage report
poetry run pytest tests/unit/ -v              # Unit tests only  
poetry run pytest tests/e2e/ -v               # E2E tests only
poetry run pytest -k "test_sessions" -v       # Specific test pattern
poetry run pytest --lf                        # Last failed tests only
```

#### Option 3: Fully Local Testing (Advanced)

Best for: Development without Docker, custom setups

```bash
# Requires local PostgreSQL and Redis
# Install and start PostgreSQL 15+ and Redis 7+

# Set environment for local services
export CO_DB_URL=postgresql+asyncpg://username:password@localhost/scimigo_co_test
export CO_REDIS_URL=redis://localhost:6379/1
export CO_ENVIRONMENT=test

# Run tests
poetry run pytest
```

#### Test Organization

```
tests/
├── unit/          # Fast, isolated unit tests
│   ├── test_models.py
│   ├── test_services.py
│   └── test_utils.py
├── integration/   # Database and service integration tests
│   ├── test_api_endpoints.py
│   ├── test_database_operations.py
│   └── test_external_clients.py
├── e2e/          # End-to-end workflow tests
│   ├── test_submission_flow.py
│   ├── test_session_lifecycle.py
│   └── test_track_completion.py
└── fixtures/     # Test data and mocks
    ├── sample_problems.json
    └── mock_responses.py
```

#### OpenAI Codex/GitHub Copilot Testing

For AI-assisted development environments:

```bash
# Install testing dependencies
poetry install --with dev

# Run specific test files that AI tools can analyze
poetry run pytest tests/unit/test_models.py -v --tb=short

# Generate test coverage for AI context
poetry run pytest --cov=co --cov-report=json
# Coverage report saved to coverage.json for AI analysis

# Run tests with minimal output for clean AI feedback
poetry run pytest -q

# Test specific functionality during development
poetry run pytest -k "Meta" -v  # Tests related to Meta track
poetry run pytest -k "signal" -v  # Tests related to signal extraction
```

### Code Quality Tools

#### Running Code Quality Checks

```bash
# Format code (auto-fix)
poetry run black src/ tests/

# Check formatting without fixing
poetry run black --check src/ tests/

# Lint with auto-fix
poetry run ruff check src/ tests/ --fix

# Lint without auto-fix
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# Run all quality checks
poetry run black --check src/ tests/ && \
poetry run ruff check src/ tests/ && \
poetry run mypy src/
```

#### Pre-commit Hooks (Recommended)

```bash
# Install pre-commit hooks (one time)
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files

# Skip hooks for emergency commits
git commit -m "emergency fix" --no-verify
```

#### IDE Integration

For VS Code, add to `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"]
}
```

### Database Operations

#### Migrations in Docker (Recommended)

```bash
# Create new migration
docker compose -f docker/docker-compose.dev.yml exec api alembic revision --autogenerate -m "Add new table"

# Apply migrations
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head

# Check current migration
docker compose -f docker/docker-compose.dev.yml exec api alembic current

# View migration history
docker compose -f docker/docker-compose.dev.yml exec api alembic history

# Rollback one version
docker compose -f docker/docker-compose.dev.yml exec api alembic downgrade -1

# Rollback to specific revision
docker compose -f docker/docker-compose.dev.yml exec api alembic downgrade d3fa9090ded3
```

#### Local Migrations

```bash
# Set database URL for migrations
export CO_DB_URL=postgresql://scimigo:scimigo@localhost:5432/scimigo_co

# Create and apply migrations
poetry run alembic revision --autogenerate -m "Add new table"
poetry run alembic upgrade head
```

#### Database Management

```bash
# Access database directly
docker compose -f docker/docker-compose.dev.yml exec postgres psql -U scimigo -d scimigo_co

# View tables
docker compose -f docker/docker-compose.dev.yml exec postgres psql -U scimigo -d scimigo_co -c "\dt"

# Reset database (warning: destroys data)
docker compose -f docker/docker-compose.dev.yml down -v
docker compose -f docker/docker-compose.dev.yml up -d postgres redis
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

## Continuous Integration & Deployment

### GitHub Actions CI Pipeline

The project uses GitHub Actions for automated testing and deployment:

#### CI Workflow (`.github/workflows/ci.yml`)

Triggers on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs:**
1. **Lint**: Code formatting (Black) and linting (Ruff)
2. **Type Check**: Static type analysis with MyPy
3. **Test**: Full test suite with PostgreSQL and Redis services
4. **Build**: Docker image build verification

#### Running CI Locally

```bash
# Simulate CI pipeline locally
poetry install

# Run linting (matches CI)
poetry run black --check src/ tests/
poetry run ruff check src/ tests/

# Run type checking (matches CI)
poetry run mypy src/

# Run tests with coverage (matches CI)
export CO_DB_URL=postgresql+asyncpg://scimigo:scimigo@localhost:5432/scimigo_co_test
export CO_REDIS_URL=redis://localhost:6379/0
export CO_ENVIRONMENT=test

docker compose -f docker/docker-compose.dev.yml up -d postgres redis
docker compose -f docker/docker-compose.dev.yml exec postgres createdb -U scimigo scimigo_co_test
poetry run alembic upgrade head
poetry run pytest tests/ -v --cov=co --cov-report=term-missing

# Build Docker image (matches CI)
docker build -f docker/Dockerfile.api -t scimigo-co:latest .
```

#### CI Environment Variables

The CI pipeline uses these environment variables:
- `CO_DB_URL`: `postgresql+asyncpg://scimigo:scimigo@localhost:5432/scimigo_co_test`
- `CO_REDIS_URL`: `redis://localhost:6379/0`
- `CO_ENVIRONMENT`: `test`

### CD Pipeline

The continuous deployment pipeline (`.github/workflows/cd.yml`) handles:

1. **Staging**: Push to `main` branch → Deploy to staging
2. **Production**: Create git tag `v*` → Deploy to production

### AWS ECS Deployment

Required AWS resources:
- **ECS Cluster** with Fargate tasks
- **ECR Repository** for Docker images
- **RDS PostgreSQL** (Multi-AZ for production)
- **ElastiCache Redis** (Cluster mode for production)
- **ALB** with target groups and health checks
- **VPC** with public/private subnets
- **IAM roles** for ECS tasks and deployment

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
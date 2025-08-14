# Curriculum Orchestrator Development Commands
.PHONY: help install dev-up dev-down test test-docker lint format typecheck clean migrate

# Default target
help: ## Show this help message
	@echo "Curriculum Orchestrator Development Commands"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development
install: ## Install dependencies with Poetry
	poetry install

dev-up: ## Start development environment with Docker
	docker compose -f docker/docker-compose.dev.yml up -d
	@echo "Services started:"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  Database UI: http://localhost:8080"

dev-down: ## Stop development environment
	docker compose -f docker/docker-compose.dev.yml down

dev-logs: ## Show development logs
	docker compose -f docker/docker-compose.dev.yml logs -f

migrate: ## Run database migrations
	docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head

migrate-local: ## Run migrations locally (requires local setup)
	poetry run alembic upgrade head

##@ Testing
test: ## Run tests locally (requires services running)
	poetry run pytest

test-unit: ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	poetry run pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	poetry run pytest tests/e2e/ -v

test-docker: ## Run tests in Docker (isolated)
	docker compose -f docker/docker-compose.test.yml down --remove-orphans 2>/dev/null || true
	docker compose -f docker/docker-compose.test.yml up --build --remove-orphans test-runner --abort-on-container-exit
	docker compose -f docker/docker-compose.test.yml down

test-cov: ## Run tests with coverage report
	poetry run pytest --cov=co --cov-report=html --cov-report=term-missing

##@ Code Quality
lint: ## Run linting
	poetry run ruff check src/ tests/

lint-fix: ## Run linting with auto-fix
	poetry run ruff check src/ tests/ --fix

format: ## Format code
	poetry run black src/ tests/

format-check: ## Check code formatting
	poetry run black --check src/ tests/

typecheck: ## Run type checking
	poetry run mypy src/

quality: format-check lint typecheck ## Run all code quality checks

##@ Database
db-shell: ## Connect to database shell
	docker compose -f docker/docker-compose.dev.yml exec postgres psql -U scimigo -d scimigo_co

db-reset: ## Reset database (WARNING: destroys data)
	docker compose -f docker/docker-compose.dev.yml down -v
	docker compose -f docker/docker-compose.dev.yml up -d postgres redis
	sleep 5
	docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head

db-create-migration: ## Create new migration (usage: make db-create-migration MSG="description")
	docker compose -f docker/docker-compose.dev.yml exec api alembic revision --autogenerate -m "$(MSG)"

##@ CI/CD Simulation
ci-local: ## Simulate CI pipeline locally
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test-docker

##@ Cleanup
clean: ## Clean up containers and volumes
	docker compose -f docker/docker-compose.dev.yml down -v
	docker compose -f docker/docker-compose.test.yml down -v
	docker system prune -f

clean-all: ## Clean up everything including images
	docker compose -f docker/docker-compose.dev.yml down -v --rmi all
	docker compose -f docker/docker-compose.test.yml down -v --rmi all
	docker system prune -a -f

##@ Utilities
shell: ## Open shell in API container
	docker compose -f docker/docker-compose.dev.yml exec api bash

logs-api: ## Show API logs
	docker compose -f docker/docker-compose.dev.yml logs -f api

logs-db: ## Show database logs
	docker compose -f docker/docker-compose.dev.yml logs -f postgres

status: ## Show status of all services
	docker compose -f docker/docker-compose.dev.yml ps
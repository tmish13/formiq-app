.PHONY: install test test-unit test-integration test-e2e lint fmt clean db-init db-migrate run run-prod docker-build docker-run help

# Variables
PYTHON = python
PIP = pip
PYTEST = pytest
FLASK = flask
ENV_FILE = .env
PORT = 8000
HOST = 0.0.0.0
WORKERS = 4

help:
	@echo "FormIQ Backend - Make Commands"
	@echo "============================="
	@echo ""
	@echo "--- Testing (three gates) ---"
	@echo "test-unit        - Unit/API gate (no Docker required)"
	@echo "                   pytest -q -m 'not integration and not e2e and not slow'"
	@echo "test-integration - Integration gate (Docker REQUIRED)"
	@echo "                   Brings Docker stack up, runs 15 integration tests, tears down"
	@echo "test-e2e         - E2E gate (Docker REQUIRED)"
	@echo "                   Brings Docker stack up, runs golden-path E2E test, tears down"
	@echo ""
	@echo "--- Other ---"
	@echo "install      - Install dependencies"
	@echo "test         - Run all tests with -xvs (legacy shortcut)"
	@echo "lint         - Run linters (flake8, mypy)"
	@echo "fmt          - Format code (black, isort)"
	@echo "clean        - Clean up build artifacts"
	@echo "db-init      - Initialize the database"
	@echo "db-migrate   - Run database migrations"
	@echo "run          - Run the development server"
	@echo "run-prod     - Run the production server"
	@echo "docker-build - Build Docker image"
	@echo "docker-run   - Run Docker container"

# Install dependencies
install:
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

# Run tests (legacy shortcut — runs everything with verbose output)
test:
	$(PYTEST) -xvs

# -----------------------------------------------------------------------
# Three explicit test gates
# -----------------------------------------------------------------------
DOCKER_COMPOSE_TEST = docker compose -f tests/docker-compose.test.yml
PYTEST_INTEGRATION  = $(PYTEST) -q -m integration \
	tests/integration/form_checks/ tests/integration/videos/ \
	--asyncio-mode=auto
PYTEST_E2E          = $(PYTEST) -q -m e2e \
	tests/e2e/test_full_flow.py \
	--asyncio-mode=auto

# Gate 1 — Unit / API (no Docker needed)
test-unit:
	$(PYTEST) -q -m "not integration and not e2e and not slow"

# Gate 2 — Integration (real Postgres + Redis via docker-compose)
test-integration: _check-docker
	$(DOCKER_COMPOSE_TEST) up -d
	$(PYTEST_INTEGRATION); \
		EXIT=$$?; \
		$(DOCKER_COMPOSE_TEST) down -v; \
		exit $$EXIT

# Gate 3 — E2E golden path (real Postgres + Redis via docker-compose)
test-e2e: _check-docker
	$(DOCKER_COMPOSE_TEST) up -d
	$(PYTEST_E2E); \
		EXIT=$$?; \
		$(DOCKER_COMPOSE_TEST) down -v; \
		exit $$EXIT

# Internal: verify Docker daemon is reachable before any docker-dependent target
_check-docker:
	@docker ps > /dev/null 2>&1 || \
		{ echo ""; \
		  echo "ERROR: Docker daemon is not running."; \
		  echo "       Start Docker Desktop (or 'sudo systemctl start docker') then retry."; \
		  echo ""; \
		  exit 1; }

# Run linters
lint:
	flake8 app tests
	mypy app

# Format code
fmt:
	black app tests
	isort app tests

# Clean up artifacts
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

# Initialize database
db-init:
	$(PYTHON) -m app.db.init_db

# Run migrations
db-migrate:
	alembic upgrade head

# Run development server
run:
	./start_formiq.sh $(PORT) $(HOST) 1 development

# Run production server
run-prod:
	ENVIRONMENT=production ./start_formiq.sh $(PORT) $(HOST) $(WORKERS) production

# Docker commands
docker-build:
	docker build -t formiq-api .

docker-run:
	docker run -p $(PORT):8000 --env-file $(ENV_FILE) formiq-api 
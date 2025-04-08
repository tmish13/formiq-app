.PHONY: install test lint fmt clean db-init db-migrate run run-prod docker-build docker-run help

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
	@echo "install      - Install dependencies"
	@echo "test         - Run tests"
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

# Run tests
test:
	$(PYTEST) -xvs

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
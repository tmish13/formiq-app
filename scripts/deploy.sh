#!/bin/bash

# Exit on error
set -e

# Load environment variables
source .env

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Run tests
echo "Running tests..."
pytest tests/ -v

# Check code style
echo "Checking code style..."
flake8 app/ tests/
black --check app/ tests/

# Build Docker image
echo "Building Docker image..."
docker build -t formiq-backend .

# Push to registry (if configured)
if [ ! -z "$DOCKER_REGISTRY" ]; then
    echo "Pushing to Docker registry..."
    docker tag formiq-backend $DOCKER_REGISTRY/formiq-backend:$VERSION
    docker push $DOCKER_REGISTRY/formiq-backend:$VERSION
fi

# Deploy to production (if configured)
if [ ! -z "$DEPLOY_TARGET" ]; then
    echo "Deploying to $DEPLOY_TARGET..."
    # Add deployment commands here
    # Example: kubectl apply -f k8s/
fi

echo "Deployment completed successfully!" 
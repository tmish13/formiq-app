#!/bin/bash

# FormIQ Production Deployment Script
# This script handles deployment of the FormIQ application to various environments
# with proper error handling and rollback capabilities.

# Exit on error, but allow for controlled error handling
set -o pipefail

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ENVIRONMENT=${ENVIRONMENT:-"production"}
BACKUP_DIR="./backups"
LOG_FILE="./deploy_${TIMESTAMP}.log"
DEPLOY_FRONTEND=${DEPLOY_FRONTEND:-true}
DEPLOY_BACKEND=${DEPLOY_BACKEND:-true}
DEPLOY_DOCKER=${DEPLOY_DOCKER:-true}
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-false}
DEPLOY_TAG=${DEPLOY_TAG:-$TIMESTAMP}
ROLLBACK_ON_ERROR=${ROLLBACK_ON_ERROR:-true}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    local level=$1
    local message=$2
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] [$level] $message" | tee -a "$LOG_FILE"
}

# Error handling function
handle_error() {
    local exit_code=$1
    local step=$2
    
    if [ $exit_code -ne 0 ]; then
        log "ERROR" "Step '$step' failed with exit code $exit_code"
        
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log "INFO" "Initiating rollback..."
            rollback "$step"
        fi
        
        log "ERROR" "Deployment failed. Check $LOG_FILE for details"
        exit $exit_code
    fi
}

# Rollback function
rollback() {
    local failed_step=$1
    
    log "INFO" "Rolling back from step: $failed_step"
    
    case "$failed_step" in
        "backend_dependencies")
            log "INFO" "No rollback needed for dependencies"
            ;;
        "backend_migrations")
            log "INFO" "Rolling back database migrations..."
            cd backend
            python -m alembic downgrade -1
            cd ..
            ;;
        "frontend_build")
            log "INFO" "Restoring previous frontend build..."
            if [ -d "$BACKUP_DIR/frontend_build_previous" ]; then
                rm -rf frontend/build
                cp -r "$BACKUP_DIR/frontend_build_previous" frontend/build
            fi
            ;;
        "docker_build")
            log "INFO" "Using previous Docker images..."
            ;;
        "docker_deploy")
            log "INFO" "Rolling back to previous containers..."
            docker-compose -f docker-compose.prod.yml down
            docker-compose -f "$BACKUP_DIR/docker-compose.backup.yml" up -d
            ;;
        *)
            log "WARNING" "No specific rollback procedure for step: $failed_step"
            ;;
    esac
}

# Function to show progress
show_step() {
    echo ""
    log "INFO" "$1"
    echo "-----------------------------------"
}

# Check requirements
check_requirements() {
    show_step "Checking requirements"
    
    for cmd in node npm python3 pip docker docker-compose; do
        if ! command -v $cmd &> /dev/null; then
            log "ERROR" "$cmd is required but not installed"
            exit 1
        fi
    done
    
    log "INFO" "All requirements satisfied"
}

# Set up environment
setup_environment() {
    show_step "Setting up environment for $ENVIRONMENT"
    
    # Backup current .env files
    if [ -f backend/.env ]; then
        cp backend/.env "$BACKUP_DIR/backend_env_$TIMESTAMP.bak"
    fi
    
    if [ -f frontend/.env ]; then
        cp frontend/.env "$BACKUP_DIR/frontend_env_$TIMESTAMP.bak"
    fi
    
    # Copy environment-specific .env files
    if [ -f "backend/.env.$ENVIRONMENT" ]; then
        cp "backend/.env.$ENVIRONMENT" backend/.env
        log "INFO" "Using backend environment: .env.$ENVIRONMENT"
    else
        log "WARNING" "Backend environment file .env.$ENVIRONMENT not found, using default"
        cp backend/.env.example backend/.env
    fi
    
    if [ -f "frontend/.env.$ENVIRONMENT" ]; then
        cp "frontend/.env.$ENVIRONMENT" frontend/.env
        log "INFO" "Using frontend environment: .env.$ENVIRONMENT"
    else
        log "WARNING" "Frontend environment file .env.$ENVIRONMENT not found, using default"
        cp frontend/.env.example frontend/.env
    fi
    
    # Create logs directory if it doesn't exist
    mkdir -p backend/logs
    chmod 755 backend/logs
}

# Deploy backend
deploy_backend() {
    if [ "$DEPLOY_BACKEND" != true ]; then
        log "INFO" "Skipping backend deployment"
        return 0
    fi
    
    show_step "Deploying backend"
    cd backend
    
    # Install dependencies
    log "INFO" "Installing Python dependencies..."
    pip install -r requirements.txt
    handle_error $? "backend_dependencies"
    
    # Run database migrations if not skipped
    if [ "$SKIP_MIGRATIONS" != true ]; then
        log "INFO" "Running database migrations..."
        python -m alembic upgrade head
        handle_error $? "backend_migrations"
    else
        log "INFO" "Skipping database migrations"
    fi
    
    cd ..
    log "INFO" "Backend deployment completed"
}

# Deploy frontend
deploy_frontend() {
    if [ "$DEPLOY_FRONTEND" != true ]; then
        log "INFO" "Skipping frontend deployment"
        return 0
    fi
    
    show_step "Building frontend"
    cd frontend
    
    # Backup previous build
    if [ -d "build" ]; then
        log "INFO" "Backing up previous frontend build..."
        mkdir -p "$BACKUP_DIR/frontend_build_previous"
        cp -r build/* "$BACKUP_DIR/frontend_build_previous/"
    fi
    
    # Install dependencies
    log "INFO" "Installing npm dependencies..."
    npm ci
    handle_error $? "frontend_dependencies"
    
    # Build frontend
    log "INFO" "Building production frontend..."
    npm run build
    handle_error $? "frontend_build"
    
    cd ..
    log "INFO" "Frontend deployment completed"
}

# Deploy Docker
deploy_docker() {
    if [ "$DEPLOY_DOCKER" != true ]; then
        log "INFO" "Skipping Docker deployment"
        return 0
    fi
    
    show_step "Deploying with Docker"
    
    # Backup current docker-compose file
    if [ -f "docker-compose.prod.yml" ]; then
        cp docker-compose.prod.yml "$BACKUP_DIR/docker-compose.backup.yml"
    fi
    
    # Build Docker containers
    log "INFO" "Building Docker containers..."
    docker-compose -f docker-compose.prod.yml build --build-arg TAG="$DEPLOY_TAG"
    handle_error $? "docker_build"
    
    # Start Docker containers
    log "INFO" "Starting Docker containers..."
    docker-compose -f docker-compose.prod.yml up -d
    handle_error $? "docker_deploy"
    
    log "INFO" "Docker deployment completed"
}

# Verify deployment
verify_deployment() {
    show_step "Verifying deployment"
    log "INFO" "Waiting for services to start..."
    sleep 10
    
    # Check backend health
    log "INFO" "Checking backend health..."
    BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
    BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/health || echo "Failed")
    
    if [ "$BACKEND_HEALTH" = "200" ]; then
        log "INFO" "✅ Backend is healthy"
    else
        log "WARNING" "❌ Backend health check failed with status: $BACKEND_HEALTH"
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log "ERROR" "Backend health check failed, initiating rollback"
            rollback "deployment_verification"
            exit 1
        fi
    fi
    
    # Check frontend if deployed
    if [ "$DEPLOY_FRONTEND" = true ]; then
        log "INFO" "Checking frontend..."
        FRONTEND_URL="${FRONTEND_URL:-http://localhost}"
        FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $FRONTEND_URL || echo "Failed")
        
        if [ "$FRONTEND_HEALTH" = "200" ]; then
            log "INFO" "✅ Frontend is accessible"
        else
            log "WARNING" "❌ Frontend check failed with status: $FRONTEND_HEALTH"
        fi
    fi
}

# Main deployment flow
main() {
    echo "====================================="
    log "INFO" "FormIQ $ENVIRONMENT Deployment"
    echo "====================================="
    
    # Display configuration
    log "INFO" "Deployment Configuration:"
    log "INFO" "- Environment: $ENVIRONMENT"
    log "INFO" "- Deploy Tag: $DEPLOY_TAG"
    log "INFO" "- Deploy Frontend: $DEPLOY_FRONTEND"
    log "INFO" "- Deploy Backend: $DEPLOY_BACKEND"
    log "INFO" "- Deploy Docker: $DEPLOY_DOCKER"
    log "INFO" "- Skip Migrations: $SKIP_MIGRATIONS"
    log "INFO" "- Rollback on Error: $ROLLBACK_ON_ERROR"
    
    # Run deployment steps
    check_requirements
    setup_environment
    deploy_backend
    deploy_frontend
    deploy_docker
    verify_deployment
    
    echo ""
    echo "====================================="
    log "INFO" "Deployment completed successfully!"
    echo "====================================="
    if [ "$ENVIRONMENT" = "production" ]; then
        log "INFO" "Frontend: https://formiq-app.com"
        log "INFO" "Backend API: https://api.formiq-app.com"
    else
        log "INFO" "Frontend: http://localhost"
        log "INFO" "Backend API: http://localhost:8000"
    fi
    echo "====================================="
}

# Execute main function
main 
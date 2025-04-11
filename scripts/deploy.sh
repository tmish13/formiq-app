#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Deployment configuration
DEPLOY_DIR="deployments/$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="deploy.log"

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to log messages
log_message() {
    local message=$1
    local level=${2:-INFO}
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
    echo -e "$message"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a command and check its exit status
run_command() {
    local cmd=$1
    local error_msg=$2
    
    if ! eval "$cmd"; then
        log_message "Error: $error_msg" "ERROR"
        return 1
    fi
    return 0
}

# Function to create deployment directory
create_deploy_dir() {
    print_header "Creating Deployment Directory"
    mkdir -p "$DEPLOY_DIR"
    log_message "Deployment directory created: $DEPLOY_DIR"
}

# Function to deploy backend
deploy_backend() {
    print_header "Deploying Backend"
    
    # Build backend Docker image
    log_message "Building backend Docker image..."
    run_command "docker-compose -f docker-compose.prod.yml build backend" "Backend Docker build failed" || return 1
    
    # Run database migrations
    log_message "Running database migrations..."
    run_command "docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head" "Database migration failed" || return 1
    
    # Start backend services
    log_message "Starting backend services..."
    run_command "docker-compose -f docker-compose.prod.yml up -d backend" "Backend service startup failed" || return 1
    
    # Wait for backend to be healthy
    log_message "Waiting for backend to be healthy..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health | grep -q "healthy"; then
            log_message "Backend is healthy" "SUCCESS"
            return 0
        fi
        log_message "Waiting for backend to be healthy (attempt $attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Backend failed to become healthy after $max_attempts attempts" "ERROR"
    return 1
}

# Function to deploy frontend
deploy_frontend() {
    print_header "Deploying Frontend"
    
    # Build frontend
    log_message "Building frontend..."
    cd frontend || return 1
    run_command "npm ci" "Frontend dependency installation failed" || return 1
    run_command "npm run build" "Frontend build failed" || return 1
    cd ..
    
    # Build frontend Docker image
    log_message "Building frontend Docker image..."
    run_command "docker-compose -f docker-compose.prod.yml build frontend" "Frontend Docker build failed" || return 1
    
    # Start frontend services
    log_message "Starting frontend services..."
    run_command "docker-compose -f docker-compose.prod.yml up -d frontend" "Frontend service startup failed" || return 1
    
    # Wait for frontend to be healthy
    log_message "Waiting for frontend to be healthy..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:3000/health | grep -q "healthy"; then
            log_message "Frontend is healthy" "SUCCESS"
            return 0
        fi
        log_message "Waiting for frontend to be healthy (attempt $attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Frontend failed to become healthy after $max_attempts attempts" "ERROR"
    return 1
}

# Function to deploy nginx
deploy_nginx() {
    print_header "Deploying Nginx"
    
    # Build nginx Docker image
    log_message "Building nginx Docker image..."
    run_command "docker-compose -f docker-compose.prod.yml build nginx" "Nginx Docker build failed" || return 1
    
    # Start nginx services
    log_message "Starting nginx services..."
    run_command "docker-compose -f docker-compose.prod.yml up -d nginx" "Nginx service startup failed" || return 1
    
    # Wait for nginx to be healthy
    log_message "Waiting for nginx to be healthy..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -k https://localhost/health | grep -q "healthy"; then
            log_message "Nginx is healthy" "SUCCESS"
            return 0
        fi
        log_message "Waiting for nginx to be healthy (attempt $attempt/$max_attempts)..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_message "Nginx failed to become healthy after $max_attempts attempts" "ERROR"
    return 1
}

# Function to verify deployment
verify_deployment() {
    print_header "Verifying Deployment"
    
    # Check if all services are running
    log_message "Checking if all services are running..."
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_message "Not all services are running" "ERROR"
        return 1
    fi
    
    # Check API health
    log_message "Checking API health..."
    if ! curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_message "API health check failed" "ERROR"
        return 1
    fi
    
    # Check frontend health
    log_message "Checking frontend health..."
    if ! curl -s http://localhost:3000/health | grep -q "healthy"; then
        log_message "Frontend health check failed" "ERROR"
        return 1
    fi
    
    # Check nginx health
    log_message "Checking nginx health..."
    if ! curl -s -k https://localhost/health | grep -q "healthy"; then
        log_message "Nginx health check failed" "ERROR"
        return 1
    fi
    
    log_message "All services are healthy" "SUCCESS"
    return 0
}

# Function to rollback deployment
rollback_deployment() {
    print_header "Rolling Back Deployment"
    
    # Stop all services
    log_message "Stopping all services..."
    run_command "docker-compose -f docker-compose.prod.yml down" "Failed to stop services" || return 1
    
    # Restore from backup
    log_message "Restoring from backup..."
    if [ -d "$BACKUP_DIR" ]; then
        # Restore environment files
        log_message "Restoring environment files..."
        cp "$BACKUP_DIR/backend.env.production" backend/.env.production
        cp "$BACKUP_DIR/frontend.env.production" frontend/.env.production
        
        # Restore database
        log_message "Restoring database..."
        docker-compose -f docker-compose.prod.yml up -d db
        sleep 10  # Wait for database to start
        docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS formiq;"
        docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -c "CREATE DATABASE formiq;"
        docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres formiq < "$BACKUP_DIR/database.sql"
        
        # Restore SSL certificates
        log_message "Restoring SSL certificates..."
        cp -r "$BACKUP_DIR/ssl"/* infrastructure/docker/nginx/ssl/
        
        log_message "Rollback completed successfully" "SUCCESS"
        return 0
    else
        log_message "No backup found to restore from" "ERROR"
        return 1
    fi
}

# Function to handle deployment
deploy() {
    local environment=$1
    local component=$2
    
    case $component in
        "frontend")
            echo "Deploying frontend to $environment..."
            cd frontend
            if [ "$environment" = "production" ]; then
                npm run build
                # Add your production deployment commands here
            else
                npm run build:dev
                # Add your development deployment commands here
            fi
            ;;
        "backend")
            echo "Deploying backend to $environment..."
            cd backend
            if [ "$environment" = "production" ]; then
                # Add your production deployment commands here
                docker-compose -f deployment/docker-compose.prod.yml up -d
            else
                # Add your development deployment commands here
                docker-compose -f deployment/docker-compose.yml up -d
            fi
            ;;
        "all")
            deploy "$environment" "frontend"
            deploy "$environment" "backend"
            ;;
        *)
            echo "Unknown component: $component"
            echo "Available components: frontend, backend, all"
            exit 1
            ;;
    esac
}

# Check if environment is provided
if [ -z "$1" ]; then
    echo "Please provide an environment: development or production"
    exit 1
fi

# Check if component is provided
if [ -z "$2" ]; then
    echo "Please provide a component: frontend, backend, or all"
    exit 1
fi

deploy "$1" "$2"

# Main deployment process
main() {
    print_header "Starting Deployment"
    
    # Create deployment directory
    create_deploy_dir
    
    # Deploy backend
    if ! deploy_backend; then
        log_message "Backend deployment failed, rolling back..." "ERROR"
        rollback_deployment
        exit 1
    fi
    
    # Deploy frontend
    if ! deploy_frontend; then
        log_message "Frontend deployment failed, rolling back..." "ERROR"
        rollback_deployment
        exit 1
    fi
    
    # Deploy nginx
    if ! deploy_nginx; then
        log_message "Nginx deployment failed, rolling back..." "ERROR"
        rollback_deployment
        exit 1
    fi
    
    # Verify deployment
    if ! verify_deployment; then
        log_message "Deployment verification failed, rolling back..." "ERROR"
        rollback_deployment
        exit 1
    fi
    
    print_header "Deployment Complete"
    log_message "Deployment completed successfully!" "SUCCESS"
    log_message "Deployment directory: $DEPLOY_DIR" "INFO"
    log_message "Backup directory: $BACKUP_DIR" "INFO"
}

# Run main function
main 
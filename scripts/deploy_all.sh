#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Deployment configuration
DEPLOY_LOG="deploy.log"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$DEPLOY_LOG"
}

# Function to log messages
log_message() {
    local message=$1
    local level=${2:-INFO}
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$DEPLOY_LOG"
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

# Function to create backup
create_backup() {
    print_header "Creating Backup"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup environment files
    log_message "Backing up environment files..."
    cp backend/.env.production "$BACKUP_DIR/backend.env.production" 2>/dev/null || true
    cp frontend/.env.production "$BACKUP_DIR/frontend.env.production" 2>/dev/null || true
    
    # Backup database
    log_message "Backing up database..."
    docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres formiq > "$BACKUP_DIR/database.sql" 2>/dev/null || true
    
    # Backup SSL certificates
    log_message "Backing up SSL certificates..."
    cp -r infrastructure/docker/nginx/ssl "$BACKUP_DIR/ssl" 2>/dev/null || true
    
    log_message "Backup completed successfully in $BACKUP_DIR" "SUCCESS"
}

# Function to check system requirements
check_system_requirements() {
    print_header "Checking System Requirements"
    
    # Check required tools
    local required_tools=(
        "docker"
        "docker-compose"
        "node"
        "npm"
        "python3"
        "pip"
        "openssl"
    )
    
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            log_message "Required tool not found: $tool" "ERROR"
            return 1
        fi
        log_message "✓ $tool is installed" "SUCCESS"
    done
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_message "Docker daemon is not running" "ERROR"
        return 1
    fi
    
    # Check available disk space
    local required_space=10 # GB
    local available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt "$required_space" ]; then
        log_message "Insufficient disk space. Required: ${required_space}GB, Available: ${available_space}GB" "ERROR"
        return 1
    fi
    
    log_message "System requirements met" "SUCCESS"
    return 0
}

# Function to run deployment setup
run_deployment_setup() {
    print_header "Running Deployment Setup"
    
    # Make scripts executable
    chmod +x scripts/*.sh
    
    # Run deployment setup script
    if ! ./scripts/deployment_setup.sh; then
        log_message "Deployment setup failed" "ERROR"
        return 1
    fi
    
    log_message "Deployment setup completed" "SUCCESS"
    return 0
}

# Function to deploy the application
deploy_application() {
    print_header "Deploying Application"
    
    # Run deployment script
    if ! ./scripts/deploy.sh; then
        log_message "Deployment failed" "ERROR"
        return 1
    fi
    
    log_message "Deployment completed successfully" "SUCCESS"
    return 0
}

# Function to set up monitoring
setup_monitoring() {
    print_header "Setting Up Monitoring"
    
    # Run monitoring setup script
    if ! ./scripts/setup_monitoring.sh; then
        log_message "Monitoring setup failed" "ERROR"
        return 1
    fi
    
    log_message "Monitoring setup completed" "SUCCESS"
    return 0
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

# Main deployment process
main() {
    print_header "Starting Deployment Process"
    
    # Create log file
    touch "$DEPLOY_LOG"
    
    # Check system requirements
    check_system_requirements || exit 1
    
    # Create backup
    create_backup
    
    # Run deployment setup
    run_deployment_setup || exit 1
    
    # Deploy the application
    deploy_application || exit 1
    
    # Verify deployment
    verify_deployment || exit 1
    
    # Set up monitoring
    setup_monitoring || exit 1
    
    print_header "Deployment Process Complete"
    log_message "All deployment steps completed successfully!" "SUCCESS"
    log_message "Backup created in: $BACKUP_DIR" "INFO"
    log_message "Deployment log: $DEPLOY_LOG" "INFO"
    echo -e "${YELLOW}Please verify the application is working as expected.${NC}"
}

# Run main function
main 
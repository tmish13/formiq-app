#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Backup directory
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create backup
create_backup() {
    print_header "Creating Backup"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup environment files
    echo "Backing up environment files..."
    cp backend/.env.production "$BACKUP_DIR/backend.env.production"
    cp frontend/.env.production "$BACKUP_DIR/frontend.env.production"
    
    # Backup database
    echo "Backing up database..."
    docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres formiq > "$BACKUP_DIR/database.sql"
    
    # Backup SSL certificates
    echo "Backing up SSL certificates..."
    cp -r infrastructure/docker/nginx/ssl "$BACKUP_DIR/ssl"
    
    echo -e "${GREEN}Backup completed successfully in $BACKUP_DIR${NC}"
}

# Function to check environment files and variables
check_env_vars() {
    local env_file=$1
    
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}Environment file not found: $env_file${NC}"
        return 1
    fi
    
    local missing_vars=()
    
    while IFS= read -r line; do
        if [[ $line =~ ^[A-Z_]+=.*\$.* ]]; then
            var_name=$(echo "$line" | cut -d'=' -f1)
            if [ -z "${!var_name}" ]; then
                missing_vars+=("$var_name")
            fi
        fi
    done < "$env_file"
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}Missing environment variables in $env_file:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        return 1
    fi
    return 0
}

# Function to verify SSL certificates
verify_ssl() {
    local domain=$1
    local cert_file=$2
    
    if [ ! -f "$cert_file" ]; then
        echo -e "${RED}SSL certificate not found: $cert_file${NC}"
        return 1
    fi
    
    # Check certificate expiration (works on both Linux and macOS)
    local expiry_date
    local now_epoch
    local expiry_epoch
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d'=' -f2)
        expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s)
        now_epoch=$(date +%s)
    else
        expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d'=' -f2)
        expiry_epoch=$(date --date="$expiry_date" +%s)
        now_epoch=$(date +%s)
    fi
    
    local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))
    
    if [ $days_left -lt 30 ]; then
        echo -e "${RED}SSL certificate for $domain expires in $days_left days${NC}"
        return 1
    fi
    
    echo -e "${GREEN}SSL certificate for $domain is valid for $days_left days${NC}"
    return 0
}

# Function to verify Docker resources
verify_docker_resources() {
    print_header "Verifying Docker Resources"
    
    # Check Docker images
    echo "Checking Docker images..."
    if ! docker-compose -f docker-compose.prod.yml config --images | grep -q "formiq"; then
        echo -e "${YELLOW}Warning: Some Docker images may need to be rebuilt${NC}"
    fi
    
    # Check Docker volumes
    echo "Checking Docker volumes..."
    if ! docker volume ls | grep -q "formiq"; then
        echo -e "${YELLOW}Warning: Some Docker volumes may need to be created${NC}"
    fi
    
    # Check Docker network
    echo "Checking Docker network..."
    if ! docker network ls | grep -q "formiq-network"; then
        echo -e "${YELLOW}Warning: Docker network 'formiq-network' may need to be created${NC}"
    fi
}

# Function to run a command and check its exit status
run_command() {
    local cmd=$1
    local error_msg=$2
    
    if ! eval "$cmd"; then
        echo -e "${RED}Error: $error_msg${NC}"
        return 1
    fi
    return 0
}

# Function to verify system resources
verify_system_resources() {
    print_header "Verifying System Resources"
    
    # Check disk space (macOS compatible)
    local required_space=10 # GB
    local available_space
    if [[ "$OSTYPE" == "darwin"* ]]; then
        available_space=$(df -g / | awk 'NR==2 {print $4}')
    else
        available_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    fi
    
    if [ "$available_space" -lt "$required_space" ]; then
        echo -e "${RED}Insufficient disk space. Required: ${required_space}GB, Available: ${available_space}GB${NC}"
        return 1
    fi
    
    # Check memory (macOS compatible)
    local required_memory=4 # GB
    local available_memory
    if [[ "$OSTYPE" == "darwin"* ]]; then
        available_memory=$(sysctl -n hw.memsize | awk '{print $0/1024/1024/1024}' | cut -d. -f1)
    else
        available_memory=$(free -g | awk '/Mem:/ {print $2}')
    fi
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        echo -e "${RED}Insufficient memory. Required: ${required_memory}GB, Available: ${available_memory}GB${NC}"
        return 1
    fi
    
    echo -e "${GREEN}System resources are sufficient${NC}"
    return 0
}

# Main deployment setup process
main() {
    print_header "Starting Deployment Setup"
    
    # Check required tools
    print_header "Checking Required Tools"
    local required_tools=("docker" "docker-compose" "node" "npm" "openssl")
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            echo -e "${RED}Required tool not found: $tool${NC}"
            exit 1
        fi
        echo -e "${GREEN}✓ $tool is installed${NC}"
    done
    
    # Check Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Docker daemon is not running${NC}"
        exit 1
    fi
    
    # Verify system resources
    verify_system_resources || exit 1
    
    # Create backup
    create_backup
    
    # Check environment variables
    print_header "Checking Environment Variables"
    check_env_vars "backend/.env.production" || exit 1
    check_env_vars "frontend/.env.production" || exit 1
    
    # Verify SSL certificates
    print_header "Verifying SSL Certificates"
    verify_ssl "api.formiq-app.com" "infrastructure/docker/nginx/ssl/api.formiq-app.com.crt" || exit 1
    verify_ssl "formiq-app.com" "infrastructure/docker/nginx/ssl/formiq-app.com.crt" || exit 1
    
    # Verify Docker resources
    verify_docker_resources
    
    # Database setup
    print_header "Setting up Database"
    run_command "docker-compose -f docker-compose.prod.yml -f docker-compose.override.yml run --rm -e PYTHONPATH=/app backend python -m alembic.config -c /app/alembic.ini upgrade head" "Database migration failed" || exit 1
    
    # Frontend build
    print_header "Building Frontend"
    cd frontend || exit 1
    run_command "npm ci" "Frontend dependency installation failed" || exit 1
    run_command "npm run build" "Frontend build failed" || exit 1
    cd ..
    
    # Backend tests
    print_header "Running Backend Tests"
    run_command "docker-compose -f docker-compose.prod.yml -f docker-compose.override.yml run --rm backend pytest" "Backend tests failed" || exit 1
    
    # Frontend tests
    print_header "Running Frontend Tests"
    cd frontend || exit 1
    run_command "npm run test -- --watchAll=false" "Frontend unit tests failed" || exit 1
    run_command "npm run test:e2e -- --headless" "Frontend E2E tests failed" || exit 1
    cd ..
    
    print_header "Deployment Setup Complete"
    echo -e "${GREEN}All pre-deployment checks passed successfully!${NC}"
    echo -e "${GREEN}Backup created in: $BACKUP_DIR${NC}"
}

# Run main function
main 
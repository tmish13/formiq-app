#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to check system requirements
check_system_requirements() {
    print_header "Checking System Requirements"
    
    local errors=0
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        ((errors++))
    else
        echo -e "${GREEN}✓ Docker is installed${NC}"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        ((errors++))
    else
        echo -e "${GREEN}✓ Docker Compose is installed${NC}"
    fi
    
    # Check disk space (minimum 10GB required)
    local required_space=10
    local available_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt "$required_space" ]; then
        echo -e "${RED}Error: Insufficient disk space. Required: ${required_space}GB, Available: ${available_space}GB${NC}"
        ((errors++))
    else
        echo -e "${GREEN}✓ Sufficient disk space available${NC}"
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        ((errors++))
    else
        echo -e "${GREEN}✓ Docker daemon is running${NC}"
    fi
    
    return $errors
}

# Function to create backup directory
create_backup_dir() {
    print_header "Creating Backup Directory"
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    
    if mkdir -p "$backup_dir"; then
        echo -e "${GREEN}✓ Backup directory created: $backup_dir${NC}"
        echo "$backup_dir"
        return 0
    else
        echo -e "${RED}Error: Failed to create backup directory${NC}"
        return 1
    fi
}

# Function to backup configuration files
backup_config_files() {
    print_header "Backing Up Configuration Files"
    
    local backup_dir=$1
    local errors=0
    
    # Backup environment files
    if [ -f ".env" ]; then
        cp ".env" "$backup_dir/.env.backup" || ((errors++))
    fi
    
    if [ -f ".env.production" ]; then
        cp ".env.production" "$backup_dir/.env.production.backup" || ((errors++))
    fi
    
    # Backup SSL certificates
    if [ -d "infrastructure/docker/nginx/ssl" ]; then
        cp -r "infrastructure/docker/nginx/ssl" "$backup_dir/ssl" || ((errors++))
    fi
    
    # Backup nginx configurations
    if [ -d "infrastructure/docker/nginx" ]; then
        cp -r "infrastructure/docker/nginx" "$backup_dir/nginx" || ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ Configuration files backed up successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to backup some configuration files${NC}"
        return 1
    fi
}

# Function to verify environment files
verify_env_files() {
    print_header "Verifying Environment Files"
    
    local errors=0
    
    # Check for required environment files
    if [ ! -f ".env.production" ]; then
        echo -e "${RED}Error: .env.production file is missing${NC}"
        ((errors++))
    fi
    
    if [ ! -f ".env.production.template" ]; then
        echo -e "${RED}Error: .env.production.template file is missing${NC}"
        ((errors++))
    fi
    
    # Verify required environment variables
    if [ -f ".env.production" ]; then
        local required_vars=(
            "NODE_ENV"
            "API_URL"
            "DATABASE_URL"
            "REDIS_URL"
            "JWT_SECRET"
            "SSL_CERT_PATH"
            "SSL_KEY_PATH"
        )
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" ".env.production"; then
                echo -e "${RED}Error: $var is not set in .env.production${NC}"
                ((errors++))
            fi
        done
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ Environment files verified successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Environment file verification failed${NC}"
        return 1
    fi
}

# Function to verify SSL certificates
verify_ssl_certificates() {
    print_header "Verifying SSL Certificates"
    
    local errors=0
    
    # Check for SSL certificate files
    if [ ! -f "infrastructure/docker/nginx/ssl/cert.pem" ]; then
        echo -e "${RED}Error: SSL certificate file is missing${NC}"
        ((errors++))
    fi
    
    if [ ! -f "infrastructure/docker/nginx/ssl/key.pem" ]; then
        echo -e "${RED}Error: SSL key file is missing${NC}"
        ((errors++))
    fi
    
    # Verify certificate validity
    if [ -f "infrastructure/docker/nginx/ssl/cert.pem" ]; then
        if ! openssl x509 -in "infrastructure/docker/nginx/ssl/cert.pem" -noout -checkend 0; then
            echo -e "${RED}Error: SSL certificate has expired${NC}"
            ((errors++))
        fi
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ SSL certificates verified successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: SSL certificate verification failed${NC}"
        return 1
    fi
}

# Function to verify nginx configuration
verify_nginx_config() {
    print_header "Verifying Nginx Configuration"
    
    local errors=0
    
    # Check for required nginx configuration files
    if [ ! -f "infrastructure/docker/nginx/nginx.conf" ]; then
        echo -e "${RED}Error: nginx.conf file is missing${NC}"
        ((errors++))
    fi
    
    if [ ! -f "infrastructure/docker/nginx/conf.d/default.conf" ]; then
        echo -e "${RED}Error: default.conf file is missing${NC}"
        ((errors++))
    fi
    
    # Verify nginx configuration syntax
    if [ -f "infrastructure/docker/nginx/nginx.conf" ]; then
        if ! docker run --rm -v "$(pwd)/infrastructure/docker/nginx:/etc/nginx" nginx nginx -t; then
            echo -e "${RED}Error: Invalid nginx configuration syntax${NC}"
            ((errors++))
        fi
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx configuration verified successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Nginx configuration verification failed${NC}"
        return 1
    fi
}

# Main function
main() {
    print_header "Starting Deployment Configuration"
    
    local errors=0
    
    # Run configuration steps
    check_system_requirements || ((errors++))
    
    local backup_dir
    if backup_dir=$(create_backup_dir); then
        backup_config_files "$backup_dir" || ((errors++))
    else
        ((errors++))
    fi
    
    verify_env_files || ((errors++))
    verify_ssl_certificates || ((errors++))
    verify_nginx_config || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Deployment Configuration Complete"
        echo -e "${GREEN}All deployment configuration steps completed successfully!${NC}"
        return 0
    else
        print_header "Deployment Configuration Failed"
        echo -e "${RED}Found $errors issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
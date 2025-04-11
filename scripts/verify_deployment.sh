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

# Function to check if a command exists
check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $cmd is installed${NC}"
    return 0
}

# Function to check file existence
check_file() {
    local file=$1
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: $file does not exist${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $file exists${NC}"
    return 0
}

# Function to check directory existence
check_directory() {
    local dir=$1
    if [ ! -d "$dir" ]; then
        echo -e "${RED}Error: $dir does not exist${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $dir exists${NC}"
    return 0
}

# Function to verify environment files
verify_env_files() {
    print_header "Verifying Environment Files"
    
    local env_files=(
        "backend/.env.production"
        "frontend/.env.production"
        "backend/.env.production.template"
        "frontend/.env.production.template"
    )
    
    local missing_files=0
    for file in "${env_files[@]}"; do
        if ! check_file "$file"; then
            ((missing_files++))
        fi
    done
    
    if [ $missing_files -gt 0 ]; then
        echo -e "${RED}Error: $missing_files environment files are missing${NC}"
        return 1
    fi
    return 0
}

# Function to verify SSL certificates
verify_ssl_certs() {
    print_header "Verifying SSL Certificates"
    
    local cert_files=(
        "infrastructure/docker/nginx/ssl/formiq-app.com.crt"
        "infrastructure/docker/nginx/ssl/formiq-app.com.key"
        "infrastructure/docker/nginx/ssl/api.formiq-app.com.crt"
        "infrastructure/docker/nginx/ssl/api.formiq-app.com.key"
    )
    
    local missing_certs=0
    for cert in "${cert_files[@]}"; do
        if ! check_file "$cert"; then
            ((missing_certs++))
        fi
    done
    
    if [ $missing_certs -gt 0 ]; then
        echo -e "${RED}Error: $missing_certs SSL certificates are missing${NC}"
        return 1
    fi
    return 0
}

# Function to verify Docker configurations
verify_docker_configs() {
    print_header "Verifying Docker Configurations"
    
    local docker_files=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "infrastructure/docker/nginx/nginx.conf"
        "infrastructure/docker/nginx/conf.d/default.conf"
    )
    
    local missing_configs=0
    for config in "${docker_files[@]}"; do
        if ! check_file "$config"; then
            ((missing_configs++))
        fi
    done
    
    if [ $missing_configs -gt 0 ]; then
        echo -e "${RED}Error: $missing_configs Docker configuration files are missing${NC}"
        return 1
    fi
    return 0
}

# Function to verify required directories
verify_directories() {
    print_header "Verifying Required Directories"
    
    local directories=(
        "backend/app"
        "backend/logs"
        "backend/tests"
        "frontend/src"
        "frontend/build"
        "infrastructure/docker/nginx/ssl"
        "infrastructure/docker/nginx/conf.d"
    )
    
    local missing_dirs=0
    for dir in "${directories[@]}"; do
        if ! check_directory "$dir"; then
            ((missing_dirs++))
        fi
    done
    
    if [ $missing_dirs -gt 0 ]; then
        echo -e "${RED}Error: $missing_dirs required directories are missing${NC}"
        return 1
    fi
    return 0
}

# Function to verify system requirements
verify_system_requirements() {
    print_header "Verifying System Requirements"
    
    local commands=(
        "docker"
        "docker-compose"
        "node"
        "npm"
        "python3"
        "pip"
        "openssl"
    )
    
    local missing_commands=0
    for cmd in "${commands[@]}"; do
        if ! check_command "$cmd"; then
            ((missing_commands++))
        fi
    done
    
    if [ $missing_commands -gt 0 ]; then
        echo -e "${RED}Error: $missing_commands required commands are missing${NC}"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Docker daemon is running${NC}"
    
    # Check disk space
    local free_space=$(df -h . | awk 'NR==2 {print $4}')
    echo -e "${GREEN}✓ Free disk space: $free_space${NC}"
    
    return 0
}

# Function to check service health
check_service_health() {
    print_header "Checking Service Health"
    
    local services=("frontend" "backend" "database" "nginx")
    local errors=0
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            echo -e "${GREEN}✓ $service is running${NC}"
        else
            echo -e "${RED}Error: $service is not running${NC}"
            ((errors++))
        fi
    done
    
    return $errors
}

# Function to verify API endpoints
verify_api_endpoints() {
    print_header "Verifying API Endpoints"
    
    local base_url="https://formiq-app.com/api"
    local endpoints=(
        "/health"
        "/auth/login"
        "/users/me"
        "/forms"
        "/submissions"
    )
    
    local errors=0
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint" | grep -q "200\|401"; then
            echo -e "${GREEN}✓ $endpoint is accessible${NC}"
        else
            echo -e "${RED}Error: $endpoint is not accessible${NC}"
            ((errors++))
        fi
    done
    
    return $errors
}

# Function to check frontend functionality
check_frontend() {
    print_header "Checking Frontend Functionality"
    
    local base_url="https://formiq-app.com"
    local errors=0
    
    # Check main page
    if curl -s -o /dev/null -w "%{http_code}" "$base_url" | grep -q "200"; then
        echo -e "${GREEN}✓ Main page is accessible${NC}"
    else
        echo -e "${RED}Error: Main page is not accessible${NC}"
        ((errors++))
    fi
    
    # Check static assets
    local assets=(
        "/static/js/main.js"
        "/static/css/main.css"
        "/static/media/logo.png"
    )
    
    for asset in "${assets[@]}"; do
        if curl -s -o /dev/null -w "%{http_code}" "$base_url$asset" | grep -q "200"; then
            echo -e "${GREEN}✓ $asset is accessible${NC}"
        else
            echo -e "${RED}Error: $asset is not accessible${NC}"
            ((errors++))
        fi
    done
    
    return $errors
}

# Function to verify SSL configuration
verify_ssl() {
    print_header "Verifying SSL Configuration"
    
    local domain="formiq-app.com"
    local errors=0
    
    # Check SSL certificate
    if openssl s_client -connect "$domain:443" -servername "$domain" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        echo -e "${GREEN}✓ SSL certificate is valid${NC}"
    else
        echo -e "${RED}Error: SSL certificate is invalid${NC}"
        ((errors++))
    fi
    
    # Check SSL protocols
    if nmap --script ssl-enum-ciphers -p 443 "$domain" 2>/dev/null | grep -q "TLSv1.2\|TLSv1.3"; then
        echo -e "${GREEN}✓ Modern SSL protocols are supported${NC}"
    else
        echo -e "${RED}Error: Modern SSL protocols are not supported${NC}"
        ((errors++))
    fi
    
    return $errors
}

# Function to check database connectivity
check_database() {
    print_header "Checking Database Connectivity"
    
    local errors=0
    
    # Check database connection
    if docker-compose exec -T database pg_isready -U postgres; then
        echo -e "${GREEN}✓ Database is accessible${NC}"
    else
        echo -e "${RED}Error: Database is not accessible${NC}"
        ((errors++))
    fi
    
    # Check database tables
    local tables=("users" "forms" "submissions" "settings")
    
    for table in "${tables[@]}"; do
        if docker-compose exec -T database psql -U postgres -d formiq -c "\dt $table" 2>/dev/null | grep -q "$table"; then
            echo -e "${GREEN}✓ Table $table exists${NC}"
        else
            echo -e "${RED}Error: Table $table does not exist${NC}"
            ((errors++))
        fi
    done
    
    return $errors
}

# Function to verify backup systems
verify_backups() {
    print_header "Verifying Backup Systems"
    
    local errors=0
    
    # Check backup directory
    if [ -d "backups" ]; then
        echo -e "${GREEN}✓ Backup directory exists${NC}"
    else
        echo -e "${RED}Error: Backup directory does not exist${NC}"
        ((errors++))
    fi
    
    # Check recent backups
    local backup_types=("database" "env" "ssl" "app")
    
    for type in "${backup_types[@]}"; do
        if find "backups" -type f -name "*.$type*" -mtime -1 | grep -q .; then
            echo -e "${GREEN}✓ Recent $type backup exists${NC}"
        else
            echo -e "${RED}Error: No recent $type backup found${NC}"
            ((errors++))
        fi
    done
    
    return $errors
}

# Function to check monitoring systems
check_monitoring() {
    print_header "Checking Monitoring Systems"
    
    local errors=0
    
    # Check Prometheus
    if curl -s "http://localhost:9090/-/healthy" | grep -q "Prometheus"; then
        echo -e "${GREEN}✓ Prometheus is running${NC}"
    else
        echo -e "${RED}Error: Prometheus is not running${NC}"
        ((errors++))
    fi
    
    # Check Grafana
    if curl -s "http://localhost:3000/api/health" | grep -q "ok"; then
        echo -e "${GREEN}✓ Grafana is running${NC}"
    else
        echo -e "${RED}Error: Grafana is not running${NC}"
        ((errors++))
    fi
    
    # Check log aggregation
    if docker-compose logs --tail=100 | grep -q "ERROR\|CRITICAL"; then
        echo -e "${YELLOW}Warning: Found errors in recent logs${NC}"
    else
        echo -e "${GREEN}✓ No recent errors in logs${NC}"
    fi
    
    return $errors
}

# Main function
main() {
    print_header "Starting Deployment Verification"
    
    local errors=0
    
    # Run verification steps
    verify_system_requirements || ((errors++))
    verify_env_files || ((errors++))
    verify_ssl_certs || ((errors++))
    verify_docker_configs || ((errors++))
    verify_directories || ((errors++))
    check_service_health || ((errors++))
    verify_api_endpoints || ((errors++))
    check_frontend || ((errors++))
    verify_ssl || ((errors++))
    check_database || ((errors++))
    verify_backups || ((errors++))
    check_monitoring || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Verification Complete"
        echo -e "${GREEN}All systems verified successfully${NC}"
        return 0
    else
        print_header "Verification Failed"
        echo -e "${RED}Found $errors issues during verification${NC}"
        echo -e "${YELLOW}Manual intervention may be required${NC}"
        return 1
    fi
}

# Run main function
main 
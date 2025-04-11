#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
VERIFY_LOG="verify.log"
HEALTH_CHECK_TIMEOUT=30
MAX_RETRIES=3
RETRY_INTERVAL=5

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$VERIFY_LOG"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to verify system requirements
verify_system() {
    print_header "Verifying System Requirements"
    
    local requirements=(
        "docker:Docker"
        "docker-compose:Docker Compose"
        "node:Node.js"
        "npm:npm"
        "python3:Python 3"
        "pip:pip"
        "nginx:Nginx"
        "openssl:OpenSSL"
    )
    
    local missing_requirements=0
    
    for req in "${requirements[@]}"; do
        IFS=':' read -r cmd name <<< "$req"
        if ! command_exists "$cmd"; then
            log_message "ERROR" "$name is not installed"
            ((missing_requirements++))
        else
            log_message "INFO" "$name is installed"
        fi
    done
    
    if [ $missing_requirements -gt 0 ]; then
        log_message "ERROR" "Missing system requirements"
        return 1
    fi
    
    return 0
}

# Function to verify Docker services
verify_docker_services() {
    print_header "Verifying Docker Services"
    
    local services=(
        "frontend:3000"
        "backend:8000"
        "database:5432"
        "nginx:80"
    )
    
    local failed_services=0
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if ! docker-compose ps | grep -q "$name.*Up"; then
            log_message "ERROR" "Service $name is not running"
            ((failed_services++))
        else
            if ! nc -z localhost "$port"; then
                log_message "ERROR" "Service $name is not listening on port $port"
                ((failed_services++))
            else
                log_message "INFO" "Service $name is running and listening on port $port"
            fi
        fi
    done
    
    if [ $failed_services -gt 0 ]; then
        log_message "ERROR" "Some Docker services are not running correctly"
        return 1
    fi
    
    return 0
}

# Function to verify database
verify_database() {
    print_header "Verifying Database"
    
    local retries=0
    local success=0
    
    while [ $retries -lt $MAX_RETRIES ] && [ $success -eq 0 ]; do
        if pg_isready -h localhost -p 5432; then
            log_message "INFO" "Database is accepting connections"
            success=1
        else
            log_message "WARNING" "Database is not ready, retrying in $RETRY_INTERVAL seconds"
            sleep $RETRY_INTERVAL
            ((retries++))
        fi
    done
    
    if [ $success -eq 0 ]; then
        log_message "ERROR" "Database verification failed after $MAX_RETRIES attempts"
        return 1
    fi
    
    # Verify database schema
    if ! psql -h localhost -U postgres -d formiq -c "\dt" > /dev/null 2>&1; then
        log_message "ERROR" "Failed to verify database schema"
        return 1
    fi
    
    log_message "INFO" "Database schema verified successfully"
    return 0
}

# Function to verify API endpoints
verify_api_endpoints() {
    print_header "Verifying API Endpoints"
    
    local endpoints=(
        "/api/health:GET:200"
        "/api/auth/login:POST:401"
        "/api/users/me:GET:401"
        "/api/forms:GET:401"
        "/api/submissions:GET:401"
    )
    
    local failed_endpoints=0
    
    for endpoint in "${endpoints[@]}"; do
        IFS=':' read -r path method expected_status <<< "$endpoint"
        local response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://localhost:8000$path")
        
        if [ "$response" != "$expected_status" ]; then
            log_message "ERROR" "Endpoint $path returned $response, expected $expected_status"
            ((failed_endpoints++))
        else
            log_message "INFO" "Endpoint $path verified successfully"
        fi
    done
    
    if [ $failed_endpoints -gt 0 ]; then
        log_message "ERROR" "Some API endpoints are not responding correctly"
        return 1
    fi
    
    return 0
}

# Function to verify frontend
verify_frontend() {
    print_header "Verifying Frontend"
    
    local retries=0
    local success=0
    
    while [ $retries -lt $MAX_RETRIES ] && [ $success -eq 0 ]; do
        if curl -s -f "http://localhost:3000" > /dev/null; then
            log_message "INFO" "Frontend is accessible"
            success=1
        else
            log_message "WARNING" "Frontend is not accessible, retrying in $RETRY_INTERVAL seconds"
            sleep $RETRY_INTERVAL
            ((retries++))
        fi
    done
    
    if [ $success -eq 0 ]; then
        log_message "ERROR" "Frontend verification failed after $MAX_RETRIES attempts"
        return 1
    fi
    
    # Verify frontend build
    if [ ! -d "frontend/build" ]; then
        log_message "ERROR" "Frontend build directory not found"
        return 1
    fi
    
    log_message "INFO" "Frontend build verified successfully"
    return 0
}

# Function to verify SSL certificates
verify_ssl() {
    print_header "Verifying SSL Certificates"
    
    local cert_path="/etc/nginx/ssl"
    local domains=("formiq-app.com" "www.formiq-app.com")
    
    for domain in "${domains[@]}"; do
        if [ ! -f "$cert_path/$domain.crt" ] || [ ! -f "$cert_path/$domain.key" ]; then
            log_message "ERROR" "SSL certificates for $domain not found"
            return 1
        fi
        
        # Verify certificate expiration
        local expiry_date=$(openssl x509 -enddate -noout -in "$cert_path/$domain.crt" | cut -d= -f2)
        local expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" "+%s")
        local current_epoch=$(date "+%s")
        local days_remaining=$(( ($expiry_epoch - $current_epoch) / 86400 ))
        
        if [ $days_remaining -lt 30 ]; then
            log_message "WARNING" "SSL certificate for $domain expires in $days_remaining days"
        else
            log_message "INFO" "SSL certificate for $domain is valid for $days_remaining days"
        fi
    done
    
    return 0
}

# Function to verify environment variables
verify_env_vars() {
    print_header "Verifying Environment Variables"
    
    local required_vars=(
        "DATABASE_URL"
        "SECRET_KEY"
        "ALLOWED_HOSTS"
        "CORS_ORIGIN_WHITELIST"
        "EMAIL_HOST"
        "EMAIL_PORT"
        "EMAIL_HOST_USER"
        "EMAIL_HOST_PASSWORD"
    )
    
    local missing_vars=0
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_message "ERROR" "Required environment variable $var is not set"
            ((missing_vars++))
        else
            log_message "INFO" "Environment variable $var is set"
        fi
    done
    
    if [ $missing_vars -gt 0 ]; then
        log_message "ERROR" "Missing required environment variables"
        return 1
    fi
    
    return 0
}

# Function to verify backups
verify_backups() {
    print_header "Verifying Backups"
    
    local backup_types=("database" "frontend" "backend" "env")
    local missing_backups=0
    
    for type in "${backup_types[@]}"; do
        local latest_backup=$(find "backups" -type f -name "*.$type.*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [ -z "$latest_backup" ]; then
            log_message "ERROR" "No backup found for $type"
            ((missing_backups++))
        else
            local backup_age=$(( $(date +%s) - $(stat -f %m "$latest_backup") ))
            local backup_days=$(( backup_age / 86400 ))
            
            if [ $backup_days -gt 1 ]; then
                log_message "WARNING" "Backup for $type is $backup_days days old"
            else
                log_message "INFO" "Backup for $type is recent ($backup_days days old)"
            fi
        fi
    done
    
    if [ $missing_backups -gt 0 ]; then
        log_message "ERROR" "Missing required backups"
        return 1
    fi
    
    return 0
}

# Main verification function
main() {
    print_header "Starting Deployment Verification"
    log_message "INFO" "Verification process initiated"
    
    # Create log file
    touch "$VERIFY_LOG"
    
    # Run verification checks
    local checks=(
        "verify_system:System Requirements"
        "verify_docker_services:Docker Services"
        "verify_database:Database"
        "verify_api_endpoints:API Endpoints"
        "verify_frontend:Frontend"
        "verify_ssl:SSL Certificates"
        "verify_env_vars:Environment Variables"
        "verify_backups:Backups"
    )
    
    local failed_checks=0
    
    for check in "${checks[@]}"; do
        IFS=':' read -r func name <<< "$check"
        print_header "Verifying $name"
        if ! $func; then
            log_message "ERROR" "$name verification failed"
            ((failed_checks++))
        else
            log_message "INFO" "$name verification passed"
        fi
    done
    
    if [ $failed_checks -gt 0 ]; then
        log_message "ERROR" "Deployment verification failed with $failed_checks failed checks"
        echo -e "${RED}Deployment verification failed${NC}"
        exit 1
    fi
    
    log_message "INFO" "Deployment verification completed successfully"
    echo -e "${GREEN}Deployment verification completed successfully${NC}"
}

# Run main function
main 
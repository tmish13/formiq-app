#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKUP_DIR="backups"
ROLLBACK_LOG="rollback.log"
MAX_BACKUPS=5

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$ROLLBACK_LOG"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to verify backup existence
verify_backup() {
    local backup_file=$1
    if [ ! -f "$backup_file" ]; then
        log_message "ERROR" "Backup file $backup_file not found"
        return 1
    fi
    return 0
}

# Function to stop services
stop_services() {
    print_header "Stopping Services"
    
    log_message "INFO" "Stopping Docker services"
    if command_exists docker-compose; then
        docker-compose down
        if [ $? -eq 0 ]; then
            log_message "INFO" "Docker services stopped successfully"
        else
            log_message "ERROR" "Failed to stop Docker services"
            return 1
        fi
    else
        log_message "ERROR" "docker-compose not found"
        return 1
    fi
}

# Function to restore database
restore_database() {
    print_header "Restoring Database"
    
    local latest_backup=$(find "$BACKUP_DIR" -type f -name "*.database.*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -z "$latest_backup" ]; then
        log_message "ERROR" "No database backup found"
        return 1
    fi
    
    verify_backup "$latest_backup" || return 1
    
    log_message "INFO" "Restoring database from $latest_backup"
    if command_exists pg_restore; then
        pg_restore -h localhost -U postgres -d formiq "$latest_backup"
        if [ $? -eq 0 ]; then
            log_message "INFO" "Database restored successfully"
        else
            log_message "ERROR" "Failed to restore database"
            return 1
        fi
    else
        log_message "ERROR" "pg_restore not found"
        return 1
    fi
}

# Function to restore frontend
restore_frontend() {
    print_header "Restoring Frontend"
    
    local latest_backup=$(find "$BACKUP_DIR" -type f -name "*.frontend.*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -z "$latest_backup" ]; then
        log_message "ERROR" "No frontend backup found"
        return 1
    fi
    
    verify_backup "$latest_backup" || return 1
    
    log_message "INFO" "Restoring frontend from $latest_backup"
    if command_exists npm; then
        cd frontend
        rm -rf build
        tar xzf "$latest_backup"
        if [ $? -eq 0 ]; then
            log_message "INFO" "Frontend restored successfully"
        else
            log_message "ERROR" "Failed to restore frontend"
            return 1
        fi
        cd ..
    else
        log_message "ERROR" "npm not found"
        return 1
    fi
}

# Function to restore backend
restore_backend() {
    print_header "Restoring Backend"
    
    local latest_backup=$(find "$BACKUP_DIR" -type f -name "*.backend.*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -z "$latest_backup" ]; then
        log_message "ERROR" "No backend backup found"
        return 1
    fi
    
    verify_backup "$latest_backup" || return 1
    
    log_message "INFO" "Restoring backend from $latest_backup"
    if command_exists python3; then
        cd backend
        rm -rf venv
        tar xzf "$latest_backup"
        if [ $? -eq 0 ]; then
            log_message "INFO" "Backend restored successfully"
        else
            log_message "ERROR" "Failed to restore backend"
            return 1
        fi
        cd ..
    else
        log_message "ERROR" "python3 not found"
        return 1
    fi
}

# Function to restore environment files
restore_env_files() {
    print_header "Restoring Environment Files"
    
    local latest_backup=$(find "$BACKUP_DIR" -type f -name "*.env.*" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -z "$latest_backup" ]; then
        log_message "ERROR" "No environment files backup found"
        return 1
    fi
    
    verify_backup "$latest_backup" || return 1
    
    log_message "INFO" "Restoring environment files from $latest_backup"
    tar xzf "$latest_backup" -C .
    if [ $? -eq 0 ]; then
        log_message "INFO" "Environment files restored successfully"
    else
        log_message "ERROR" "Failed to restore environment files"
        return 1
    fi
}

# Function to start services
start_services() {
    print_header "Starting Services"
    
    log_message "INFO" "Starting Docker services"
    if command_exists docker-compose; then
        docker-compose up -d
        if [ $? -eq 0 ]; then
            log_message "INFO" "Docker services started successfully"
        else
            log_message "ERROR" "Failed to start Docker services"
            return 1
        fi
    else
        log_message "ERROR" "docker-compose not found"
        return 1
    fi
}

# Function to verify rollback
verify_rollback() {
    print_header "Verifying Rollback"
    
    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        log_message "ERROR" "Some services are not running"
        return 1
    fi
    
    # Check database connectivity
    if ! pg_isready -h localhost -p 5432; then
        log_message "ERROR" "Database is not accepting connections"
        return 1
    fi
    
    # Check API health
    if ! curl -s -f "http://localhost:8000/api/health" > /dev/null; then
        log_message "ERROR" "API health check failed"
        return 1
    fi
    
    # Check frontend
    if ! curl -s -f "http://localhost:3000" > /dev/null; then
        log_message "ERROR" "Frontend health check failed"
        return 1
    fi
    
    log_message "INFO" "Rollback verification successful"
    return 0
}

# Main rollback function
main() {
    print_header "Starting Deployment Rollback"
    log_message "INFO" "Rollback process initiated"
    
    # Create log file
    touch "$ROLLBACK_LOG"
    
    # Stop services
    stop_services || { log_message "ERROR" "Failed to stop services"; exit 1; }
    
    # Restore components
    restore_database || { log_message "ERROR" "Failed to restore database"; exit 1; }
    restore_frontend || { log_message "ERROR" "Failed to restore frontend"; exit 1; }
    restore_backend || { log_message "ERROR" "Failed to restore backend"; exit 1; }
    restore_env_files || { log_message "ERROR" "Failed to restore environment files"; exit 1; }
    
    # Start services
    start_services || { log_message "ERROR" "Failed to start services"; exit 1; }
    
    # Verify rollback
    verify_rollback || { log_message "ERROR" "Rollback verification failed"; exit 1; }
    
    log_message "INFO" "Rollback completed successfully"
    echo -e "${GREEN}Rollback completed successfully${NC}"
}

# Run main function
main 
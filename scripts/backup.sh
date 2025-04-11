#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKUP_DIR="backups"
BACKUP_LOG="backup.log"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
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
    echo "[$timestamp] [$level] $message" | tee -a "$BACKUP_LOG"
}

# Function to create backup directory
create_backup_dir() {
    print_header "Creating Backup Directory"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        if [ $? -eq 0 ]; then
            log_message "INFO" "Created backup directory: $BACKUP_DIR"
        else
            log_message "ERROR" "Failed to create backup directory"
            return 1
        fi
    fi
}

# Function to backup database
backup_database() {
    print_header "Backing Up Database"
    
    local backup_file="$BACKUP_DIR/database_$TIMESTAMP.sql"
    
    log_message "INFO" "Creating database backup: $backup_file"
    
    if docker-compose exec -T database pg_dump -U postgres formiq > "$backup_file"; then
        log_message "INFO" "Database backup created successfully"
        
        # Verify backup
        if [ -s "$backup_file" ]; then
            log_message "INFO" "Database backup verified"
            return 0
        else
            log_message "ERROR" "Database backup is empty"
            rm "$backup_file"
            return 1
        fi
    else
        log_message "ERROR" "Failed to create database backup"
        return 1
    fi
}

# Function to backup environment files
backup_env_files() {
    print_header "Backing Up Environment Files"
    
    local env_files=(
        "backend/.env"
        "frontend/.env"
        "infrastructure/docker/.env"
    )
    
    for env_file in "${env_files[@]}"; do
        if [ -f "$env_file" ]; then
            local backup_file="$BACKUP_DIR/$(basename "$env_file")_$TIMESTAMP"
            
            log_message "INFO" "Backing up $env_file to $backup_file"
            
            if cp "$env_file" "$backup_file"; then
                log_message "INFO" "Backed up $env_file successfully"
            else
                log_message "ERROR" "Failed to backup $env_file"
                return 1
            fi
        else
            log_message "WARNING" "Environment file not found: $env_file"
        fi
    done
}

# Function to backup SSL certificates
backup_ssl_certificates() {
    print_header "Backing Up SSL Certificates"
    
    local ssl_files=(
        "infrastructure/docker/nginx/ssl/formiq-app.com.crt"
        "infrastructure/docker/nginx/ssl/formiq-app.com.key"
    )
    
    for cert_file in "${ssl_files[@]}"; do
        if [ -f "$cert_file" ]; then
            local backup_file="$BACKUP_DIR/$(basename "$cert_file")_$TIMESTAMP"
            
            log_message "INFO" "Backing up $cert_file to $backup_file"
            
            if cp "$cert_file" "$backup_file"; then
                log_message "INFO" "Backed up $cert_file successfully"
            else
                log_message "ERROR" "Failed to backup $cert_file"
                return 1
            fi
        else
            log_message "WARNING" "SSL certificate not found: $cert_file"
        fi
    done
}

# Function to backup application code
backup_application() {
    print_header "Backing Up Application Code"
    
    local backup_file="$BACKUP_DIR/app_$TIMESTAMP.tar.gz"
    
    log_message "INFO" "Creating application backup: $backup_file"
    
    if tar --exclude='node_modules' --exclude='.git' --exclude='backups' -czf "$backup_file" .; then
        log_message "INFO" "Application backup created successfully"
        
        # Verify backup
        if [ -s "$backup_file" ]; then
            log_message "INFO" "Application backup verified"
            return 0
        else
            log_message "ERROR" "Application backup is empty"
            rm "$backup_file"
            return 1
        fi
    else
        log_message "ERROR" "Failed to create application backup"
        return 1
    fi
}

# Function to clean up old backups
cleanup_backups() {
    print_header "Cleaning Up Old Backups"
    
    for backup_type in "database" "env" "ssl" "app"; do
        local backup_count=$(find "$BACKUP_DIR" -type f -name "*.$backup_type.*" | wc -l)
        
        if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
            local files_to_delete=$((backup_count - MAX_BACKUPS))
            find "$BACKUP_DIR" -type f -name "*.$backup_type.*" -printf '%T@ %p\n' | sort -n | head -n "$files_to_delete" | cut -d' ' -f2- | xargs rm -f
            
            log_message "INFO" "Removed $files_to_delete old $backup_type backup(s)"
        fi
    done
}

# Function to verify backups
verify_backups() {
    print_header "Verifying Backups"
    
    local errors=0
    
    # Check database backup
    local db_backup=$(find "$BACKUP_DIR" -type f -name "database_$TIMESTAMP.sql" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -z "$db_backup" ] || [ ! -s "$db_backup" ]; then
        log_message "ERROR" "Database backup verification failed"
        ((errors++))
    fi
    
    # Check environment file backups
    local env_files=("backend/.env" "frontend/.env" "infrastructure/docker/.env")
    for env_file in "${env_files[@]}"; do
        local env_backup=$(find "$BACKUP_DIR" -type f -name "$(basename "$env_file")_$TIMESTAMP" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        if [ -z "$env_backup" ] || [ ! -s "$env_backup" ]; then
            log_message "ERROR" "Environment file backup verification failed: $env_file"
            ((errors++))
        fi
    done
    
    # Check SSL certificate backups
    local ssl_files=("formiq-app.com.crt" "formiq-app.com.key")
    for ssl_file in "${ssl_files[@]}"; do
        local ssl_backup=$(find "$BACKUP_DIR" -type f -name "${ssl_file}_$TIMESTAMP" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        if [ -z "$ssl_backup" ] || [ ! -s "$ssl_backup" ]; then
            log_message "ERROR" "SSL certificate backup verification failed: $ssl_file"
            ((errors++))
        fi
    done
    
    # Check application backup
    local app_backup=$(find "$BACKUP_DIR" -type f -name "app_$TIMESTAMP.tar.gz" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -z "$app_backup" ] || [ ! -s "$app_backup" ]; then
        log_message "ERROR" "Application backup verification failed"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        log_message "INFO" "All backups verified successfully"
        return 0
    else
        log_message "ERROR" "Found $errors verification errors"
        return 1
    fi
}

# Main backup function
main() {
    print_header "Starting Backup Process"
    log_message "INFO" "Backup process initiated"
    
    # Create backup log
    touch "$BACKUP_LOG"
    
    # Execute backup steps
    create_backup_dir || { log_message "ERROR" "Failed to create backup directory"; exit 1; }
    backup_database || { log_message "ERROR" "Failed to backup database"; exit 1; }
    backup_env_files || { log_message "ERROR" "Failed to backup environment files"; exit 1; }
    backup_ssl_certificates || { log_message "ERROR" "Failed to backup SSL certificates"; exit 1; }
    backup_application || { log_message "ERROR" "Failed to backup application code"; exit 1; }
    verify_backups || { log_message "ERROR" "Backup verification failed"; exit 1; }
    cleanup_backups
    
    print_header "Backup Completed Successfully"
    log_message "INFO" "Backup process completed successfully"
}

# Run main function
main 
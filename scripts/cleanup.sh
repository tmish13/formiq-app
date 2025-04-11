#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
CLEANUP_LOG="cleanup.log"
BACKUP_RETENTION_DAYS=7
TEMP_DIR_RETENTION_DAYS=1
LOG_RETENTION_DAYS=30

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$CLEANUP_LOG"
}

# Function to clean old backups
cleanup_backups() {
    print_header "Cleaning Old Backups"
    
    local backup_dir="backups"
    local deleted_count=0
    
    # Find and remove old backups
    while IFS= read -r backup_file; do
        local backup_age=$(($(date +%s) - $(stat -c %Y "$backup_file")))
        local backup_age_days=$((backup_age / 86400))
        
        if [ $backup_age_days -gt $BACKUP_RETENTION_DAYS ]; then
            rm -f "$backup_file"
            ((deleted_count++))
            log_message "INFO" "Removed old backup: $backup_file"
        fi
    done < <(find "$backup_dir" -type f -name "*.backup.*")
    
    log_message "INFO" "Removed $deleted_count old backup files"
}

# Function to clean temporary files
cleanup_temp_files() {
    print_header "Cleaning Temporary Files"
    
    local temp_dirs=(
        "frontend/build"
        "backend/__pycache__"
        "backend/*.pyc"
        "backend/.pytest_cache"
        "backend/.coverage"
        "backend/htmlcov"
        "infrastructure/terraform/.terraform"
        "infrastructure/terraform/*.tfstate"
        "infrastructure/terraform/*.tfstate.backup"
    )
    
    local deleted_count=0
    
    for pattern in "${temp_dirs[@]}"; do
        while IFS= read -r temp_file; do
            local file_age=$(($(date +%s) - $(stat -c %Y "$temp_file")))
            local file_age_days=$((file_age / 86400))
            
            if [ $file_age_days -gt $TEMP_DIR_RETENTION_DAYS ]; then
                rm -rf "$temp_file"
                ((deleted_count++))
                log_message "INFO" "Removed temporary file: $temp_file"
            fi
        done < <(find . -path "./$pattern" -type f -o -type d)
    done
    
    log_message "INFO" "Removed $deleted_count temporary files and directories"
}

# Function to clean old logs
cleanup_logs() {
    print_header "Cleaning Old Logs"
    
    local log_dirs=(
        "logs"
        "backend/logs"
        "frontend/logs"
        "infrastructure/logs"
    )
    
    local deleted_count=0
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            while IFS= read -r log_file; do
                local log_age=$(($(date +%s) - $(stat -c %Y "$log_file")))
                local log_age_days=$((log_age / 86400))
                
                if [ $log_age_days -gt $LOG_RETENTION_DAYS ]; then
                    rm -f "$log_file"
                    ((deleted_count++))
                    log_message "INFO" "Removed old log file: $log_file"
                fi
            done < <(find "$log_dir" -type f -name "*.log")
        fi
    done
    
    log_message "INFO" "Removed $deleted_count old log files"
}

# Function to clean Docker resources
cleanup_docker() {
    print_header "Cleaning Docker Resources"
    
    # Remove unused containers
    local removed_containers=$(docker container prune -f | grep "Total reclaimed space" | awk '{print $4}')
    log_message "INFO" "Removed unused containers, reclaimed $removed_containers"
    
    # Remove unused images
    local removed_images=$(docker image prune -f | grep "Total reclaimed space" | awk '{print $4}')
    log_message "INFO" "Removed unused images, reclaimed $removed_images"
    
    # Remove unused volumes
    local removed_volumes=$(docker volume prune -f | grep "Total reclaimed space" | awk '{print $4}')
    log_message "INFO" "Removed unused volumes, reclaimed $removed_volumes"
    
    # Remove unused networks
    local removed_networks=$(docker network prune -f | grep "Total reclaimed space" | awk '{print $4}')
    log_message "INFO" "Removed unused networks, reclaimed $removed_networks"
}

# Function to clean npm cache
cleanup_npm() {
    print_header "Cleaning NPM Cache"
    
    if [ -d "frontend" ]; then
        cd frontend
        local cache_size_before=$(npm cache verify | grep "Cache size" | awk '{print $3}')
        npm cache clean --force
        local cache_size_after=$(npm cache verify | grep "Cache size" | awk '{print $3}')
        log_message "INFO" "Cleaned NPM cache, reduced from $cache_size_before to $cache_size_after"
        cd ..
    fi
}

# Function to clean pip cache
cleanup_pip() {
    print_header "Cleaning Pip Cache"
    
    if [ -d "backend" ]; then
        cd backend
        local cache_size_before=$(du -sh ~/.cache/pip 2>/dev/null | awk '{print $1}')
        pip cache purge
        local cache_size_after=$(du -sh ~/.cache/pip 2>/dev/null | awk '{print $1}')
        log_message "INFO" "Cleaned pip cache, reduced from $cache_size_before to $cache_size_after"
        cd ..
    fi
}

# Function to verify cleanup
verify_cleanup() {
    print_header "Verifying Cleanup"
    
    # Check disk space
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    log_message "INFO" "Current disk usage: ${disk_usage}%"
    
    # Check backup directory size
    local backup_size=$(du -sh backups 2>/dev/null | awk '{print $1}')
    log_message "INFO" "Current backup directory size: $backup_size"
    
    # Check log directory size
    local log_size=$(du -sh logs 2>/dev/null | awk '{print $1}')
    log_message "INFO" "Current log directory size: $log_size"
    
    # Check Docker disk usage
    local docker_size=$(docker system df | grep "Total" | awk '{print $4}')
    log_message "INFO" "Current Docker disk usage: $docker_size"
}

# Main cleanup function
main() {
    print_header "Starting Deployment Cleanup"
    log_message "INFO" "Cleanup process initiated"
    
    # Create log file
    touch "$CLEANUP_LOG"
    
    # Run cleanup tasks
    cleanup_backups
    cleanup_temp_files
    cleanup_logs
    cleanup_docker
    cleanup_npm
    cleanup_pip
    verify_cleanup
    
    log_message "INFO" "Deployment cleanup completed successfully"
    print_header "Cleanup Complete"
}

# Run main function
main 
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

# Function to create backup directory
create_backup_dir() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    echo "$backup_dir"
}

# Function to backup database
backup_database() {
    print_header "Creating Database Backup"
    
    local backup_dir=$(create_backup_dir)
    local backup_file="${backup_dir}/database_backup.sql"
    
    echo -e "${YELLOW}Creating database backup...${NC}"
    if docker-compose exec -T db pg_dump -U postgres formiq > "$backup_file"; then
        echo -e "${GREEN}✓ Database backup created successfully: $backup_file${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to create database backup${NC}"
        return 1
    fi
}

# Function to backup environment files
backup_env_files() {
    print_header "Backing Up Environment Files"
    
    local backup_dir=$(create_backup_dir)
    local env_files=(
        "backend/.env.production"
        "frontend/.env.production"
    )
    
    for file in "${env_files[@]}"; do
        if [ -f "$file" ]; then
            local backup_file="${backup_dir}/$(basename "$file")"
            if cp "$file" "$backup_file"; then
                echo -e "${GREEN}✓ Backed up $file to $backup_file${NC}"
            else
                echo -e "${RED}Error: Failed to backup $file${NC}"
                return 1
            fi
        fi
    done
    
    return 0
}

# Function to backup SSL certificates
backup_ssl_certs() {
    print_header "Backing Up SSL Certificates"
    
    local backup_dir=$(create_backup_dir)
    local ssl_dir="infrastructure/docker/nginx/ssl"
    
    if [ -d "$ssl_dir" ]; then
        local backup_ssl_dir="${backup_dir}/ssl"
        if cp -r "$ssl_dir" "$backup_ssl_dir"; then
            echo -e "${GREEN}✓ Backed up SSL certificates to $backup_ssl_dir${NC}"
            return 0
        else
            echo -e "${RED}Error: Failed to backup SSL certificates${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Warning: SSL directory not found${NC}"
        return 0
    fi
}

# Function to backup configuration files
backup_config_files() {
    print_header "Backing Up Configuration Files"
    
    local backup_dir=$(create_backup_dir)
    local config_files=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "infrastructure/docker/nginx/nginx.conf"
        "infrastructure/docker/nginx/conf.d/default.conf"
    )
    
    for file in "${config_files[@]}"; do
        if [ -f "$file" ]; then
            local backup_file="${backup_dir}/$(basename "$file")"
            if cp "$file" "$backup_file"; then
                echo -e "${GREEN}✓ Backed up $file to $backup_file${NC}"
            else
                echo -e "${RED}Error: Failed to backup $file${NC}"
                return 1
            fi
        fi
    done
    
    return 0
}

# Function to restore database
restore_database() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file $backup_file does not exist${NC}"
        return 1
    fi
    
    print_header "Restoring Database"
    
    echo -e "${YELLOW}Restoring database from backup...${NC}"
    if docker-compose exec -T db psql -U postgres -d formiq < "$backup_file"; then
        echo -e "${GREEN}✓ Database restored successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to restore database${NC}"
        return 1
    fi
}

# Function to restore environment files
restore_env_files() {
    local backup_dir=$1
    
    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory $backup_dir does not exist${NC}"
        return 1
    fi
    
    print_header "Restoring Environment Files"
    
    local env_files=(
        "backend/.env.production"
        "frontend/.env.production"
    )
    
    for file in "${env_files[@]}"; do
        local backup_file="${backup_dir}/$(basename "$file")"
        if [ -f "$backup_file" ]; then
            if cp "$backup_file" "$file"; then
                echo -e "${GREEN}✓ Restored $file from backup${NC}"
            else
                echo -e "${RED}Error: Failed to restore $file${NC}"
                return 1
            fi
        fi
    done
    
    return 0
}

# Function to restore SSL certificates
restore_ssl_certs() {
    local backup_dir=$1
    
    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory $backup_dir does not exist${NC}"
        return 1
    fi
    
    print_header "Restoring SSL Certificates"
    
    local backup_ssl_dir="${backup_dir}/ssl"
    local ssl_dir="infrastructure/docker/nginx/ssl"
    
    if [ -d "$backup_ssl_dir" ]; then
        if cp -r "$backup_ssl_dir"/* "$ssl_dir"/; then
            echo -e "${GREEN}✓ Restored SSL certificates${NC}"
            return 0
        else
            echo -e "${RED}Error: Failed to restore SSL certificates${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Warning: SSL backup directory not found${NC}"
        return 0
    fi
}

# Function to restore configuration files
restore_config_files() {
    local backup_dir=$1
    
    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory $backup_dir does not exist${NC}"
        return 1
    fi
    
    print_header "Restoring Configuration Files"
    
    local config_files=(
        "docker-compose.yml"
        "docker-compose.prod.yml"
        "infrastructure/docker/nginx/nginx.conf"
        "infrastructure/docker/nginx/conf.d/default.conf"
    )
    
    for file in "${config_files[@]}"; do
        local backup_file="${backup_dir}/$(basename "$file")"
        if [ -f "$backup_file" ]; then
            if cp "$backup_file" "$file"; then
                echo -e "${GREEN}✓ Restored $file from backup${NC}"
            else
                echo -e "${RED}Error: Failed to restore $file${NC}"
                return 1
            fi
        fi
    done
    
    return 0
}

# Function to list available backups
list_backups() {
    print_header "Available Backups"
    
    local backup_dirs=($(ls -d backups/*/ 2>/dev/null))
    
    if [ ${#backup_dirs[@]} -eq 0 ]; then
        echo -e "${YELLOW}No backups found${NC}"
        return 0
    fi
    
    for dir in "${backup_dirs[@]}"; do
        echo -e "${GREEN}Backup: $(basename "$dir")${NC}"
        ls -lh "$dir"
        echo
    done
    
    return 0
}

# Main function
main() {
    local command=$1
    local backup_dir=$2
    
    case "$command" in
        "backup")
            print_header "Starting Backup"
            
            local errors=0
            backup_database || ((errors++))
            backup_env_files || ((errors++))
            backup_ssl_certs || ((errors++))
            backup_config_files || ((errors++))
            
            if [ $errors -eq 0 ]; then
                print_header "Backup Complete"
                echo -e "${GREEN}All backups completed successfully!${NC}"
                return 0
            else
                print_header "Backup Failed"
                echo -e "${RED}Found $errors issues during backup${NC}"
                return 1
            fi
            ;;
        "restore")
            if [ -z "$backup_dir" ]; then
                echo -e "${RED}Error: Backup directory not specified${NC}"
                return 1
            fi
            
            print_header "Starting Restore"
            
            local errors=0
            restore_database "${backup_dir}/database_backup.sql" || ((errors++))
            restore_env_files "$backup_dir" || ((errors++))
            restore_ssl_certs "$backup_dir" || ((errors++))
            restore_config_files "$backup_dir" || ((errors++))
            
            if [ $errors -eq 0 ]; then
                print_header "Restore Complete"
                echo -e "${GREEN}All files restored successfully!${NC}"
                return 0
            else
                print_header "Restore Failed"
                echo -e "${RED}Found $errors issues during restore${NC}"
                return 1
            fi
            ;;
        "list")
            list_backups
            ;;
        *)
            echo -e "${RED}Error: Invalid command. Use 'backup', 'restore', or 'list'${NC}"
            return 1
            ;;
    esac
}

# Run main function with arguments
main "$@" 
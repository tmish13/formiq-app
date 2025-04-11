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

# Function to check database connection
check_database_connection() {
    print_header "Checking Database Connection"
    
    if ! docker-compose exec -T db pg_isready; then
        echo -e "${RED}Error: Cannot connect to database${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Database connection successful${NC}"
    return 0
}

# Function to create database backup
create_database_backup() {
    print_header "Creating Database Backup"
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    local backup_file="$backup_dir/database_backup.sql"
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    # Create backup
    if docker-compose exec -T db pg_dump -U postgres formiq > "$backup_file"; then
        echo -e "${GREEN}✓ Database backup created: $backup_file${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to create database backup${NC}"
        return 1
    fi
}

# Function to verify database backup
verify_database_backup() {
    print_header "Verifying Database Backup"
    
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        return 1
    fi
    
    # Check if backup file is not empty
    if [ ! -s "$backup_file" ]; then
        echo -e "${RED}Error: Backup file is empty${NC}"
        return 1
    fi
    
    # Verify backup file format
    if ! head -n 1 "$backup_file" | grep -q "PostgreSQL database dump complete"; then
        echo -e "${RED}Error: Invalid backup file format${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Database backup verified successfully${NC}"
    return 0
}

# Function to run database migrations
run_migrations() {
    print_header "Running Database Migrations"
    
    # Run migrations
    if docker-compose exec -T backend python manage.py migrate; then
        echo -e "${GREEN}✓ Database migrations completed successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Database migrations failed${NC}"
        return 1
    fi
}

# Function to verify migrations
verify_migrations() {
    print_header "Verifying Migrations"
    
    # Check for pending migrations
    if docker-compose exec -T backend python manage.py showmigrations | grep -q "\[ \]"; then
        echo -e "${RED}Error: There are pending migrations${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ All migrations are applied${NC}"
    return 0
}

# Function to create database indexes
create_indexes() {
    print_header "Creating Database Indexes"
    
    # Run index creation
    if docker-compose exec -T backend python manage.py create_indexes; then
        echo -e "${GREEN}✓ Database indexes created successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to create database indexes${NC}"
        return 1
    fi
}

# Function to verify database indexes
verify_indexes() {
    print_header "Verifying Database Indexes"
    
    # Check for missing indexes
    if docker-compose exec -T backend python manage.py verify_indexes | grep -q "Missing indexes"; then
        echo -e "${RED}Error: Some indexes are missing${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ All required indexes are present${NC}"
    return 0
}

# Function to optimize database
optimize_database() {
    print_header "Optimizing Database"
    
    # Run database optimization
    if docker-compose exec -T db psql -U postgres -d formiq -c "VACUUM ANALYZE;"; then
        echo -e "${GREEN}✓ Database optimization completed successfully${NC}"
# Function to create database if it doesn't exist
create_database() {
    print_header "Creating Database"
    
    echo -e "${YELLOW}Creating database if it doesn't exist...${NC}"
    if docker-compose exec -T db psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'formiq'" | grep -q 1; then
        echo -e "${GREEN}✓ Database 'formiq' already exists${NC}"
        return 0
    else
        if docker-compose exec -T db createdb -U postgres formiq; then
            echo -e "${GREEN}✓ Database 'formiq' created successfully${NC}"
            return 0
        else
            echo -e "${RED}Error: Failed to create database${NC}"
            return 1
        fi
    fi
}

# Function to wait for database to be ready
wait_for_database() {
    print_header "Waiting for Database"
    
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for database to be ready...${NC}"
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Database is ready${NC}"
            return 0
        fi
        echo -e "${YELLOW}Attempt $attempt of $max_attempts...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}Error: Database failed to become ready after $max_attempts attempts${NC}"
    return 1
}

# Main function
main() {
    print_header "Starting Database Setup"
    
    local errors=0
    
    # Run database setup steps
    wait_for_database || ((errors++))
    create_database || ((errors++))
    check_database_connection || ((errors++))
    backup_database || ((errors++))
    run_migrations || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Database Setup Complete"
        echo -e "${GREEN}All database operations completed successfully!${NC}"
        return 0
    else
        print_header "Database Setup Failed"
        echo -e "${RED}Found $errors issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
main 
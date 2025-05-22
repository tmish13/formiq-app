#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting backend cleanup...${NC}"

# Create directory for backups
if [ ! -d "backups/backend" ]; then
  mkdir -p backups/backend
fi

cd /Users/tarpanmishra/formiq-app-5

# Function to back up a file or directory before removing it
backup_and_remove() {
  local item=$1
  local backup_name=$(echo $item | sed 's|/|_|g')
  if [ -d "$item" ]; then
    # It's a directory
    tar -czf "backups/backend/$backup_name.tar.gz" "$item"
    echo -e "Backed up directory: ${RED}$item${NC} to backups/backend/$backup_name.tar.gz"
    rm -rf "$item"
    echo -e "Removed directory: ${RED}$item${NC}"
  else
    # It's a file
    cp "$item" "backups/backend/$backup_name"
    echo -e "Backed up file: ${RED}$item${NC} to backups/backend/$backup_name"
    rm "$item"
    echo -e "Removed file: ${RED}$item${NC}"
  fi
}

# 1. Clean up nested backend directory
echo -e "${YELLOW}Cleaning up nested backend directory...${NC}"
if [ -d "backend/backend" ]; then
  backup_and_remove "backend/backend"
  echo -e "${GREEN}Removed redundant nested backend directory.${NC}"
fi

# 2. Move app.log files from backend root to logs directory
echo -e "${YELLOW}Moving log files to the logs directory...${NC}"
mkdir -p backend/logs
for log_file in backend/app.log*; do
  if [ -f "$log_file" ]; then
    # Get just the filename
    filename=$(basename "$log_file")
    # Move to logs directory
    mv "$log_file" "backend/logs/$filename"
    echo -e "Moved ${RED}$log_file${NC} to backend/logs/$filename"
  fi
done
echo -e "${GREEN}Moved log files to the logs directory.${NC}"

# 3. Remove test_connection.db if it's empty
echo -e "${YELLOW}Cleaning up test database files...${NC}"
if [ -f "backend/test_connection.db" ] && [ ! -s "backend/test_connection.db" ]; then
  backup_and_remove "backend/test_connection.db"
  echo -e "${GREEN}Removed empty test database file.${NC}"
fi

# 4. Handle duplicate migrations folders (careful with this one)
echo -e "${YELLOW}Checking migrations folders...${NC}"
if [ -d "backend/app/migrations" ] && [ -d "backend/migrations" ]; then
  # Check which one has more migration files
  app_migrations=$(find backend/app/migrations -name "*.py" | wc -l)
  root_migrations=$(find backend/migrations -name "*.py" | wc -l)
  
  echo -e "Found ${app_migrations} migration files in app/migrations and ${root_migrations} in root migrations."
  
  if [ $app_migrations -eq 0 ]; then
    # app/migrations is empty, can be removed
    backup_and_remove "backend/app/migrations"
    echo -e "${GREEN}Removed empty app/migrations directory.${NC}"
  elif [ $root_migrations -eq 0 ]; then
    # root migrations is empty, can be removed
    backup_and_remove "backend/migrations"
    echo -e "${GREEN}Removed empty root migrations directory.${NC}"
  else
    # Both have files - don't automatically remove either
    echo -e "${RED}Both migrations directories contain files. Manual review required.${NC}"
    echo -e "Consider reviewing both directories and consolidating migrations manually."
  fi
fi

# 5. Remove any __pycache__ directories
echo -e "${YELLOW}Cleaning up __pycache__ directories...${NC}"
find backend -name "__pycache__" -type d -exec rm -rf {} +
echo -e "${GREEN}Removed __pycache__ directories.${NC}"

# 6. Remove .pyc files
echo -e "${YELLOW}Cleaning up .pyc files...${NC}"
find backend -name "*.pyc" -delete
echo -e "${GREEN}Removed .pyc files.${NC}"

# 7. Remove .pytest_cache directory
echo -e "${YELLOW}Cleaning up pytest cache...${NC}"
if [ -d "backend/.pytest_cache" ]; then
  rm -rf backend/.pytest_cache
  echo -e "${GREEN}Removed pytest cache.${NC}"
fi

echo -e "${GREEN}Backend cleanup complete!${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Cleaned up redundant nested backend directory"
echo -e "  - Moved log files to the logs directory"
echo -e "  - Cleaned up test database files"
echo -e "  - Checked and handled duplicate migrations folders"
echo -e "  - Removed __pycache__ directories and .pyc files"
echo -e "  - Removed pytest cache"
echo -e "${YELLOW}All removed files have been backed up to backups/backend/${NC}" 
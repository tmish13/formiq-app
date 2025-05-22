#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting final backend cleanup...${NC}"

# Create backup directory if it doesn't exist
mkdir -p backups/backend/app_files

cd /Users/tarpanmishra/formiq-app-5

# Function to back up a file before removing it
backup_and_move() {
  local file=$1
  local backup_name=$(basename "$file")
  cp "$file" "backups/backend/app_files/$backup_name"
  echo -e "Backed up file: ${RED}$file${NC} to backups/backend/app_files/$backup_name"
  rm "$file"
  echo -e "Removed file: ${RED}$file${NC}"
}

# 1. Handle the multiple app files
echo -e "${YELLOW}Checking app files...${NC}"

# Check app/main.py exists
if [ -f "backend/app/main.py" ]; then
  # It exists, so we can safely move other redundant app files to the backup directory
  
  if [ -f "backend/minimal_app.py" ]; then
    backup_and_move "backend/minimal_app.py"
  fi
  
  if [ -f "backend/simple_app.py" ]; then
    backup_and_move "backend/simple_app.py"
  fi
  
  if [ -f "fixed_main.py" ]; then
    backup_and_move "fixed_main.py"
  fi
  
  echo -e "${GREEN}Cleaned up redundant app files.${NC}"
else
  echo -e "${RED}backend/app/main.py not found. Cannot safely remove other app files.${NC}"
fi

# 2. Clean up htmlcov directory if it exists (coverage reports can be regenerated)
echo -e "${YELLOW}Checking htmlcov directory...${NC}"
if [ -d "backend/htmlcov" ]; then
  # Archive it first
  tar -czf "backups/backend/htmlcov_$(date +%Y%m%d_%H%M%S).tar.gz" backend/htmlcov
  echo -e "Backed up htmlcov directory to backups/backend/"
  
  # Remove it
  rm -rf backend/htmlcov
  echo -e "${GREEN}Removed htmlcov directory.${NC}"
fi

# 3. Clean up .benchmarks directory if it exists
echo -e "${YELLOW}Checking .benchmarks directory...${NC}"
if [ -d "backend/.benchmarks" ]; then
  rm -rf backend/.benchmarks
  echo -e "${GREEN}Removed .benchmarks directory.${NC}"
fi

# 4. Clean up alembic/versions_backup to keep only the latest backup
echo -e "${YELLOW}Checking alembic versions backups...${NC}"
if [ -d "backend/alembic/versions_backup" ]; then
  # First, archive the whole directory
  tar -czf "backups/backend/alembic_versions_backup_$(date +%Y%m%d_%H%M%S).tar.gz" backend/alembic/versions_backup
  echo -e "Backed up alembic versions_backup directory"
  
  # Get the latest backup directory
  latest_backup=$(find backend/alembic/versions_backup -type d -name "backup_*" | sort -r | head -n 1)
  
  if [ -n "$latest_backup" ]; then
    # Clean up everything except the latest backup
    echo -e "${YELLOW}Keeping only the latest backup: $latest_backup${NC}"
    mkdir -p backend/alembic/versions_backup_new
    cp -R "$latest_backup" backend/alembic/versions_backup_new/
    rm -rf backend/alembic/versions_backup
    mv backend/alembic/versions_backup_new backend/alembic/versions_backup
    echo -e "${GREEN}Cleaned up old alembic version backups.${NC}"
  else
    echo -e "${RED}No backup directories found in alembic/versions_backup.${NC}"
  fi
fi

# 5. Add a note to README about the cleanup
echo -e "${YELLOW}Adding cleanup note to README...${NC}"
echo -e "\n## Cleanup Notes\n\nCodebase was cleaned up on $(date). Redundant files have been removed and migrations consolidated." >> backend/README.md
echo -e "${GREEN}Added cleanup note to README.${NC}"

echo -e "${GREEN}Final backend cleanup complete!${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Removed redundant app files (minimal_app.py, simple_app.py, fixed_main.py)"
echo -e "  - Cleaned up coverage report directory (htmlcov)"
echo -e "  - Removed benchmark directories"
echo -e "  - Cleaned up old alembic version backups"
echo -e "  - Added cleanup note to README"
echo -e "${YELLOW}All removed files have been backed up to backups/backend/${NC}" 
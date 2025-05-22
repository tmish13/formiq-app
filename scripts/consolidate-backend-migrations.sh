#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting migration consolidation...${NC}"

# Create backup directory if it doesn't exist
mkdir -p backups/backend/migrations

cd /Users/tarpanmishra/formiq-app-5

# First, back up both migration directories
echo -e "${YELLOW}Backing up existing migration directories...${NC}"
tar -czf "backups/backend/migrations/app_migrations_$(date +%Y%m%d_%H%M%S).tar.gz" backend/app/migrations
tar -czf "backups/backend/migrations/root_migrations_$(date +%Y%m%d_%H%M%S).tar.gz" backend/migrations
echo -e "${GREEN}Backed up both migration directories.${NC}"

# Create a consolidated migrations directory
echo -e "${YELLOW}Creating consolidated migrations directory...${NC}"
mkdir -p backend/migrations/versions_consolidated

# Copy all migration files from app/migrations to the consolidated directory
echo -e "${YELLOW}Copying app migrations...${NC}"
if [ -d "backend/app/migrations/versions" ]; then
  cp -R backend/app/migrations/versions/* backend/migrations/versions_consolidated/
  echo -e "${GREEN}Copied migrations from app/migrations/versions.${NC}"
fi

# Copy migration files from the root migrations/versions to the consolidated directory
echo -e "${YELLOW}Copying root migrations...${NC}"
if [ -d "backend/migrations/versions" ]; then
  cp -R backend/migrations/versions/* backend/migrations/versions_consolidated/
  echo -e "${GREEN}Copied migrations from migrations/versions.${NC}"
fi

# Now replace the versions directory with our consolidated one
echo -e "${YELLOW}Updating versions directory...${NC}"
mv backend/migrations/versions backend/migrations/versions_old_$(date +%Y%m%d_%H%M%S)
mv backend/migrations/versions_consolidated backend/migrations/versions
echo -e "${GREEN}Updated versions directory.${NC}"

# Remove the app/migrations directory since we've consolidated it
echo -e "${YELLOW}Removing app/migrations directory...${NC}"
rm -rf backend/app/migrations
echo -e "${GREEN}Removed app/migrations directory.${NC}"

# Create a note in the README
echo -e "${YELLOW}Adding migration note to README...${NC}"
echo -e "\n## Migration Notes\n\nMigrations were consolidated on $(date). All migration files are now in backend/migrations/versions/." >> backend/README.md
echo -e "${GREEN}Added migration note to README.${NC}"

echo -e "${GREEN}Migration consolidation complete!${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Backed up both migration directories"
echo -e "  - Consolidated all migrations into backend/migrations/versions"
echo -e "  - Removed duplicate app/migrations directory"
echo -e "  - Added migration note to README"
echo -e "${YELLOW}Note: You may need to update alembic.ini or other configuration files to point to the consolidated migrations directory.${NC}" 
#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting duplicate files cleanup...${NC}"

# Create directory for backups - make sure it exists first
mkdir -p backups/duplicates

# Function to back up a file before removing it
backup_and_remove() {
  local file=$1
  local backup_name=$(echo $file | sed 's|/|_|g')
  cp "$file" "backups/duplicates/$backup_name"
  rm "$file"
  echo -e "Backed up and removed: ${RED}$file${NC}"
}

# 1. Handle duplicate polyfills.js files
# Keep the one in frontend/src and remove others
echo -e "${YELLOW}Cleaning up polyfills.js files...${NC}"
if [ -f "polyfills.js" ]; then
  backup_and_remove "polyfills.js"
fi
if [ -f "frontend/polyfills.js" ]; then
  backup_and_remove "frontend/polyfills.js"
fi
echo -e "${GREEN}Cleaned up polyfills.js duplicates. Kept only frontend/src/polyfills.js${NC}"

# 2. Handle duplicate test results files
echo -e "${YELLOW}Cleaning up test results files...${NC}"
if [ -f "frontend/frontend/test-results.json" ]; then
  backup_and_remove "frontend/frontend/test-results.json"
fi
if [ -f "frontend/test-results-before.json" ]; then
  backup_and_remove "frontend/test-results-before.json"
fi
echo -e "${GREEN}Cleaned up test results duplicates. Kept only frontend/test-results.json${NC}"

# 3. Handle duplicate gradle files in root
# The android build.gradle files are different from the root ones, so we'll just back up the root ones
echo -e "${YELLOW}Cleaning up gradle files...${NC}"
if [ -f "build.gradle" ]; then
  backup_and_remove "build.gradle"
fi
if [ -f "variables.gradle" ]; then
  backup_and_remove "variables.gradle"
fi
echo -e "${GREEN}Cleaned up gradle duplicates from root directory${NC}"

# 4. Handle duplicate IMPROVEMENTS_SUMMARY.md
# Keep the one in frontend and remove the root one
echo -e "${YELLOW}Cleaning up IMPROVEMENTS_SUMMARY.md...${NC}"
if [ -f "IMPROVEMENTS_SUMMARY.md" ]; then
  backup_and_remove "IMPROVEMENTS_SUMMARY.md"
fi
echo -e "${GREEN}Cleaned up IMPROVEMENTS_SUMMARY.md duplicate${NC}"

# 5. Handle duplicate jest.config.js
# Keep the one in frontend and remove the root one
echo -e "${YELLOW}Cleaning up jest.config.js...${NC}"
if [ -f "jest.config.js" ]; then
  backup_and_remove "jest.config.js"
fi
echo -e "${GREEN}Cleaned up jest.config.js duplicate${NC}"

# 6. Clean up any other unnecessary test files
echo -e "${YELLOW}Cleaning up other redundant files...${NC}"
# Remove unnecessary frontend test report files
for file in "frontend-test-audit.md" "frontend-test-functionality-matrix.md" "frontend-test-refactor-plan.md" "test-consolidation-report.md"; do
  if [ -f "$file" ]; then
    backup_and_remove "$file"
  fi
done
echo -e "${GREEN}Cleaned up redundant test report files${NC}"

# Remove temporary files
if [ -f "temp.html" ]; then
  backup_and_remove "temp.html"
fi

# 7. Clean up redundant and now empty directories
echo -e "${YELLOW}Cleaning up empty directories...${NC}"
find frontend -type d -empty -not -path "*/node_modules/*" -not -path "*/\.*" -delete 2>/dev/null || true
echo -e "${GREEN}Cleaned up empty directories${NC}"

echo -e "${GREEN}Duplicate files cleanup complete!${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Cleaned up duplicate polyfills.js files"
echo -e "  - Cleaned up duplicate test results files"
echo -e "  - Cleaned up duplicate gradle files"
echo -e "  - Cleaned up duplicate IMPROVEMENTS_SUMMARY.md"
echo -e "  - Cleaned up duplicate jest.config.js"
echo -e "  - Cleaned up other redundant test files"
echo -e "  - Cleaned up empty directories"
echo -e "  - All removed files have been backed up to backups/duplicates/"

# List backup files to confirm
echo -e "${YELLOW}Files backed up to backups/duplicates/:${NC}"
ls -la backups/duplicates/ 
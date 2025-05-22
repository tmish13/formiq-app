#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleaning up unnecessary reports and summaries...${NC}"

# Create directory for archiving if it doesn't exist
if [ ! -d "archived-docs" ]; then
  mkdir -p archived-docs/migration-reports
  mkdir -p archived-docs/test-reports
  mkdir -p archived-docs/coverage-reports
fi

# Move migration reports to archive folder (keeping them for reference but out of the main directory)
echo -e "${YELLOW}Archiving migration reports...${NC}"
find . -name "*migration-report*.md" -o -name "*migration-summary*.md" | grep -v "archived-docs" | while read file; do
  if [ -f "$file" ]; then
    mv "$file" "archived-docs/migration-reports/$(basename "$file")"
    echo "Archived: $file"
  fi
done

# Remove unnecessary coverage and test reports
echo -e "${YELLOW}Removing unnecessary coverage reports...${NC}"
rm -rf frontend/coverage 2>/dev/null || true
rm -rf coverage 2>/dev/null || true
rm -f frontend/test-audit-report.md 2>/dev/null || true

# Keep coverage-budget.json as it's needed for the CI/CD pipeline
# But move other test summaries to archive
find . -name "*audit-summary*.md" -o -name "*test-*-summary*.md" | grep -v "archived-docs" | while read file; do
  if [ -f "$file" ]; then
    mv "$file" "archived-docs/test-reports/$(basename "$file")"
    echo "Archived: $file"
  fi
done

echo -e "${GREEN}Cleanup complete.${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Archived migration reports to archived-docs/migration-reports/"
echo -e "  - Removed coverage reports and directories"
echo -e "  - Archived test summaries to archived-docs/test-reports/"
echo -e "  - Kept coverage-budget.json for CI/CD pipeline" 
#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting file structure optimization...${NC}"

# 1. Remove empty directories in the entire project
echo -e "${YELLOW}Removing empty directories...${NC}"
find . -type d -empty -not -path "*/node_modules/*" -not -path "*/\.*" -not -path "*/coverage/*" -delete 2>/dev/null || true
echo -e "${GREEN}Empty directories removed.${NC}"

# 2. Remove common unnecessary files that might be accidentally committed
echo -e "${YELLOW}Removing unnecessary files...${NC}"
find . -name ".DS_Store" -o -name "*.swp" -o -name "*.swo" -o -name "*~" -o -name "Thumbs.db" -o -name ".directory" | xargs rm -f 2>/dev/null || true
echo -e "${GREEN}Unnecessary files removed.${NC}"

# 3. Clean up potential build artifacts that shouldn't be in the repo
echo -e "${YELLOW}Cleaning up build artifacts...${NC}"
find . -type d -name "dist" -not -path "*/node_modules/*" | xargs rm -rf 2>/dev/null || true
find . -type d -name "build" -not -path "*/node_modules/*" | xargs rm -rf 2>/dev/null || true
echo -e "${GREEN}Build artifacts cleaned up.${NC}"

# 4. Optimize legacy tests folder to only keep unique files
echo -e "${YELLOW}Optimizing legacy tests folder...${NC}"

# 4a. Remove duplicated test files in deeply nested structure
if [ -d "frontend/src/__legacy_tests__/src" ]; then
  echo -e "${YELLOW}Cleaning up deeply nested test structure...${NC}"
  find frontend/src/__legacy_tests__/src -type f -name "*.test.ts" -o -name "*.test.tsx" | while read file; do
    # Get the relative path from src
    rel_path=$(echo "$file" | sed -e 's|frontend/src/__legacy_tests__/src/||')
    
    # Check if the same file exists in the top level
    if [ -f "frontend/src/__legacy_tests__/$rel_path" ]; then
      # It's a duplicate, remove it
      rm "$file"
      echo "Removed duplicate: $file"
    fi
  done
  echo -e "${GREEN}Deeply nested test structure cleaned up.${NC}"
fi

# 5. Remove empty directories again after the cleanup
echo -e "${YELLOW}Removing empty directories after cleanup...${NC}"
find . -type d -empty -not -path "*/node_modules/*" -not -path "*/\.*" -not -path "*/coverage/*" -delete 2>/dev/null || true
echo -e "${GREEN}Empty directories removed.${NC}"

# 6. Create an optimized structure summary
echo -e "${YELLOW}Creating file structure summary...${NC}"

# Count consolidated tests
CONSOLIDATED_TESTS=$(find tests/consolidated -name "*.consolidated.test.tsx" | wc -l)

# Count legacy tests
LEGACY_TESTS=$(find frontend/src/__legacy_tests__ -name "*.test.tsx" -o -name "*.test.ts" | wc -l)

# Get directory sizes
CONSOLIDATED_SIZE=$(du -sh tests/consolidated | cut -f1)
LEGACY_SIZE=$(du -sh frontend/src/__legacy_tests__ | cut -f1)

echo -e "${GREEN}Codebase structure optimization complete!${NC}"
echo -e "${YELLOW}Summary:${NC}"
echo -e "  - Consolidated tests: ${CONSOLIDATED_TESTS} files (${CONSOLIDATED_SIZE})"
echo -e "  - Legacy tests: ${LEGACY_TESTS} files (${LEGACY_SIZE})"
echo -e "  - Removed empty directories and unnecessary files"
echo -e "  - Cleaned up build artifacts"
echo -e "  - Optimized legacy tests folder structure"

echo -e "${GREEN}File structure has been optimized successfully!${NC}" 
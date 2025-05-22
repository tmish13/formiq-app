#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting codebase cleanup...${NC}"

# 1. Remove nested legacy tests directory
if [ -d "frontend/src/__legacy_tests__/src/__legacy_tests__" ]; then
  echo -e "${YELLOW}Removing nested legacy tests directory...${NC}"
  rm -rf frontend/src/__legacy_tests__/src/__legacy_tests__
  echo -e "${GREEN}Nested legacy tests directory removed.${NC}"
fi

# 2. Remove duplicate consolidated test files from legacy folder
echo -e "${YELLOW}Removing duplicate consolidated test files from legacy folder...${NC}"
find frontend/src/__legacy_tests__ -name "*\.consolidated\.*" -type f -delete
echo -e "${GREEN}Duplicate consolidated test files removed.${NC}"

# 3. Move snapshot directories to the legacy folder
if [ -d "frontend/src/components/__tests__/__snapshots__" ]; then
  echo -e "${YELLOW}Moving snapshot directories to legacy folder...${NC}"
  
  # Create target directory if it doesn't exist
  mkdir -p frontend/src/__legacy_tests__/components/__tests__/__snapshots__
  
  # Move snapshots
  cp -r frontend/src/components/__tests__/__snapshots__/* frontend/src/__legacy_tests__/components/__tests__/__snapshots__/
  rm -rf frontend/src/components/__tests__/__snapshots__
  
  echo -e "${GREEN}Snapshot directories moved to legacy folder.${NC}"
fi

if [ -d "frontend/src/components/FormValidation/__tests__/__snapshots__" ]; then
  echo -e "${YELLOW}Moving FormValidation snapshot directories to legacy folder...${NC}"
  
  # Create target directory if it doesn't exist
  mkdir -p frontend/src/__legacy_tests__/components/FormValidation/__tests__/__snapshots__
  
  # Move snapshots
  cp -r frontend/src/components/FormValidation/__tests__/__snapshots__/* frontend/src/__legacy_tests__/components/FormValidation/__tests__/__snapshots__/
  rm -rf frontend/src/components/FormValidation/__tests__/__snapshots__
  
  echo -e "${GREEN}FormValidation snapshot directories moved to legacy folder.${NC}"
fi

# 4. Check for any other test files in the src directory that might have been missed
echo -e "${YELLOW}Checking for missed test files...${NC}"
MISSED_TESTS=$(find frontend/src -name "*.test.tsx" -o -name "*.test.ts" | grep -v "__legacy_tests__" | wc -l)

if [ $MISSED_TESTS -gt 0 ]; then
  echo -e "${RED}Found $MISSED_TESTS test files that weren't moved to the legacy folder.${NC}"
  echo -e "${YELLOW}Moving them now...${NC}"
  
  find frontend/src -name "*.test.tsx" -o -name "*.test.ts" | grep -v "__legacy_tests__" | while read -r test_file; do
    # Extract relative path within src
    rel_path=$(echo "$test_file" | sed 's|frontend/src/||')
    
    # Create target directory
    target_dir="frontend/src/__legacy_tests__/$(dirname "$rel_path")"
    mkdir -p "$target_dir"
    
    # Copy file
    cp "$test_file" "$target_dir/$(basename "$test_file")"
    echo "Moved $test_file to $target_dir/$(basename "$test_file")"
    
    # Delete original
    rm "$test_file"
  done
  
  echo -e "${GREEN}All missed test files moved to legacy folder.${NC}"
else
  echo -e "${GREEN}No missed test files found.${NC}"
fi

# 5. Remove any empty directories in the src folder
echo -e "${YELLOW}Removing empty directories...${NC}"
find frontend/src -type d -empty -not -path "*/node_modules/*" -not -path "*/\.*" -delete
echo -e "${GREEN}Empty directories removed.${NC}"

# 6. Clean up any temporary files that shouldn't be in the repo
echo -e "${YELLOW}Cleaning up temporary files...${NC}"
find frontend -name "*.tmp" -o -name "*.log" -o -name ".DS_Store" -o -name "*.bak" | grep -v "node_modules" | xargs rm -f 2>/dev/null || true
echo -e "${GREEN}Temporary files cleaned up.${NC}"

echo -e "${GREEN}Codebase cleanup complete!${NC}"
echo -e "${YELLOW}Summary of actions:${NC}"
echo -e "  - Removed nested legacy tests directory"
echo -e "  - Removed duplicate consolidated test files from legacy folder"
echo -e "  - Moved snapshot directories to legacy folder"
echo -e "  - Moved any missed test files to legacy folder"
echo -e "  - Removed empty directories"
echo -e "  - Cleaned up temporary files" 
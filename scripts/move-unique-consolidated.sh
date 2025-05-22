#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Finding and handling consolidated test files outside the main directory...${NC}"

# Create a temporary directory to store potential newer versions
mkdir -p .tmp-consolidated

# Find all consolidated test files outside the main directory
find . -name "*.consolidated.test.*" | grep -v "tests/consolidated" | grep -v "node_modules" | while read file; do
  if [ -f "$file" ]; then
    base_filename=$(basename "$file")
    
    # Check if the file exists in the consolidated directory
    if [ -f "tests/consolidated/$base_filename" ]; then
      # Files exist in both locations, check which is newer and larger
      original_date=$(stat -f "%m" "$file")
      consolidated_date=$(stat -f "%m" "tests/consolidated/$base_filename")
      original_size=$(stat -f "%z" "$file")
      consolidated_size=$(stat -f "%z" "tests/consolidated/$base_filename")
      
      echo "Comparing: $file (size: $original_size, date: $original_date) vs tests/consolidated/$base_filename (size: $consolidated_size, date: $consolidated_date)"
      
      # If the original file is newer or larger, we'll replace the consolidated version
      if [[ $original_date -gt $consolidated_date ]] || [[ $original_size -gt $consolidated_size ]]; then
        echo -e "${YELLOW}Found newer/larger version: $file${NC}"
        # Copy the original file to a temporary location (we'll move them all at once later)
        cp "$file" ".tmp-consolidated/$base_filename"
        echo "Marked for replacement: $file"
      else
        echo "Keeping consolidated version, removing duplicate: $file"
        rm "$file"
      fi
    else
      # File only exists outside consolidated directory - it's unique
      echo -e "${GREEN}Found unique file: $file${NC}"
      cp "$file" ".tmp-consolidated/$base_filename"
      echo "Marked for moving: $file"
      rm "$file"
    fi
  fi
done

# Now move any better versions to the consolidated directory
find .tmp-consolidated -type f | while read tmp_file; do
  base_name=$(basename "$tmp_file")
  if [ -f "tests/consolidated/$base_name" ]; then
    echo "Replacing consolidated/$base_name with newer version"
    mv "$tmp_file" "tests/consolidated/$base_name"
  else
    echo "Adding new file to consolidated tests: $base_name"
    mv "$tmp_file" "tests/consolidated/$base_name"
  fi
done

# Cleanup
rm -rf .tmp-consolidated

# Handle legacy archive files - we don't need duplicates
echo -e "${YELLOW}Handling legacy archive consolidated tests...${NC}"
find ./tests/legacy/_archive -name "*.consolidated.test.*" -type f -delete
echo -e "${GREEN}Removed consolidated tests from legacy archive.${NC}"

echo -e "${GREEN}All consolidated test files have been unified into the main directory.${NC}"
echo "Listing current consolidated test files:"
find tests/consolidated -name "*.consolidated.test.*" | sort 
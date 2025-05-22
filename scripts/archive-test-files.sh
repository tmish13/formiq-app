#!/bin/bash

# Script to archive test files from frontend/src to tests/legacy/_archive/
# Created as part of the test consolidation tasks

set -e

echo "📦 Archiving test files to tests/legacy/_archive/..."
cd "$(dirname "$0")/.."

# Create the archive directory if it doesn't exist
mkdir -p tests/legacy/_archive

# Count test files before archiving
OLD_COUNT=$(find frontend/src -name "*.test.ts*" | wc -l)
echo "Found $OLD_COUNT test files to archive"

# Get a list of directories containing test files
TEST_DIRS=$(find frontend/src -name "__tests__" -type d)

# Archive each test file while preserving directory structure
for dir in $TEST_DIRS; do
  # Get the relative path from frontend/src
  REL_PATH=${dir#frontend/src/}
  
  # Create the target directory
  mkdir -p "tests/legacy/_archive/$REL_PATH"
  
  # Find and copy each test file
  for test_file in $(find "$dir" -name "*.test.ts*"); do
    # Get the filename
    filename=$(basename "$test_file")
    
    # Copy the file to the archive directory
    cp "$test_file" "tests/legacy/_archive/$REL_PATH/$filename"
    echo "Archived: $test_file → tests/legacy/_archive/$REL_PATH/$filename"
  done
done

# Also find test files that are not in __tests__ directories
for test_file in $(find frontend/src -name "*.test.ts*" | grep -v "__tests__"); do
  # Get the directory path relative to frontend/src
  dir_path=$(dirname "${test_file#frontend/src/}")
  
  # Create the target directory
  mkdir -p "tests/legacy/_archive/$dir_path"
  
  # Get the filename
  filename=$(basename "$test_file")
  
  # Copy the file to the archive directory
  cp "$test_file" "tests/legacy/_archive/$dir_path/$filename"
  echo "Archived: $test_file → tests/legacy/_archive/$dir_path/$filename"
done

# Count archived files
ARCHIVED_COUNT=$(find tests/legacy/_archive -name "*.test.ts*" | wc -l)
echo "✅ Archived $ARCHIVED_COUNT test files to tests/legacy/_archive/"

# Display consolidated test files
CONSOLIDATED_COUNT=$(find tests/consolidated -name "*.consolidated.test.ts*" | wc -l)
echo "ℹ️ Found $CONSOLIDATED_COUNT consolidated test files in tests/consolidated/"

echo "📋 Summary:"
echo "  - Original test files: $OLD_COUNT"
echo "  - Archived test files: $ARCHIVED_COUNT"
echo "  - Consolidated test files: $CONSOLIDATED_COUNT"
echo ""
echo "⚠️ Note: The original test files have been archived but not removed."
echo "   To remove them, run: find frontend/src -name \"*.test.ts*\" -exec rm {} \\;"
echo ""
echo "   First verify that the tests work with just the consolidated files by running:"
echo "   cd frontend && npm test -- --testPathPattern=\"tests/consolidated\"" 
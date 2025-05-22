#!/bin/bash

# Script to verify that all test files have been archived
# Created as part of the test consolidation tasks

set -e

echo "🔍 Verifying that all test files have been properly archived..."
cd "$(dirname "$0")/.."

# Count original test files in frontend/src
ORIGINAL_COUNT=$(find frontend/src -name "*.test.ts*" | wc -l)
echo "Found $ORIGINAL_COUNT test files in frontend/src"

# Count archived test files
ARCHIVED_COUNT=$(find tests/legacy/_archive -name "*.test.ts*" | wc -l)
echo "Found $ARCHIVED_COUNT test files in tests/legacy/_archive"

# Count consolidated test files
CONSOLIDATED_COUNT=$(find tests/consolidated -name "*.consolidated.test.ts*" | wc -l)
echo "Found $CONSOLIDATED_COUNT consolidated test files in tests/consolidated"

# Check if all files have been archived
if [ "$ORIGINAL_COUNT" -gt "$ARCHIVED_COUNT" ]; then
  echo "❌ Not all test files have been archived."
  echo "   There are $ORIGINAL_COUNT test files in frontend/src, but only $ARCHIVED_COUNT in tests/legacy/_archive"
  
  # Find files that have not been archived
  echo ""
  echo "Files that have not been archived:"
  for file in $(find frontend/src -name "*.test.ts*"); do
    filename=$(basename "$file")
    if ! find tests/legacy/_archive -name "$filename" | grep . > /dev/null; then
      echo "   $file"
    fi
  done
  
  echo ""
  echo "To archive these files, run:"
  echo "./scripts/archive-test-files.sh"
else
  echo "✅ All test files have been archived successfully."
fi

# Check that consolidated test files are properly structured
echo ""
echo "Checking consolidated test file structure..."

# Check if all consolidated test files have the right naming pattern
VALID_PATTERN_COUNT=$(find tests/consolidated -name "*.consolidated.test.ts*" | wc -l)
if [ "$VALID_PATTERN_COUNT" -ne "$CONSOLIDATED_COUNT" ]; then
  echo "❌ Some consolidated test files do not follow the correct naming pattern."
  echo "   All consolidated test files should be named ComponentName.consolidated.test.tsx"
  
  # Find files with incorrect patterns
  for file in $(find tests/consolidated -type f); do
    if [[ ! "$file" =~ \.consolidated\.test\.(tsx|ts)$ ]]; then
      echo "   Incorrect pattern: $file"
    fi
  done
else
  echo "✅ All consolidated test files follow the correct naming pattern."
fi

# Check if there's a __snapshots__ directory for consolidated tests
if [ ! -d "tests/consolidated/__snapshots__" ]; then
  echo "❌ Missing __snapshots__ directory for consolidated tests."
  echo "   Run ./scripts/update-snapshots.sh to create it."
else
  echo "✅ Found __snapshots__ directory for consolidated tests."
  
  # Check if there are snapshots for each consolidated test file
  SNAPSHOT_COUNT=$(find tests/consolidated/__snapshots__ -name "*.snap" | wc -l)
  echo "   Found $SNAPSHOT_COUNT snapshot files in consolidated tests."
fi

echo ""
echo "📋 Summary:"
echo "  - Original test files: $ORIGINAL_COUNT"
echo "  - Archived test files: $ARCHIVED_COUNT"
echo "  - Consolidated test files: $CONSOLIDATED_COUNT"

if [ "$ORIGINAL_COUNT" -eq "$ARCHIVED_COUNT" ] && [ "$VALID_PATTERN_COUNT" -eq "$CONSOLIDATED_COUNT" ]; then
  echo "✅ The test structure looks good!"
  echo "   You can now move forward with updating snapshots."
  echo "   Run: ./scripts/update-snapshots.sh"
else
  echo "❌ There are issues with the test structure that need to be resolved."
  echo "   Please address the issues above before proceeding."
fi 
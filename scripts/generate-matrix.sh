#!/bin/bash

# Script to generate a simple version of the test functionality matrix
# Usage: ./generate-matrix.sh

set -e

MATRIX_FILE="../frontend-test-functionality-matrix.md"
CONSOLIDATED_DIR="../tests/consolidated"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}FormIQ Test Matrix Generator${NC}"
echo "================================"

# Ensure consolidated directory exists
if [ ! -d "$CONSOLIDATED_DIR" ]; then
  echo -e "${RED}Error: Consolidated test directory not found: $CONSOLIDATED_DIR${NC}"
  exit 1
fi

# Create matrix header
cat > $MATRIX_FILE << EOL
# Frontend Test Functionality Matrix

This document maps test files to the specific functionalities they test, helping identify coverage gaps and redundancies.

EOL

# Function to add a category section
add_category() {
  local category=$1
  local search_pattern=$2
  
  echo -e "${YELLOW}Processing category: $category${NC}"
  
  echo -e "\n### $category" >> $MATRIX_FILE
  echo "| Functionality | Status | Test File(s) |" >> $MATRIX_FILE
  echo "|---------------|--------|-------------|" >> $MATRIX_FILE
  
  # Find files matching the pattern
  local files=""
  if [ -n "$search_pattern" ]; then
    files=$(find ../frontend/src ../tests -type f -name "*.test.ts*" | grep -i "$search_pattern" || echo "")
  fi
  
  if [ -z "$files" ]; then
    echo "| $category | Pending | (None) |" >> $MATRIX_FILE
    return
  fi
  
  # Extract functionalities from filenames
  for file in $files; do
    filename=$(basename "$file")
    
    # Determine if this is a consolidated test
    if [[ "$filename" == *".consolidated."* ]]; then
      status="Complete"
    else
      status="Pending"
    fi
    
    # Extract functionality from filename
    functionality=$(echo "$filename" | sed -E 's/([A-Za-z]+)\..*/\1/')
    functionality=${functionality:-"$category"}
    
    echo "| $functionality | $status | \`$filename\` |" >> $MATRIX_FILE
  done
}

# Add category sections
add_category "Upload Guidance & Flow" "upload"
add_category "Form Analysis" "form"
add_category "User Authentication" "auth"
add_category "Profile Management" "profile"
add_category "API Services" "api\|service"
add_category "Custom Hooks" "hook"
add_category "Video Service" "video"
add_category "Subscription Management" "subscription"
add_category "Pose Analysis" "pose"
add_category "Exercise Analysis" "exercise"
add_category "Form Check Redux Flow" "formCheck\|form-check"
add_category "End-to-End User Flows" "e2e\|flow"
add_category "Security & Performance" "security\|performance"

# Add next steps section
cat >> $MATRIX_FILE << EOL

## Next Steps

1. **Validate this Matrix**:
   - Confirm that all behaviors are correctly mapped
   - Ensure no critical behaviors are missing
   - Verify primary test locations make sense

2. **Continue Consolidation**:
   - Start with highest-priority areas
   - Refactor primary test locations to be behavior-focused
   - Migrate unique test coverage from other files
   - Remove redundant tests

3. **Track Progress**:
   - Update the Status column as work progresses
   - Document test file deletions
   - Measure coverage to ensure no functionality is lost
EOL

echo -e "${GREEN}Matrix written to $MATRIX_FILE${NC}" 
#!/bin/bash

# Script to analyze test files and identify candidates for consolidation
# Usage: ./check-consolidation.sh

set -e

REPORT_FILE="../test-consolidation-report.md"
FRONTEND_DIR="../frontend/src"
TESTS_DIR="../tests"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}FormIQ Test Consolidation Analyzer${NC}"
echo "===================================="

# Create report header
cat > $REPORT_FILE << EOL
# Test Consolidation Report

This report identifies test files that are candidates for consolidation based on naming patterns and functionality overlap.

EOL

# Function to find test files by pattern
find_test_files() {
  local pattern=$1
  find $FRONTEND_DIR $TESTS_DIR -type f -name "*.test.ts*" | grep -i "$pattern" || echo ""
}

# Function to analyze a category
analyze_category() {
  local category=$1
  local search_pattern=$2
  
  echo -e "${YELLOW}Analyzing category: $category${NC}"
  
  echo -e "\n## $category" >> $REPORT_FILE
  
  # Find files matching the pattern
  local files=$(find_test_files "$search_pattern")
  
  if [ -z "$files" ]; then
    echo "No test files found for pattern: $search_pattern" >> $REPORT_FILE
    return
  fi
  
  # Check if we already have a consolidated test file
  if echo "$files" | grep -q ".consolidated."; then
    echo "✅ Consolidated test file exists" >> $REPORT_FILE
    echo -e "${GREEN}Found consolidated test file(s)${NC}"
  else
    echo "❌ No consolidated test file found" >> $REPORT_FILE
    echo -e "${RED}No consolidated test file found${NC}"
  fi
  
  # Count test files
  local count=$(echo "$files" | wc -l | tr -d ' ')
  echo "Total test files: $count" >> $REPORT_FILE
  
  # List all files
  echo "### Test files:" >> $REPORT_FILE
  echo "| File | Line Count | Test Count | Consolidation Status |" >> $REPORT_FILE
  echo "|------|------------|------------|---------------------|" >> $REPORT_FILE
  
  for file in $files; do
    filename=$(basename "$file")
    line_count=$(wc -l < "$file" | tr -d ' ')
    test_count=$(grep -c "it(" "$file" || echo "0")
    
    # Determine status
    if [[ "$filename" == *".consolidated."* ]]; then
      status="✅ Primary"
    else
      # Check for duplication with consolidated tests
      if echo "$files" | grep -q ".consolidated."; then
        status="⚠️ Candidate for removal"
      else
        status="⚠️ Candidate for consolidation"
      fi
    fi
    
    echo "| \`$filename\` | $line_count | $test_count | $status |" >> $REPORT_FILE
  done
}

# Analyze categories
analyze_category "Upload Guidance & Flow" "upload"
analyze_category "Form Analysis" "form"
analyze_category "User Authentication" "auth"
analyze_category "Profile Management" "profile"
analyze_category "API Services" "api\|service"
analyze_category "Custom Hooks" "hook"
analyze_category "Video Service" "video"
analyze_category "Subscription Management" "subscription"
analyze_category "Pose Analysis" "pose"
analyze_category "Exercise Analysis" "exercise"
analyze_category "Form Check Redux Flow" "formCheck\|form-check"
analyze_category "End-to-End User Flows" "e2e\|flow"
analyze_category "Security & Performance" "security\|performance"

# Add summary and recommendations
cat >> $REPORT_FILE << EOL

## Summary and Recommendations

### Consolidation Progress
- Categories with consolidated tests: $(grep -c "✅ Consolidated test file exists" $REPORT_FILE || echo "0")
- Categories needing consolidation: $(grep -c "❌ No consolidated test file found" $REPORT_FILE || echo "0")

### Next Steps
1. **Create consolidated test files** for categories marked with ❌
2. **Review and migrate unique tests** from files marked as "Candidate for removal"
3. **Archive redundant test files** once their content has been migrated
4. **Update the test matrix** to reflect the new structure
EOL

echo -e "${GREEN}Report written to $REPORT_FILE${NC}"
echo "You can now review the recommendations and begin consolidation work." 
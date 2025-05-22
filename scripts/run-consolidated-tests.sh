#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running consolidated tests only...${NC}"

# Add environment variables to help with React version conflicts
export NODE_OPTIONS="--unhandled-rejections=strict --max-old-space-size=4096"
export SKIP_PREFLIGHT_CHECK=true
export REACT_APP_SKIP_RECONCILIATION_ERROR=true

# Run Jest with the pattern matching only consolidated tests
cd frontend && npm run test:consolidated

# Check the exit code from the tests run
if [ $? -ne 0 ]; then
  echo -e "${RED}Consolidated tests failed. See error details above.${NC}"
  echo -e "${YELLOW}Some failures may be due to React version mismatches or import path issues.${NC}"
  echo -e "${YELLOW}You can still continue with the tests that pass while fixing the failing ones incrementally.${NC}"
  
  # Still attempt to generate coverage from the tests that passed
  echo -e "${YELLOW}Generating coverage report for consolidated tests that succeeded...${NC}"
  npm run test:coverage:consolidated || true
  
  echo -e "${YELLOW}Coverage report available at:${NC} file://$(pwd)/../coverage/index.html"
  
  # Count consolidated tests
  TEST_COUNT=$(find ../tests/consolidated -name "*.consolidated.test.tsx" | wc -l)
  echo -e "${GREEN}Found ${TEST_COUNT} consolidated test files.${NC}"
  exit 1
else
  echo -e "${GREEN}All consolidated tests passed successfully!${NC}"
  
  # Now generate coverage report focusing only on consolidated tests
  echo -e "${YELLOW}Generating coverage report for consolidated tests...${NC}"
  npm run test:coverage:consolidated
  
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to generate coverage report.${NC}"
    exit 1
  else
    echo -e "${GREEN}Coverage report generated successfully.${NC}"
    echo -e "${YELLOW}Coverage report available at:${NC} file://$(pwd)/../coverage/index.html"
    
    # Count consolidated tests
    TEST_COUNT=$(find ../tests/consolidated -name "*.consolidated.test.tsx" | wc -l)
    echo -e "${GREEN}Found ${TEST_COUNT} consolidated test files.${NC}"
    exit 0
  fi
fi

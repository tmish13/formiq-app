#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Verifying test structure to ensure all tests are properly consolidated...${NC}"

# Check for test files that are not in the consolidated directory and not archived
NON_CONSOLIDATED_TESTS=$(find frontend/src -name "*.test.tsx" -o -name "*.test.ts" | grep -v "__tests__" | wc -l)
TESTS_IN_SRC_TESTS_DIR=$(find frontend/src -path "*/src/__tests__/*" -name "*.test.tsx" -o -name "*.test.ts" | wc -l)
TESTS_IN_COMPONENTS_TESTS_DIR=$(find frontend/src -path "*/src/components/__tests__/*" -name "*.test.tsx" -o -name "*.test.ts" | wc -l)
TESTS_IN_SERVICES_TESTS_DIR=$(find frontend/src -path "*/src/services/__tests__/*" -name "*.test.tsx" -o -name "*.test.ts" | wc -l)

# Check for tests in consolidated directory
CONSOLIDATED_TESTS=$(find tests/consolidated -name "*.consolidated.test.tsx" -o -name "*.consolidated.test.ts" | wc -l)

# Check for archived tests
ARCHIVED_TESTS=$(find tests/legacy/_archive -name "*.test.tsx" -o -name "*.test.ts" | wc -l)

echo -e "\n${YELLOW}Test Structure Analysis:${NC}"
echo -e "Tests in frontend/src: ${NON_CONSOLIDATED_TESTS}"
echo -e "Tests in frontend/src/__tests__: ${TESTS_IN_SRC_TESTS_DIR}"
echo -e "Tests in frontend/src/components/__tests__: ${TESTS_IN_COMPONENTS_TESTS_DIR}"
echo -e "Tests in frontend/src/services/__tests__: ${TESTS_IN_SERVICES_TESTS_DIR}"
echo -e "Consolidated tests in tests/consolidated: ${CONSOLIDATED_TESTS}"
echo -e "Archived tests in tests/legacy/_archive: ${ARCHIVED_TESTS}"

# Verify consolidated test naming pattern
INCORRECT_NAMING=$(find tests/consolidated -name "*.test.tsx" -o -name "*.test.ts" | grep -v "consolidated" | wc -l)
if [ $INCORRECT_NAMING -gt 0 ]; then
  echo -e "\n${RED}Error: Found ${INCORRECT_NAMING} test files in consolidated directory that don't follow the *.consolidated.test.tsx naming pattern.${NC}"
  find tests/consolidated -name "*.test.tsx" -o -name "*.test.ts" | grep -v "consolidated"
  echo -e "Please rename these files to follow the naming convention."
  exit 1
fi

# Verify snapshot directory
if [ ! -d "tests/consolidated/__snapshots__" ]; then
  echo -e "\n${RED}Error: __snapshots__ directory not found in tests/consolidated.${NC}"
  echo -e "Create it with: mkdir -p tests/consolidated/__snapshots__"
  mkdir -p tests/consolidated/__snapshots__
  echo -e "${GREEN}Created tests/consolidated/__snapshots__ directory.${NC}"
fi

# Count snapshot files
SNAPSHOT_COUNT=$(find tests/consolidated/__snapshots__ -name "*.snap" | wc -l)
echo -e "Snapshot files in tests/consolidated/__snapshots__: ${SNAPSHOT_COUNT}"

# Summary
echo -e "\n${YELLOW}Summary:${NC}"
TOTAL_TESTS=$((NON_CONSOLIDATED_TESTS + TESTS_IN_SRC_TESTS_DIR + TESTS_IN_COMPONENTS_TESTS_DIR + TESTS_IN_SERVICES_TESTS_DIR + CONSOLIDATED_TESTS + ARCHIVED_TESTS))
echo -e "Total test files found: ${TOTAL_TESTS}"

if [ $INCORRECT_NAMING -gt 0 ]; then
  echo -e "${RED}❌ Test structure has errors that need to be fixed.${NC}"
else
  echo -e "${GREEN}✅ Test structure looks good! All consolidated tests follow the correct naming pattern.${NC}"
  echo -e "Run ./scripts/run-consolidated-tests.sh to run only the consolidated tests."
  echo -e "Run ./scripts/update-snapshots.sh to update the snapshots."
fi

exit 0 
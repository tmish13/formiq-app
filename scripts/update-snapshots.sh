#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Updating Jest snapshots in consolidated test files...${NC}"

# Ensure the snapshots directory exists
mkdir -p tests/consolidated/__snapshots__

# Run Jest with the update snapshot flag specifically for consolidated tests
cd frontend && npm test -- --updateSnapshot --testPathPattern="tests/consolidated"

# Check the exit code
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to update snapshots. See error details above.${NC}"
  exit 1
else
  echo -e "${GREEN}Snapshots updated successfully!${NC}"
  
  # Count updated snapshots
  SNAPSHOT_COUNT=$(find ../tests/consolidated/__snapshots__ -type f | wc -l)
  echo -e "${GREEN}Updated ${SNAPSHOT_COUNT} snapshot files in tests/consolidated/__snapshots__${NC}"
  exit 0
fi 
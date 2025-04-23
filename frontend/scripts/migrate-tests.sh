#!/bin/bash

# Create new test directories if they don't exist
mkdir -p tests/unit/components/{common,form,layout}
mkdir -p tests/unit/hooks
mkdir -p tests/unit/services
mkdir -p tests/integration/api
mkdir -p tests/e2e/flows

# Move component tests
mv src/__tests__/components/common/* tests/unit/components/common/
mv src/__tests__/components/social/* tests/unit/components/form/

# Move hook tests
mv src/__tests__/hooks/* tests/unit/hooks/

# Move service tests
mv src/__tests__/services/* tests/unit/services/

# Clean up old test directories
rm -rf src/__tests__/components
rm -rf src/__tests__/hooks
rm -rf src/__tests__/services

echo "Test migration completed successfully!" 
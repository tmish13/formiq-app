#!/bin/bash

# Test Authentication Module
# This script runs the tests for the authentication module to verify that all auth flows work correctly

set -e # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up test environment...${NC}"

# Set testing environment variables
export ENVIRONMENT="test"
export TESTING="True"
export DATABASE_TEST_URL="sqlite:///./test.db"
export JWT_SECRET="testing_secret_key_dont_use_in_production"
export COOKIE_SECURE="False"

# Change to the backend directory
cd backend

echo -e "${BLUE}Running authentication tests...${NC}"

# Check if pytest-cov is installed
if pip list | grep -q pytest-cov; then
  # Run tests with coverage
  python -m pytest app/tests/test_auth_flows.py -v --cov=app/routers/auth --cov=app/core/csrf
else
  # Run tests without coverage
  python -m pytest app/tests/test_auth_flows.py -v
fi

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}All authentication tests passed!${NC}"
else
  echo -e "${RED}Some tests failed. Please check the output above.${NC}"
  exit $TEST_EXIT_CODE
fi

# Verify CSRF token endpoint is working
echo -e "\n${BLUE}Verifying CSRF token endpoint...${NC}"
curl -s http://localhost:8000/auth/csrf-token | grep -q "csrf_token"

if [ $? -eq 0 ]; then
  echo -e "${GREEN}CSRF token endpoint is working correctly!${NC}"
else
  echo -e "${RED}CSRF token endpoint verification failed.${NC}"
  echo "Make sure the server is running."
  exit 1
fi

echo -e "\n${GREEN}Authentication module verification complete.${NC}"
exit 0 
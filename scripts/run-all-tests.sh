#!/bin/bash

# Set colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting FormIQ test suite...${NC}"

# Create directory for test results
results_dir="test-results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$results_dir"

cd /Users/tarpanmishra/formiq-app-5

# Function to run tests and capture results
run_tests() {
  test_type=$1
  command=$2
  
  echo -e "\n${YELLOW}Running $test_type tests...${NC}"
  
  # Run the tests and capture output
  start_time=$(date +%s)
  $command > "$results_dir/${test_type}_output.log" 2>&1
  exit_code=$?
  end_time=$(date +%s)
  duration=$((end_time - start_time))
  
  # Analyze results
  if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}$test_type tests completed successfully in ${duration}s!${NC}"
    echo "$test_type: PASS (${duration}s)" >> "$results_dir/summary.txt"
  else
    echo -e "${RED}$test_type tests failed with exit code $exit_code (${duration}s)${NC}"
    echo -e "${YELLOW}See $results_dir/${test_type}_output.log for details${NC}"
    echo "$test_type: FAIL (${duration}s) - Exit code: $exit_code" >> "$results_dir/summary.txt"
  fi
  
  return $exit_code
}

# Initialize summary file
echo "FormIQ Test Results - $(date)" > "$results_dir/summary.txt"
echo "===============================" >> "$results_dir/summary.txt"

# Track overall success
all_passed=true

# 1. Run frontend consolidated tests
if run_tests "frontend-consolidated" "cd frontend && npm run test:consolidated"; then
  # If tests pass, generate coverage report
  echo -e "${YELLOW}Generating frontend test coverage report...${NC}"
  cd frontend && npm run test:coverage:consolidated > "$results_dir/frontend_coverage.log" 2>&1
  cd ..
  
  # Copy coverage report to results directory
  mkdir -p "$results_dir/coverage/frontend"
  if [ -d "frontend/coverage" ]; then
    cp -R frontend/coverage/* "$results_dir/coverage/frontend/"
    echo -e "${GREEN}Frontend coverage report generated${NC}"
  else
    echo -e "${RED}Frontend coverage report not found${NC}"
  fi
else
  all_passed=false
fi

# 2. Run backend tests
if run_tests "backend" "cd backend && python -m pytest"; then
  # If tests pass, generate coverage report
  echo -e "${YELLOW}Generating backend test coverage report...${NC}"
  cd backend && python -m pytest --cov=app --cov-report=html:../test-results/coverage/backend > "$results_dir/backend_coverage.log" 2>&1
  cd ..
  
  echo -e "${GREEN}Backend coverage report generated${NC}"
else
  all_passed=false
fi

# 3. Run API integration tests if both frontend and backend passed
if [ "$all_passed" = true ]; then
  echo -e "${YELLOW}Running API integration tests...${NC}"
  if run_tests "api-integration" "cd backend && python -m pytest tests/integration"; then
    echo -e "${GREEN}API integration tests passed${NC}"
  else
    all_passed=false
  fi
else
  echo -e "${YELLOW}Skipping API integration tests due to previous failures${NC}"
  echo "api-integration: SKIPPED (due to previous failures)" >> "$results_dir/summary.txt"
fi

# Generate final summary
echo -e "\n${YELLOW}Test Summary:${NC}"
cat "$results_dir/summary.txt"

if [ "$all_passed" = true ]; then
  echo -e "\n${GREEN}All tests passed successfully!${NC}"
  exit 0
else
  echo -e "\n${RED}Some tests failed. See logs for details.${NC}"
  echo -e "${YELLOW}Test results saved to: $results_dir${NC}"
  exit 1
fi 
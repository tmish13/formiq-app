#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to check Python dependencies
check_dependencies() {
    print_header "Checking Python Dependencies"
    
    # Create and activate virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    
    # Install/update dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    pip install -r requirements-test.txt
    
    # Check for outdated packages
    local outdated=$(pip list --outdated)
    if [ ! -z "$outdated" ]; then
        echo -e "${YELLOW}Warning: Some packages are outdated:${NC}"
        echo "$outdated"
    fi
}

# Function to run linting
run_linting() {
    print_header "Running Linting"
    
    # Run flake8
    if ! flake8 .; then
        echo -e "${RED}Flake8 linting failed${NC}"
        return 1
    fi
    
    # Run black
    if ! black --check .; then
        echo -e "${RED}Black formatting check failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Linting passed${NC}"
    return 0
}

# Function to run type checking
run_type_checking() {
    print_header "Running Type Checking"
    
    if ! mypy .; then
        echo -e "${RED}Type checking failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Type checking passed${NC}"
    return 0
}

# Function to run unit tests
run_unit_tests() {
    print_header "Running Unit Tests"
    
    # Run tests with coverage
    if ! pytest --cov=app --cov-report=term-missing; then
        echo -e "${RED}Unit tests failed${NC}"
        return 1
    fi
    
    # Generate coverage report
    coverage html -d coverage_report
    
    echo -e "${GREEN}Unit tests passed${NC}"
    return 0
}

# Function to run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"
    
    # Start test database
    docker-compose -f docker-compose.test.yml up -d db
    
    # Wait for database to be ready
    sleep 5
    
    # Run integration tests
    if ! pytest tests/integration; then
        echo -e "${RED}Integration tests failed${NC}"
        docker-compose -f docker-compose.test.yml down
        return 1
    fi
    
    # Clean up
    docker-compose -f docker-compose.test.yml down
    
    echo -e "${GREEN}Integration tests passed${NC}"
    return 0
}

# Function to check API documentation
check_api_docs() {
    print_header "Checking API Documentation"
    
    # Generate OpenAPI schema
    if ! python -c "from app.main import app; from fastapi.openapi.utils import get_openapi; print(get_openapi(app.title, app.version, app.openapi_version, app.description))" > openapi.json; then
        echo -e "${RED}Failed to generate OpenAPI schema${NC}"
        return 1
    fi
    
    # Validate OpenAPI schema
    if ! swagger-cli validate openapi.json; then
        echo -e "${RED}OpenAPI schema validation failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}API documentation is valid${NC}"
    return 0
}

# Function to check security
check_security() {
    print_header "Checking Security"
    
    # Run bandit
    if ! bandit -r app/; then
        echo -e "${RED}Security check failed${NC}"
        return 1
    fi
    
    # Run safety
    if ! safety check; then
        echo -e "${RED}Safety check failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Security checks passed${NC}"
    return 0
}

# Function to verify environment variables
verify_env_vars() {
    print_header "Verifying Environment Variables"
    
    # Check required environment variables
    local required_vars=(
        "POSTGRES_SERVER"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "SECRET_KEY"
        "ENCRYPTION_KEY"
        "SMTP_HOST"
        "SMTP_USER"
        "SMTP_PASSWORD"
        "AWS_ACCESS_KEY_ID"
        "AWS_SECRET_ACCESS_KEY"
        "S3_BUCKET"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}Missing required environment variable: $var${NC}"
            return 1
        fi
    done
    
    echo -e "${GREEN}Environment variables verified${NC}"
    return 0
}

# Main backend setup process
main() {
    cd backend || exit 1
    
    # Check dependencies
    check_dependencies || exit 1
    
    # Run linting
    run_linting || exit 1
    
    # Run type checking
    run_type_checking || exit 1
    
    # Run unit tests
    run_unit_tests || exit 1
    
    # Run integration tests
    run_integration_tests || exit 1
    
    # Check API documentation
    check_api_docs || exit 1
    
    # Check security
    check_security || exit 1
    
    # Verify environment variables
    verify_env_vars || exit 1
    
    print_header "Backend Setup Complete"
    echo -e "${GREEN}All backend operations completed successfully!${NC}"
}

# Run main function
main 
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

# Function to check Node.js version
check_node_version() {
    print_header "Checking Node.js Version"
    
    local required_version="16.0.0"
    local current_version=$(node -v | cut -d'v' -f2)
    
    if ! command -v node &> /dev/null; then
        echo -e "${RED}Error: Node.js is not installed${NC}"
        return 1
    fi
    
    if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo -e "${RED}Error: Node.js version $current_version is lower than required version $required_version${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Node.js version $current_version meets requirements${NC}"
    return 0
}

# Function to check npm version
check_npm_version() {
    print_header "Checking npm Version"
    
    local required_version="7.0.0"
    local current_version=$(npm -v)
    
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}Error: npm is not installed${NC}"
        return 1
    fi
    
    if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
        echo -e "${RED}Error: npm version $current_version is lower than required version $required_version${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ npm version $current_version meets requirements${NC}"
    return 0
}

# Function to install dependencies
install_dependencies() {
    print_header "Installing Dependencies"
    
    # Clean install dependencies
    if npm ci; then
        echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        return 1
    fi
}

# Function to run linting
run_linting() {
    print_header "Running Linting"
    
    if npm run lint; then
        echo -e "${GREEN}✓ Linting passed successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Linting failed${NC}"
        return 1
    fi
}

# Function to run type checking
run_type_checking() {
    print_header "Running Type Checking"
    
    if npm run type-check; then
        echo -e "${GREEN}✓ Type checking passed successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Type checking failed${NC}"
        return 1
    fi
}

# Function to run tests
run_tests() {
    print_header "Running Tests"
    
    if npm run test; then
        echo -e "${GREEN}✓ Tests passed successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Tests failed${NC}"
        return 1
    fi
}

# Function to build the application
build_application() {
    print_header "Building Application"
    
    if npm run build; then
        echo -e "${GREEN}✓ Application built successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Build failed${NC}"
        return 1
    fi
}

# Function to verify build output
verify_build_output() {
    print_header "Verifying Build Output"
    
    local build_dir="build"
    local required_files=("index.html" "static/js/main.*.js" "static/css/main.*.css")
    
    for file in "${required_files[@]}"; do
        if ! ls $build_dir/$file 1> /dev/null 2>&1; then
            echo -e "${RED}Error: Required file $file not found in build output${NC}"
            return 1
        fi
    done
    
    echo -e "${GREEN}✓ Build output verified successfully${NC}"
    return 0
}

# Function to optimize assets
optimize_assets() {
    print_header "Optimizing Assets"
    
    # Optimize images
    if npm run optimize-images; then
        echo -e "${GREEN}✓ Images optimized successfully${NC}"
    else
        echo -e "${RED}Error: Image optimization failed${NC}"
        return 1
    fi
    
    # Compress static files
    if npm run compress-static; then
        echo -e "${GREEN}✓ Static files compressed successfully${NC}"
    else
        echo -e "${RED}Error: Static file compression failed${NC}"
        return 1
    fi
    
    return 0
}

# Function to generate source maps
generate_source_maps() {
    print_header "Generating Source Maps"
    
    if npm run generate-source-maps; then
        echo -e "${GREEN}✓ Source maps generated successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Source map generation failed${NC}"
        return 1
    fi
}

# Main function
main() {
    print_header "Starting Frontend Setup"
    
    local errors=0
    
    # Run frontend setup steps
    check_node_version || ((errors++))
    check_npm_version || ((errors++))
    install_dependencies || ((errors++))
    run_linting || ((errors++))
    run_type_checking || ((errors++))
    run_tests || ((errors++))
    build_application || ((errors++))
    verify_build_output || ((errors++))
    optimize_assets || ((errors++))
    generate_source_maps || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Frontend Setup Complete"
        echo -e "${GREEN}All frontend setup steps completed successfully!${NC}"
        return 0
    else
        print_header "Frontend Setup Failed"
        echo -e "${RED}Found $errors issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
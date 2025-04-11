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

# Function to check if a command exists
check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}Error: $cmd is not installed${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $cmd is installed${NC}"
    return 0
}

# Function to check for security headers
check_security_headers() {
    print_header "Checking Security Headers"
    
    local url="https://formiq-app.com"
    local headers=$(curl -sI "$url")
    
    local required_headers=(
        "Strict-Transport-Security"
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Content-Security-Policy"
    )
    
    local missing_headers=0
    for header in "${required_headers[@]}"; do
        if ! echo "$headers" | grep -q "$header"; then
            echo -e "${RED}Error: Missing security header: $header${NC}"
            ((missing_headers++))
        fi
    done
    
    if [ $missing_headers -gt 0 ]; then
        echo -e "${RED}Error: $missing_headers security headers are missing${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ All required security headers are present${NC}"
    return 0
}

# Function to check SSL configuration
check_ssl_config() {
    print_header "Checking SSL Configuration"
    
    local url="https://formiq-app.com"
    local ssl_info=$(openssl s_client -connect formiq-app.com:443 -servername formiq-app.com 2>/dev/null)
    
    # Check SSL protocol version
    if echo "$ssl_info" | grep -q "Protocol  : TLSv1.3"; then
        echo -e "${GREEN}✓ Using TLS 1.3${NC}"
    else
        echo -e "${RED}Error: Not using TLS 1.3${NC}"
        return 1
    fi
    
    # Check cipher suites
    if echo "$ssl_info" | grep -q "ECDHE"; then
        echo -e "${GREEN}✓ Using strong cipher suites${NC}"
    else
        echo -e "${RED}Error: Not using strong cipher suites${NC}"
        return 1
    fi
    
    return 0
}

# Function to check dependencies for vulnerabilities
check_dependencies() {
    print_header "Checking Dependencies"
    
    # Check Python dependencies
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${YELLOW}Checking Python dependencies...${NC}"
        if ! safety check -r backend/requirements.txt; then
            echo -e "${RED}Error: Vulnerabilities found in Python dependencies${NC}"
            return 1
        fi
    fi
    
    # Check Node.js dependencies
    if [ -f "frontend/package.json" ]; then
        echo -e "${YELLOW}Checking Node.js dependencies...${NC}"
        if ! npm audit; then
            echo -e "${RED}Error: Vulnerabilities found in Node.js dependencies${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}✓ No vulnerabilities found in dependencies${NC}"
    return 0
}

# Function to check for sensitive data exposure
check_sensitive_data() {
    print_header "Checking for Sensitive Data Exposure"
    
    local patterns=(
        "API_KEY"
        "SECRET_KEY"
        "PASSWORD"
        "PRIVATE_KEY"
        "AWS_ACCESS_KEY"
        "AWS_SECRET_KEY"
    )
    
    local found_sensitive=0
    for pattern in "${patterns[@]}"; do
        local matches=$(grep -r --include="*.{py,js,json,yml,yaml,env}" "$pattern" .)
        if [ ! -z "$matches" ]; then
            echo -e "${RED}Error: Found potential sensitive data pattern: $pattern${NC}"
            echo "$matches"
            ((found_sensitive++))
        fi
    done
    
    if [ $found_sensitive -gt 0 ]; then
        echo -e "${RED}Error: Found $found_sensitive instances of potential sensitive data exposure${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ No sensitive data exposure found${NC}"
    return 0
}

# Function to check file permissions
check_file_permissions() {
    print_header "Checking File Permissions"
    
    local sensitive_files=(
        "backend/.env.production"
        "frontend/.env.production"
        "infrastructure/docker/nginx/ssl/*.key"
    )
    
    local incorrect_permissions=0
    for file in "${sensitive_files[@]}"; do
        for f in $file; do
            if [ -f "$f" ]; then
                local perms=$(stat -f "%OLp" "$f")
                if [ "$perms" != "600" ]; then
                    echo -e "${RED}Error: Incorrect permissions on $f: $perms${NC}"
                    ((incorrect_permissions++))
                fi
            fi
        done
    done
    
    if [ $incorrect_permissions -gt 0 ]; then
        echo -e "${RED}Error: Found $incorrect_permissions files with incorrect permissions${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ All file permissions are correct${NC}"
    return 0
}

# Function to check for outdated packages
check_outdated_packages() {
    print_header "Checking for Outdated Packages"
    
    # Check Python packages
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${YELLOW}Checking Python packages...${NC}"
        pip list --outdated
    fi
    
    # Check Node.js packages
    if [ -f "frontend/package.json" ]; then
        echo -e "${YELLOW}Checking Node.js packages...${NC}"
        npm outdated
    fi
    
    return 0
}

# Main function
main() {
    print_header "Starting Security Check"
    
    local errors=0
    
    # Run security checks
    check_security_headers || ((errors++))
    check_ssl_config || ((errors++))
    check_dependencies || ((errors++))
    check_sensitive_data || ((errors++))
    check_file_permissions || ((errors++))
    check_outdated_packages || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Security Check Complete"
        echo -e "${GREEN}All security checks passed successfully!${NC}"
        return 0
    else
        print_header "Security Check Failed"
        echo -e "${RED}Found $errors security issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
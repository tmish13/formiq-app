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

# Function to run load testing
run_load_test() {
    print_header "Running Load Test"
    
    local url="https://formiq-app.com"
    local duration=300  # 5 minutes
    local users=100
    
    echo -e "${YELLOW}Starting load test with $users users for $duration seconds...${NC}"
    
    if ! locust --host="$url" --users="$users" --spawn-rate=10 --run-time="${duration}s" --headless; then
        echo -e "${RED}Error: Load test failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Load test completed successfully${NC}"
    return 0
}

# Function to run stress testing
run_stress_test() {
    print_header "Running Stress Test"
    
    local url="https://formiq-app.com"
    local duration=600  # 10 minutes
    local users=500
    
    echo -e "${YELLOW}Starting stress test with $users users for $duration seconds...${NC}"
    
    if ! locust --host="$url" --users="$users" --spawn-rate=50 --run-time="${duration}s" --headless; then
        echo -e "${RED}Error: Stress test failed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Stress test completed successfully${NC}"
    return 0
}

# Function to check API response times
check_api_response_times() {
    print_header "Checking API Response Times"
    
    local endpoints=(
        "/api/health"
        "/api/users"
        "/api/products"
        "/api/orders"
    )
    
    local base_url="https://formiq-app.com"
    local total_time=0
    local count=0
    
    for endpoint in "${endpoints[@]}"; do
        local start_time=$(date +%s.%N)
        local response=$(curl -s -w "%{http_code}" "$base_url$endpoint" -o /dev/null)
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        
        if [ "$response" -eq 200 ]; then
            echo -e "${GREEN}✓ $endpoint: ${duration}s${NC}"
            total_time=$(echo "$total_time + $duration" | bc)
            ((count++))
        else
            echo -e "${RED}Error: $endpoint returned status $response${NC}"
            return 1
        fi
    done
    
    local avg_time=$(echo "scale=3; $total_time / $count" | bc)
    echo -e "${GREEN}Average response time: ${avg_time}s${NC}"
    
    if (( $(echo "$avg_time > 1.0" | bc -l) )); then
        echo -e "${RED}Warning: Average response time is above 1 second${NC}"
        return 1
    fi
    
    return 0
}

# Function to check database performance
check_database_performance() {
    print_header "Checking Database Performance"
    
    local queries=(
        "SELECT COUNT(*) FROM users;"
        "SELECT COUNT(*) FROM products;"
        "SELECT COUNT(*) FROM orders;"
    )
    
    for query in "${queries[@]}"; do
        local start_time=$(date +%s.%N)
        if ! docker-compose exec -T db psql -U postgres -d formiq -c "$query" > /dev/null; then
            echo -e "${RED}Error: Database query failed${NC}"
            return 1
        fi
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        
        echo -e "${GREEN}✓ Query executed in ${duration}s${NC}"
        
        if (( $(echo "$duration > 0.5" | bc -l) )); then
            echo -e "${RED}Warning: Query execution time is above 0.5 seconds${NC}"
            return 1
        fi
    done
    
    return 0
}

# Function to check frontend performance
check_frontend_performance() {
    print_header "Checking Frontend Performance"
    
    local url="https://formiq-app.com"
    local metrics=$(curl -s "https://www.webpagetest.org/runtest.php?url=$url&f=json&k=YOUR_API_KEY")
    
    # Check First Contentful Paint
    local fcp=$(echo "$metrics" | jq -r '.data.median.firstView.firstContentfulPaint')
    if [ "$fcp" -gt 1000 ]; then
        echo -e "${RED}Warning: First Contentful Paint is above 1 second: ${fcp}ms${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ First Contentful Paint: ${fcp}ms${NC}"
    
    # Check Time to Interactive
    local tti=$(echo "$metrics" | jq -r '.data.median.firstView.TimeToInteractive')
    if [ "$tti" -gt 3000 ]; then
        echo -e "${RED}Warning: Time to Interactive is above 3 seconds: ${tti}ms${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Time to Interactive: ${tti}ms${NC}"
    
    return 0
}

# Function to optimize assets
optimize_assets() {
    print_header "Optimizing Assets"
    
    # Optimize images
    if command -v imagemin >/dev/null 2>&1; then
        echo -e "${YELLOW}Optimizing images...${NC}"
        imagemin frontend/build/**/*.{jpg,png,gif,svg} --out-dir=frontend/build
    fi
    
    # Minify CSS
    if command -v cleancss >/dev/null 2>&1; then
        echo -e "${YELLOW}Minifying CSS...${NC}"
        cleancss -o frontend/build/**/*.min.css frontend/build/**/*.css
    fi
    
    # Minify JavaScript
    if command -v uglifyjs >/dev/null 2>&1; then
        echo -e "${YELLOW}Minifying JavaScript...${NC}"
        uglifyjs frontend/build/**/*.js -o frontend/build/**/*.min.js
    fi
    
    echo -e "${GREEN}✓ Asset optimization completed${NC}"
    return 0
}

# Main function
main() {
    print_header "Starting Performance Test"
    
    local errors=0
    
    # Run performance tests
    run_load_test || ((errors++))
    run_stress_test || ((errors++))
    check_api_response_times || ((errors++))
    check_database_performance || ((errors++))
    check_frontend_performance || ((errors++))
    optimize_assets || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Performance Test Complete"
        echo -e "${GREEN}All performance tests passed successfully!${NC}"
        return 0
    else
        print_header "Performance Test Failed"
        echo -e "${RED}Found $errors performance issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
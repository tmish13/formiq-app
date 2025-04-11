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
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a command and check its exit status
run_command() {
    local cmd=$1
    local error_msg=$2
    
    if ! eval "$cmd"; then
        echo -e "${RED}Error: $error_msg${NC}"
        return 1
    fi
    return 0
}

# Main setup process
main() {
    print_header "Setting Up Monitoring"
    
    # Check if cron is installed
    if ! command_exists "cron"; then
        echo -e "${RED}Cron is not installed. Please install cron to set up monitoring.${NC}"
        exit 1
    fi
    
    # Make monitoring script executable
    echo "Making monitoring script executable..."
    run_command "chmod +x scripts/monitor.sh" "Failed to make monitoring script executable" || exit 1
    
    # Create log directory if it doesn't exist
    echo "Creating log directory..."
    run_command "mkdir -p logs" "Failed to create log directory" || exit 1
    
    # Set up cron job for monitoring
    echo "Setting up cron job for monitoring..."
    
    # Check if the cron job already exists
    if crontab -l 2>/dev/null | grep -q "scripts/monitor.sh"; then
        echo -e "${YELLOW}Monitoring cron job already exists.${NC}"
    else
        # Add the cron job to run every 5 minutes
        (crontab -l 2>/dev/null; echo "*/5 * * * * cd $(pwd) && ./scripts/monitor.sh >> logs/cron.log 2>&1") | crontab -
        echo -e "${GREEN}Monitoring cron job added successfully.${NC}"
    fi
    
    # Set up log rotation for monitoring logs
    echo "Setting up log rotation..."
    
    # Create logrotate configuration
    cat > /etc/logrotate.d/formiq-monitor << EOF
$(pwd)/logs/monitor.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $(whoami) $(whoami)
}

$(pwd)/logs/alerts.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $(whoami) $(whoami)
}

$(pwd)/logs/cron.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $(whoami) $(whoami)
}
EOF
    
    echo -e "${GREEN}Log rotation configured successfully.${NC}"
    
    # Test the monitoring script
    echo "Testing monitoring script..."
    run_command "./scripts/monitor.sh" "Monitoring script test failed" || exit 1
    
    print_header "Monitoring Setup Complete"
    echo -e "${GREEN}Monitoring has been set up successfully!${NC}"
    echo -e "${YELLOW}The monitoring script will run every 5 minutes.${NC}"
    echo -e "${YELLOW}Logs will be stored in the logs directory.${NC}"
    echo -e "${YELLOW}Alerts will be sent to $ALERT_EMAIL and Slack.${NC}"
}

# Run main function
main 
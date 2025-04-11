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

# Function to setup logging directories
setup_logging_dirs() {
    print_header "Setting Up Logging Directories"
    
    local log_dirs=(
        "logs/application"
        "logs/nginx"
        "logs/database"
        "logs/monitoring"
    )
    
    for dir in "${log_dirs[@]}"; do
        if mkdir -p "$dir"; then
            echo -e "${GREEN}✓ Created directory: $dir${NC}"
        else
            echo -e "${RED}Error: Failed to create directory: $dir${NC}"
            return 1
        fi
    done
    
    return 0
}

# Function to setup log rotation
setup_log_rotation() {
    print_header "Setting Up Log Rotation"
    
    local logrotate_conf="/etc/logrotate.d/formiq"
    
    if [ ! -f "$logrotate_conf" ]; then
        echo -e "${YELLOW}Creating logrotate configuration...${NC}"
        
        cat > "$logrotate_conf" << EOF
/logs/*/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        /usr/bin/systemctl reload nginx >/dev/null 2>&1 || true
    endscript
}
EOF
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Logrotate configuration created${NC}"
        else
            echo -e "${RED}Error: Failed to create logrotate configuration${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✓ Logrotate configuration already exists${NC}"
    fi
    
    return 0
}

# Function to setup monitoring
setup_monitoring() {
    print_header "Setting Up Monitoring"
    
    # Check if Prometheus is installed
    if ! check_command "prometheus"; then
        echo -e "${YELLOW}Installing Prometheus...${NC}"
        # Add your Prometheus installation commands here
    fi
    
    # Check if Grafana is installed
    if ! check_command "grafana-server"; then
        echo -e "${YELLOW}Installing Grafana...${NC}"
        # Add your Grafana installation commands here
    fi
    
    # Setup monitoring configuration
    local prometheus_conf="infrastructure/monitoring/prometheus/prometheus.yml"
    local grafana_conf="infrastructure/monitoring/grafana/grafana.ini"
    
    # Create Prometheus configuration
    mkdir -p "$(dirname "$prometheus_conf")"
    cat > "$prometheus_conf" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'formiq'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
EOF
    
    # Create Grafana configuration
    mkdir -p "$(dirname "$grafana_conf")"
    cat > "$grafana_conf" << EOF
[server]
http_port = 3000
domain = localhost

[security]
admin_user = admin
admin_password = admin

[auth.anonymous]
enabled = true
org_role = Viewer
EOF
    
    echo -e "${GREEN}✓ Monitoring configuration created${NC}"
    return 0
}

# Function to setup alerting
setup_alerting() {
    print_header "Setting Up Alerting"
    
    local alertmanager_conf="infrastructure/monitoring/alertmanager/alertmanager.yml"
    
    # Create Alertmanager configuration
    mkdir -p "$(dirname "$alertmanager_conf")"
    cat > "$alertmanager_conf" << EOF
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email-notifications'

receivers:
- name: 'email-notifications'
  email_configs:
  - to: 'admin@formiq-app.com'
    from: 'alertmanager@formiq-app.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alertmanager@formiq-app.com'
    auth_password: 'your-password'
EOF
    
    echo -e "${GREEN}✓ Alerting configuration created${NC}"
    return 0
}

# Function to verify monitoring setup
verify_monitoring() {
    print_header "Verifying Monitoring Setup"
    
    # Check if Prometheus is running
    if systemctl is-active --quiet prometheus; then
        echo -e "${GREEN}✓ Prometheus is running${NC}"
    else
        echo -e "${RED}Error: Prometheus is not running${NC}"
        return 1
    fi
    
    # Check if Grafana is running
    if systemctl is-active --quiet grafana-server; then
        echo -e "${GREEN}✓ Grafana is running${NC}"
    else
        echo -e "${RED}Error: Grafana is not running${NC}"
        return 1
    fi
    
    # Check if Alertmanager is running
    if systemctl is-active --quiet alertmanager; then
        echo -e "${GREEN}✓ Alertmanager is running${NC}"
    else
        echo -e "${RED}Error: Alertmanager is not running${NC}"
        return 1
    fi
    
    return 0
}

# Main function
main() {
    print_header "Starting Monitoring Setup"
    
    local errors=0
    
    # Run monitoring setup steps
    setup_logging_dirs || ((errors++))
    setup_log_rotation || ((errors++))
    setup_monitoring || ((errors++))
    setup_alerting || ((errors++))
    verify_monitoring || ((errors++))
    
    if [ $errors -eq 0 ]; then
        print_header "Monitoring Setup Complete"
        echo -e "${GREEN}All monitoring operations completed successfully!${NC}"
        return 0
    else
        print_header "Monitoring Setup Failed"
        echo -e "${RED}Found $errors issues that need to be resolved${NC}"
        return 1
    fi
}

# Run main function
main 
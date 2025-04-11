#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Monitoring configuration
LOG_FILE="monitor.log"
ALERT_LOG="alerts.log"
CHECK_INTERVAL=300  # 5 minutes
ALERT_THRESHOLD=3   # Number of consecutive failures before alerting
MAX_RETRIES=3       # Number of retries for each check

# Alert configuration
ALERT_EMAIL="admin@formiq-app.com"
ALERT_SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to log messages
log_message() {
    local message=$1
    local level=${2:-INFO}
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
    echo -e "$message"
}

# Function to log alerts
log_alert() {
    local message=$1
    local severity=${2:-WARNING}
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$severity] ALERT: $message" >> "$ALERT_LOG"
    echo -e "${RED}ALERT: $message${NC}"
    
    # Send alert via email
    echo "$message" | mail -s "[$severity] Formiq App Alert" "$ALERT_EMAIL"
    
    # Send alert via Slack
    curl -s -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"[$severity] $message\"}" \
        "$ALERT_SLACK_WEBHOOK"
}

# Function to check system resources
check_system_resources() {
    print_header "Checking System Resources"
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        log_alert "High CPU usage: $cpu_usage%" "WARNING"
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        log_alert "High memory usage: $memory_usage%" "WARNING"
    fi
    
    # Check disk usage
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        log_alert "High disk usage: $disk_usage%" "WARNING"
    fi
    
    log_message "System resource check completed"
}

# Function to check Docker services
check_docker_services() {
    print_header "Checking Docker Services"
    
    # Check if all services are running
    local services_down=$(docker-compose -f docker-compose.prod.yml ps | grep -v "Up" | wc -l)
    if [ "$services_down" -gt 0 ]; then
        log_alert "Some Docker services are not running" "ERROR"
        docker-compose -f docker-compose.prod.yml ps >> "$LOG_FILE"
    fi
    
    # Check Docker container health
    local unhealthy_containers=$(docker ps --filter "health=unhealthy" | wc -l)
    if [ "$unhealthy_containers" -gt 1 ]; then  # 1 because header line is counted
        log_alert "Some Docker containers are unhealthy" "ERROR"
        docker ps --filter "health=unhealthy" >> "$LOG_FILE"
    fi
    
    log_message "Docker service check completed"
}

# Function to check API health
check_api_health() {
    print_header "Checking API Health"
    
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $MAX_RETRIES ] && [ "$success" = false ]; do
        if curl -s http://localhost:8000/health | grep -q "healthy"; then
            success=true
            log_message "API is healthy" "SUCCESS"
        else
            retry_count=$((retry_count + 1))
            log_message "API health check failed (attempt $retry_count/$MAX_RETRIES)" "WARNING"
            sleep 5
        fi
    done
    
    if [ "$success" = false ]; then
        log_alert "API health check failed after $MAX_RETRIES attempts" "ERROR"
    fi
}

# Function to check frontend health
check_frontend_health() {
    print_header "Checking Frontend Health"
    
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $MAX_RETRIES ] && [ "$success" = false ]; do
        if curl -s http://localhost:3000/health | grep -q "healthy"; then
            success=true
            log_message "Frontend is healthy" "SUCCESS"
        else
            retry_count=$((retry_count + 1))
            log_message "Frontend health check failed (attempt $retry_count/$MAX_RETRIES)" "WARNING"
            sleep 5
        fi
    done
    
    if [ "$success" = false ]; then
        log_alert "Frontend health check failed after $MAX_RETRIES attempts" "ERROR"
    fi
}

# Function to check nginx health
check_nginx_health() {
    print_header "Checking Nginx Health"
    
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $MAX_RETRIES ] && [ "$success" = false ]; do
        if curl -s -k https://localhost/health | grep -q "healthy"; then
            success=true
            log_message "Nginx is healthy" "SUCCESS"
        else
            retry_count=$((retry_count + 1))
            log_message "Nginx health check failed (attempt $retry_count/$MAX_RETRIES)" "WARNING"
            sleep 5
        fi
    done
    
    if [ "$success" = false ]; then
        log_alert "Nginx health check failed after $MAX_RETRIES attempts" "ERROR"
    fi
}

# Function to check database health
check_database_health() {
    print_header "Checking Database Health"
    
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $MAX_RETRIES ] && [ "$success" = false ]; do
        if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres; then
            success=true
            log_message "Database is healthy" "SUCCESS"
        else
            retry_count=$((retry_count + 1))
            log_message "Database health check failed (attempt $retry_count/$MAX_RETRIES)" "WARNING"
            sleep 5
        fi
    done
    
    if [ "$success" = false ]; then
        log_alert "Database health check failed after $MAX_RETRIES attempts" "ERROR"
    fi
}

# Function to check SSL certificates
check_ssl_certificates() {
    print_header "Checking SSL Certificates"
    
    local domains=("api.formiq-app.com" "formiq-app.com")
    local cert_files=("infrastructure/docker/nginx/ssl/api.formiq-app.com.crt" "infrastructure/docker/nginx/ssl/formiq-app.com.crt")
    
    for i in "${!domains[@]}"; do
        local domain="${domains[$i]}"
        local cert_file="${cert_files[$i]}"
        
        if [ ! -f "$cert_file" ]; then
            log_alert "SSL certificate not found for $domain" "ERROR"
            continue
        fi
        
        # Check certificate expiration
        local expiry_date
        local now_epoch
        local expiry_epoch
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d'=' -f2)
            expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s)
            now_epoch=$(date +%s)
        else
            expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d'=' -f2)
            expiry_epoch=$(date --date="$expiry_date" +%s)
            now_epoch=$(date +%s)
        fi
        
        local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))
        
        if [ $days_left -lt 30 ]; then
            log_alert "SSL certificate for $domain expires in $days_left days" "WARNING"
        else
            log_message "SSL certificate for $domain is valid for $days_left days" "SUCCESS"
        fi
    done
}

# Function to check backup system
check_backup_system() {
    print_header "Checking Backup System"
    
    # Check if backup directory exists
    if [ ! -d "backups" ]; then
        log_alert "Backup directory does not exist" "ERROR"
        return 1
    fi
    
    # Check if there are any backups
    local backup_count=$(ls -1 backups | wc -l)
    if [ "$backup_count" -eq 0 ]; then
        log_alert "No backups found" "WARNING"
        return 1
    fi
    
    # Check if the latest backup is recent (within 24 hours)
    local latest_backup=$(ls -1t backups | head -1)
    local backup_time=$(stat -f "%m" "backups/$latest_backup" 2>/dev/null || stat -c "%Y" "backups/$latest_backup")
    local now=$(date +%s)
    local hours_since_backup=$(( ($now - $backup_time) / 3600 ))
    
    if [ $hours_since_backup -gt 24 ]; then
        log_alert "Latest backup is $hours_since_backup hours old" "WARNING"
    else
        log_message "Latest backup is $hours_since_backup hours old" "SUCCESS"
    fi
}

# Function to check for security issues
check_security() {
    print_header "Checking Security"
    
    # Check for open ports
    local open_ports=$(netstat -tuln | grep LISTEN | awk '{print $4}' | cut -d':' -f2)
    for port in $open_ports; do
        if [[ ! "$port" =~ ^(80|443|8000|3000)$ ]]; then
            log_alert "Unexpected open port: $port" "WARNING"
        fi
    done
    
    # Check for failed login attempts
    local failed_logins=$(grep "Failed password" /var/log/auth.log 2>/dev/null || grep "Failed password" /var/log/secure 2>/dev/null | wc -l)
    if [ "$failed_logins" -gt 10 ]; then
        log_alert "High number of failed login attempts: $failed_logins" "WARNING"
    fi
    
    log_message "Security check completed"
}

# Function to generate monitoring report
generate_report() {
    print_header "Generating Monitoring Report"
    
    local report_file="monitoring_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Formiq App Monitoring Report"
        echo "Generated on: $(date)"
        echo "----------------------------------------"
        echo ""
        
        echo "System Resources:"
        echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
        echo "Memory Usage: $(free | grep Mem | awk '{print $3/$2 * 100.0}')%"
        echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"
        echo ""
        
        echo "Docker Services:"
        docker-compose -f docker-compose.prod.yml ps
        echo ""
        
        echo "API Health:"
        curl -s http://localhost:8000/health
        echo ""
        
        echo "Frontend Health:"
        curl -s http://localhost:3000/health
        echo ""
        
        echo "Nginx Health:"
        curl -s -k https://localhost/health
        echo ""
        
        echo "Database Health:"
        docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres
        echo ""
        
        echo "SSL Certificates:"
        for cert_file in infrastructure/docker/nginx/ssl/*.crt; do
            echo "Certificate: $cert_file"
            openssl x509 -in "$cert_file" -noout -subject -issuer -dates
            echo ""
        done
        
        echo "Backup Status:"
        ls -lh backups
        echo ""
        
        echo "Recent Alerts:"
        tail -n 10 "$ALERT_LOG"
    } > "$report_file"
    
    log_message "Monitoring report generated: $report_file" "SUCCESS"
}

# Main monitoring process
main() {
    print_header "Starting Monitoring"
    
    # Initialize failure counters
    local api_failures=0
    local frontend_failures=0
    local nginx_failures=0
    local db_failures=0
    
    # Run monitoring checks
    check_system_resources
    check_docker_services
    check_api_health || api_failures=$((api_failures + 1))
    check_frontend_health || frontend_failures=$((frontend_failures + 1))
    check_nginx_health || nginx_failures=$((nginx_failures + 1))
    check_database_health || db_failures=$((db_failures + 1))
    check_ssl_certificates
    check_backup_system
    check_security
    
    # Generate report
    generate_report
    
    # Check for persistent failures
    if [ $api_failures -ge $ALERT_THRESHOLD ]; then
        log_alert "API has failed $api_failures consecutive health checks" "ERROR"
    fi
    
    if [ $frontend_failures -ge $ALERT_THRESHOLD ]; then
        log_alert "Frontend has failed $frontend_failures consecutive health checks" "ERROR"
    fi
    
    if [ $nginx_failures -ge $ALERT_THRESHOLD ]; then
        log_alert "Nginx has failed $nginx_failures consecutive health checks" "ERROR"
    fi
    
    if [ $db_failures -ge $ALERT_THRESHOLD ]; then
        log_alert "Database has failed $db_failures consecutive health checks" "ERROR"
    fi
    
    print_header "Monitoring Complete"
    log_message "Monitoring cycle completed successfully" "SUCCESS"
}

# Run main function
main 
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
CHECK_INTERVAL=300  # 5 minutes
LOG_FILE="deployment_monitor.log"
ALERT_EMAIL="admin@formiq-app.com"
MAX_RETRIES=3
THRESHOLD_CPU=80
THRESHOLD_MEMORY=85
THRESHOLD_DISK=90

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to log messages
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Function to send alerts
send_alert() {
    local subject=$1
    local message=$2
    echo "$message" | mail -s "$subject" "$ALERT_EMAIL"
    log_message "ALERT" "Alert sent: $subject"
}

# Function to check system resources
check_resources() {
    print_header "Checking System Resources"
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    if [ "${cpu_usage%.*}" -gt "$THRESHOLD_CPU" ]; then
        send_alert "High CPU Usage Alert" "CPU usage is at ${cpu_usage}%"
        log_message "WARNING" "High CPU usage detected: ${cpu_usage}%"
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    if [ "${memory_usage%.*}" -gt "$THRESHOLD_MEMORY" ]; then
        send_alert "High Memory Usage Alert" "Memory usage is at ${memory_usage}%"
        log_message "WARNING" "High memory usage detected: ${memory_usage}%"
    fi
    
    # Check disk usage
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt "$THRESHOLD_DISK" ]; then
        send_alert "High Disk Usage Alert" "Disk usage is at ${disk_usage}%"
        log_message "WARNING" "High disk usage detected: ${disk_usage}%"
    fi
}

# Function to check service health
check_services() {
    print_header "Checking Service Health"
    
    local services=("frontend" "backend" "database" "nginx")
    local unhealthy_services=()
    
    for service in "${services[@]}"; do
        if ! docker-compose ps "$service" | grep -q "Up"; then
            unhealthy_services+=("$service")
            log_message "ERROR" "Service $service is not running"
        fi
    done
    
    if [ ${#unhealthy_services[@]} -gt 0 ]; then
        send_alert "Service Health Alert" "The following services are not running: ${unhealthy_services[*]}"
    fi
}

# Function to check API health
check_api() {
    print_header "Checking API Health"
    
    local endpoints=(
        "/health"
        "/auth/login"
        "/users/me"
        "/forms"
        "/submissions"
    )
    
    local failed_endpoints=()
    
    for endpoint in "${endpoints[@]}"; do
        local retries=0
        local success=false
        
        while [ $retries -lt $MAX_RETRIES ] && [ "$success" = false ]; do
            if curl -s -o /dev/null -w "%{http_code}" "https://formiq-app.com/api$endpoint" | grep -q "200\|401"; then
                success=true
            else
                ((retries++))
                sleep 5
            fi
        done
        
        if [ "$success" = false ]; then
            failed_endpoints+=("$endpoint")
            log_message "ERROR" "API endpoint $endpoint is not responding"
        fi
    done
    
    if [ ${#failed_endpoints[@]} -gt 0 ]; then
        send_alert "API Health Alert" "The following endpoints are not responding: ${failed_endpoints[*]}"
    fi
}

# Function to check database health
check_database() {
    print_header "Checking Database Health"
    
    # Check connection
    if ! docker-compose exec -T database pg_isready -U postgres; then
        send_alert "Database Health Alert" "Database is not accepting connections"
        log_message "ERROR" "Database connection failed"
        return 1
    fi
    
    # Check replication lag
    local replication_lag=$(docker-compose exec -T database psql -U postgres -t -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::INT" 2>/dev/null)
    if [ -n "$replication_lag" ] && [ "$replication_lag" -gt 300 ]; then
        send_alert "Database Replication Alert" "Replication lag is ${replication_lag} seconds"
        log_message "WARNING" "High replication lag detected: ${replication_lag}s"
    fi
    
    # Check table sizes
    local large_tables=$(docker-compose exec -T database psql -U postgres -t -c "
        SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname|| '.' ||tablename)) as size
        FROM pg_tables
        WHERE pg_total_relation_size(schemaname|| '.' ||tablename) > 1000000000
        ORDER BY pg_total_relation_size(schemaname|| '.' ||tablename) DESC;
    " 2>/dev/null)
    
    if [ -n "$large_tables" ]; then
        log_message "WARNING" "Large tables detected:\n$large_tables"
    fi
}

# Function to check SSL certificates
check_ssl() {
    print_header "Checking SSL Certificates"
    
    local domain="formiq-app.com"
    local cert_file="/etc/nginx/ssl/$domain.crt"
    
    if [ -f "$cert_file" ]; then
        local expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry_date" +%s)
        local current_epoch=$(date +%s)
        local days_remaining=$(( ($expiry_epoch - $current_epoch) / 86400 ))
        
        if [ "$days_remaining" -lt 30 ]; then
            send_alert "SSL Certificate Alert" "SSL certificate for $domain expires in $days_remaining days"
            log_message "WARNING" "SSL certificate expires in $days_remaining days"
        fi
    else
        send_alert "SSL Certificate Alert" "SSL certificate file not found"
        log_message "ERROR" "SSL certificate file missing"
    fi
}

# Function to check backup status
check_backups() {
    print_header "Checking Backup Status"
    
    local backup_types=("database" "env" "ssl" "app")
    local missing_backups=()
    
    for type in "${backup_types[@]}"; do
        if ! find "backups" -type f -name "*.$type*" -mtime -1 | grep -q .; then
            missing_backups+=("$type")
            log_message "ERROR" "No recent $type backup found"
        fi
    done
    
    if [ ${#missing_backups[@]} -gt 0 ]; then
        send_alert "Backup Alert" "Missing recent backups for: ${missing_backups[*]}"
    fi
}

# Function to check log files
check_logs() {
    print_header "Checking Log Files"
    
    local error_patterns=(
        "ERROR"
        "CRITICAL"
        "Exception"
        "Failed"
        "Timeout"
    )
    
    for pattern in "${error_patterns[@]}"; do
        local error_count=$(docker-compose logs --tail=1000 | grep -c "$pattern")
        if [ "$error_count" -gt 10 ]; then
            send_alert "Log Alert" "High number of $pattern messages in logs"
            log_message "WARNING" "Found $error_count $pattern messages in recent logs"
        fi
    done
}

# Main monitoring loop
main() {
    print_header "Starting Deployment Monitoring"
    log_message "INFO" "Monitoring started"
    
    while true; do
        check_resources
        check_services
        check_api
        check_database
        check_ssl
        check_backups
        check_logs
        
        log_message "INFO" "Monitoring cycle completed"
        sleep "$CHECK_INTERVAL"
    done
}

# Run main function
main 
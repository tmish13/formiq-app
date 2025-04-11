#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOCS_DIR="docs"
REQUIRED_DOCS=(
    "deployment-guide.md"
    "api-documentation.md"
    "database-schema.md"
    "environment-variables.md"
    "monitoring-guide.md"
    "rollback-procedures.md"
    "security-guide.md"
    "troubleshooting-guide.md"
)

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}=== $1 ===${NC}\n"
}

# Function to check if a file exists
check_file() {
    local file=$1
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
        return 0
    else
        echo -e "${RED}✗${NC} $file"
        return 1
    fi
}

# Function to generate deployment guide
generate_deployment_guide() {
    print_header "Generating Deployment Guide"
    
    cat > "$DOCS_DIR/deployment-guide.md" << EOF
# Deployment Guide

## Prerequisites
- Docker and Docker Compose
- Node.js and npm
- Python 3.8+
- PostgreSQL
- Nginx
- SSL certificates

## Deployment Steps
1. Run pre-deployment verification:
   \`\`\`bash
   ./scripts/verify.sh
   \`\`\`

2. Create backups:
   \`\`\`bash
   ./scripts/backup.sh
   \`\`\`

3. Deploy application:
   \`\`\`bash
   ./scripts/deploy.sh
   \`\`\`

4. Start monitoring:
   \`\`\`bash
   ./scripts/monitor.sh
   \`\`\`

## Verification
- Check service health
- Verify API endpoints
- Test frontend functionality
- Monitor system resources

## Rollback Procedure
If deployment fails:
\`\`\`bash
./scripts/rollback.sh
\`\`\`

## Maintenance
Regular maintenance tasks:
\`\`\`bash
./scripts/cleanup.sh
\`\`\`
EOF
}

# Function to generate API documentation
generate_api_docs() {
    print_header "Generating API Documentation"
    
    cat > "$DOCS_DIR/api-documentation.md" << EOF
# API Documentation

## Authentication
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/refresh

## Users
- GET /api/users/me
- PUT /api/users/me
- GET /api/users/{id}

## Forms
- GET /api/forms
- POST /api/forms
- GET /api/forms/{id}
- PUT /api/forms/{id}
- DELETE /api/forms/{id}

## Submissions
- GET /api/submissions
- POST /api/submissions
- GET /api/submissions/{id}
- PUT /api/submissions/{id}
- DELETE /api/submissions/{id}

## Health Check
- GET /api/health
EOF
}

# Function to generate database schema documentation
generate_db_schema() {
    print_header "Generating Database Schema Documentation"
    
    cat > "$DOCS_DIR/database-schema.md" << EOF
# Database Schema

## Users Table
\`\`\`sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
\`\`\`

## Forms Table
\`\`\`sql
CREATE TABLE forms (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
\`\`\`

## Submissions Table
\`\`\`sql
CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    form_id INTEGER REFERENCES forms(id),
    submitted_by INTEGER REFERENCES users(id),
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
\`\`\`
EOF
}

# Function to generate environment variables documentation
generate_env_docs() {
    print_header "Generating Environment Variables Documentation"
    
    cat > "$DOCS_DIR/environment-variables.md" << EOF
# Environment Variables

## Backend (.env)
\`\`\`
DATABASE_URL=postgresql://user:password@localhost:5432/formiq
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=formiq-app.com,www.formiq-app.com
CORS_ORIGIN_WHITELIST=https://formiq-app.com
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password
\`\`\`

## Frontend (.env)
\`\`\`
REACT_APP_API_URL=https://api.formiq-app.com
REACT_APP_WS_URL=wss://ws.formiq-app.com
\`\`\`
EOF
}

# Function to generate monitoring guide
generate_monitoring_guide() {
    print_header "Generating Monitoring Guide"
    
    cat > "$DOCS_DIR/monitoring-guide.md" << EOF
# Monitoring Guide

## System Monitoring
- CPU usage (threshold: 80%)
- Memory usage (threshold: 80%)
- Disk space (threshold: 80%)
- Service health
- API response times

## Log Monitoring
- Application logs
- Error logs
- Access logs
- Database logs

## Alert Thresholds
- CPU: > 80%
- Memory: > 80%
- Disk: > 80%
- API Response: > 2s
- Error Rate: > 1%

## Monitoring Script
\`\`\`bash
./scripts/monitor.sh
\`\`\`
EOF
}

# Function to generate rollback procedures
generate_rollback_procedures() {
    print_header "Generating Rollback Procedures"
    
    cat > "$DOCS_DIR/rollback-procedures.md" << EOF
# Rollback Procedures

## Automatic Rollback
If deployment fails, run:
\`\`\`bash
./scripts/rollback.sh
\`\`\`

## Manual Rollback Steps
1. Stop services:
   \`\`\`bash
   docker-compose down
   \`\`\`

2. Restore database:
   \`\`\`bash
   pg_restore -d formiq backups/latest.database.backup
   \`\`\`

3. Restore frontend:
   \`\`\`bash
   tar -xzf backups/latest.frontend.backup
   \`\`\`

4. Restore backend:
   \`\`\`bash
   tar -xzf backups/latest.backend.backup
   \`\`\`

5. Restore environment files:
   \`\`\`bash
   tar -xzf backups/latest.env.backup
   \`\`\`

6. Start services:
   \`\`\`bash
   docker-compose up -d
   \`\`\`
EOF
}

# Function to generate security guide
generate_security_guide() {
    print_header "Generating Security Guide"
    
    cat > "$DOCS_DIR/security-guide.md" << EOF
# Security Guide

## SSL Certificates
- Location: /etc/nginx/ssl/
- Renewal: Every 90 days
- Domains: formiq-app.com, www.formiq-app.com

## Environment Variables
- Never commit .env files
- Use strong passwords
- Rotate secrets regularly

## Database Security
- Regular backups
- Access control
- Connection encryption

## API Security
- Rate limiting
- Input validation
- CORS configuration
- Authentication
- Authorization

## Monitoring
- Error logging
- Access logging
- Security alerts
EOF
}

# Function to generate troubleshooting guide
generate_troubleshooting_guide() {
    print_header "Generating Troubleshooting Guide"
    
    cat > "$DOCS_DIR/troubleshooting-guide.md" << EOF
# Troubleshooting Guide

## Common Issues

### Service Not Starting
1. Check logs:
   \`\`\`bash
   docker-compose logs [service]
   \`\`\`

2. Verify configuration:
   \`\`\`bash
   docker-compose config
   \`\`\`

### Database Issues
1. Check connection:
   \`\`\`bash
   pg_isready -h localhost -p 5432
   \`\`\`

2. Verify credentials:
   \`\`\`bash
   psql -h localhost -U postgres -d formiq
   \`\`\`

### API Issues
1. Check endpoints:
   \`\`\`bash
   curl -v http://localhost:8000/api/health
   \`\`\`

2. Verify logs:
   \`\`\`bash
   tail -f backend/logs/error.log
   \`\`\`

### Frontend Issues
1. Check build:
   \`\`\`bash
   npm run build
   \`\`\`

2. Verify nginx:
   \`\`\`bash
   nginx -t
   \`\`\`
EOF
}

# Main function
main() {
    print_header "Documentation Generation"
    
    # Create docs directory
    mkdir -p "$DOCS_DIR"
    
    # Generate all documentation
    generate_deployment_guide
    generate_api_docs
    generate_db_schema
    generate_env_docs
    generate_monitoring_guide
    generate_rollback_procedures
    generate_security_guide
    generate_troubleshooting_guide
    
    # Verify all required documentation
    print_header "Verifying Documentation"
    local missing_docs=0
    
    for doc in "${REQUIRED_DOCS[@]}"; do
        if ! check_file "$DOCS_DIR/$doc"; then
            ((missing_docs++))
        fi
    done
    
    if [ $missing_docs -eq 0 ]; then
        echo -e "\n${GREEN}All documentation generated successfully${NC}"
    else
        echo -e "\n${RED}Missing $missing_docs documentation files${NC}"
        exit 1
    fi
}

# Run main function
main 
# Deployment Scripts

This directory contains a collection of scripts to automate various aspects of the deployment process for the FormIQ application.

## Scripts Overview

### 1. `deploy.sh`
The main deployment script that orchestrates the entire deployment process.

**Usage:**
```bash
./deploy.sh
```

### 2. `backend_setup.sh`
Handles backend setup, including dependency installation, testing, and verification.

**Usage:**
```bash
./backend_setup.sh
```

### 3. `frontend_setup.sh`
Manages frontend setup, including dependency installation, building, and optimization.

**Usage:**
```bash
./frontend_setup.sh
```

### 4. `database_setup.sh`
Handles database setup, migrations, and backups.

**Usage:**
```bash
./database_setup.sh
```

### 5. `monitoring_setup.sh`
Sets up monitoring and logging infrastructure.

**Usage:**
```bash
./monitoring_setup.sh
```

### 6. `security_check.sh`
Performs security checks and compliance verification.

**Usage:**
```bash
./security_check.sh
```

### 7. `performance_test.sh`
Runs performance tests and optimizations.

**Usage:**
```bash
./performance_test.sh
```

### 8. `backup_restore.sh`
Manages backup and restore operations.

**Usage:**
```bash
# Create a backup
./backup_restore.sh backup

# Restore from a backup
./backup_restore.sh restore <backup_directory>

# List available backups
./backup_restore.sh list
```

### 9. `generate_ssl.sh`
Generates SSL certificates for development.

**Usage:**
```bash
./generate_ssl.sh
```

### 10. `verify_deployment.sh`
Verifies the deployment environment and configurations.

**Usage:**
```bash
./verify_deployment.sh
```

## Prerequisites

Before running any of these scripts, ensure you have the following installed:

- Docker and Docker Compose
- Node.js and npm
- Python 3.x and pip
- OpenSSL
- Required Python packages (from `requirements.txt`)
- Required Node.js packages (from `package.json`)

## Directory Structure

```
scripts/
├── deploy.sh              # Main deployment script
├── backend_setup.sh       # Backend setup script
├── frontend_setup.sh      # Frontend setup script
├── database_setup.sh      # Database setup script
├── monitoring_setup.sh    # Monitoring setup script
├── security_check.sh      # Security check script
├── performance_test.sh    # Performance test script
├── backup_restore.sh      # Backup and restore script
├── generate_ssl.sh        # SSL certificate generation script
├── verify_deployment.sh   # Deployment verification script
└── README.md             # This file
```

## Environment Variables

The scripts expect certain environment variables to be set. Create a `.env` file in the root directory with the following variables:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=formiq
DB_USER=postgres
DB_PASSWORD=your_password

# Backend
BACKEND_PORT=8000
DJANGO_SECRET_KEY=your_secret_key
DJANGO_DEBUG=False

# Frontend
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=production
REACT_APP_VERSION=1.0.0

# SSL
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## Error Handling

All scripts include error handling and will:
1. Display colored output for better visibility
2. Exit with appropriate status codes
3. Provide detailed error messages
4. Create logs for debugging

## Logging

Logs are stored in the following directories:
- Application logs: `logs/application/`
- Nginx logs: `logs/nginx/`
- Database logs: `logs/database/`
- Monitoring logs: `logs/monitoring/`

## Backup and Restore

Backups are stored in the `backups/` directory with timestamps. Each backup includes:
- Database dump
- Environment files
- SSL certificates
- Configuration files

## Security Considerations

- All scripts check for proper file permissions
- Sensitive data is handled securely
- SSL certificates are properly managed
- Security headers are verified
- Dependencies are checked for vulnerabilities

## Performance Optimization

The scripts include:
- Asset optimization
- Database optimization
- Load testing
- Stress testing
- Response time monitoring

## Monitoring

The monitoring setup includes:
- Prometheus for metrics collection
- Grafana for visualization
- Alertmanager for notifications
- Log rotation and management

## Contributing

When adding new scripts or modifying existing ones:
1. Follow the established pattern of error handling
2. Include proper documentation
3. Add appropriate logging
4. Test thoroughly before committing

## Troubleshooting

Common issues and solutions:

1. **Database Connection Issues**
   - Check if PostgreSQL is running
   - Verify database credentials
   - Ensure proper network connectivity

2. **SSL Certificate Issues**
   - Verify certificate paths
   - Check certificate validity
   - Ensure proper permissions

3. **Permission Issues**
   - Check file ownership
   - Verify directory permissions
   - Ensure proper user access

4. **Performance Issues**
   - Monitor resource usage
   - Check for bottlenecks
   - Review optimization settings

## Support

For issues or questions:
1. Check the logs in the appropriate directory
2. Review the error messages
3. Consult the documentation
4. Contact the development team 
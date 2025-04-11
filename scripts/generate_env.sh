#!/bin/bash

# Function to generate a random string
generate_random_string() {
    openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c "$1"
}

# Function to generate a random number
generate_random_number() {
    openssl rand -hex 1 | tr -dc '0-9' | head -c "$1"
}

# Generate secure values
SECRET_KEY=$(generate_random_string 64)
ENCRYPTION_KEY=$(generate_random_string 32)
ADMIN_REGISTRATION_CODE=$(generate_random_string 16)
SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@db:5432/formiq"
SMTP_PORT="587"
SMTP_HOST="smtp.gmail.com"
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-app-specific-password"
STRIPE_SECRET_KEY="sk_test_your_stripe_test_key"
STRIPE_WEBHOOK_SECRET="whsec_your_stripe_webhook_secret"
AWS_ACCESS_KEY_ID="your_aws_access_key"
AWS_SECRET_ACCESS_KEY="your_aws_secret_key"
REDIS_HOST="redis"
REDIS_PORT="6379"
REDIS_PASSWORD=$(generate_random_string 32)
SENTRY_DSN="your_sentry_dsn"

# Create .env.production file
cat > backend/.env.production << EOL
# Project
PROJECT_NAME=FormIQ
VERSION=1.0.0
DESCRIPTION=AI-powered fitness tracking and form analysis
API_V1_STR=/api/v1
ENVIRONMENT=production
DEBUG=false

# CORS
CORS_ORIGINS=["https://formiq-app.com", "https://www.formiq-app.com", "https://app.formiq-app.com"]

# Security
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=14
ADMIN_REGISTRATION_CODE=${ADMIN_REGISTRATION_CODE}

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/formiq
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=formiq
SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI}

# Database connection pool settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=300
DB_ECHO=false

# Email
SMTP_TLS=True
SMTP_PORT=${SMTP_PORT}
SMTP_HOST=${SMTP_HOST}
SMTP_USER=${SMTP_USER}
SMTP_PASSWORD=${SMTP_PASSWORD}
EMAILS_FROM_EMAIL=no-reply@formiq-app.com
EMAILS_FROM_NAME=FormIQ

# Stripe
STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_REGION=us-west-2
S3_BUCKET=formiq-media
USE_S3_STORAGE=true

# Redis
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_DB=0
USE_REDIS_CACHE=true

# Storage
UPLOAD_DIR=uploads/videos
UPLOAD_URL=https://formiq-media.s3.amazonaws.com
MAX_CONTENT_LENGTH=104857600
MAX_VIDEO_DURATION=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_TO_STDOUT=true
LOG_TO_FILE=true
LOG_FILE_PATH=/var/log/formiq/application.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
ENABLE_REQUEST_LOGGING=true
ENABLE_SENTRY=true
SENTRY_DSN=${SENTRY_DSN}
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Rate limiting
RATE_LIMIT_STORAGE=redis
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_REQUESTS=100
RATE_LIMIT_DEFAULT_BURST=200
RATE_LIMIT_TOKEN_REQUESTS=50

# Security Headers
SECURITY_HSTS_SECONDS=31536000
SECURITY_HSTS_INCLUDE_SUBDOMAINS=true
SECURITY_FRAME_DENY=true
SECURITY_XSS_PROTECTION=true
SECURITY_CONTENT_TYPE_NOSNIFF=true
SECURITY_CONTENT_SECURITY_POLICY="default-src 'self'; img-src 'self' data: https://*.s3.amazonaws.com; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self' https://api.stripe.com;"

# Miscellaneous
APP_DOMAIN=formiq-app.com
ENABLE_DOCS=false
ALLOWED_ORIGINS=https://formiq-app.com,https://www.formiq-app.com
EOL

echo "Environment variables generated successfully in backend/.env.production"
echo "Please review and update the following values with your actual credentials:"
echo "- SMTP_USER and SMTP_PASSWORD"
echo "- STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET"
echo "- AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
echo "- SENTRY_DSN" 
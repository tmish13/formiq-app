#!/bin/bash

# Database Configuration
export POSTGRES_SERVER=localhost
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_secure_password
export POSTGRES_DB=formiq
export SQLALCHEMY_DATABASE_URI=postgresql://postgres:your_secure_password@localhost:5432/formiq

# Security
export SECRET_KEY=your_secret_key_here
export ENCRYPTION_KEY=your_encryption_key_here
export ADMIN_REGISTRATION_CODE=your_admin_code_here

# Email Configuration
export SMTP_PORT=587
export SMTP_HOST=smtp.example.com
export SMTP_USER=your_email@example.com
export SMTP_PASSWORD=your_email_password

# Payment Processing
export STRIPE_SECRET_KEY=your_stripe_secret_key
export STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret

# AWS Configuration
export AWS_ACCESS_KEY_ID=your_aws_access_key
export AWS_SECRET_ACCESS_KEY=your_aws_secret_key
export S3_BUCKET=formiq-storage

# Redis Configuration
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your_redis_password

# Error Tracking
export SENTRY_DSN=your_sentry_dsn

# Frontend Configuration
export REACT_APP_API_URL=https://api.formiq-app.com
export REACT_APP_WS_URL=wss://api.formiq-app.com
export REACT_APP_SENTRY_DSN=${SENTRY_DSN}
export REACT_APP_GA_TRACKING_ID=your_ga_tracking_id 
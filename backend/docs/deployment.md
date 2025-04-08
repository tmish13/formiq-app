# FormIQ Deployment Guide

This guide provides instructions for deploying the FormIQ application in a production environment.

## Prerequisites

- Linux server (Ubuntu 20.04 LTS or later recommended)
- Python 3.9+ with venv
- PostgreSQL 14+
- Redis (optional, for rate limiting and caching)
- AWS account with S3 access
- Domain name with SSL certificate
- Nginx or similar web server for reverse proxy

## System Requirements

- **Minimum**: 2 CPU cores, 4GB RAM, 20GB storage
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB storage
- **Database**: Separate PostgreSQL instance recommended for production

## Step 1: Server Setup

### Create a Dedicated User

```bash
# Create the formiq user
sudo adduser --disabled-password formiq

# Add to sudo group if needed
sudo usermod -aG sudo formiq

# Create application directories
sudo mkdir -p /home/formiq/formiq-app
sudo mkdir -p /var/log/formiq
sudo chown -R formiq:formiq /home/formiq/formiq-app /var/log/formiq
```

### Install Required Packages

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib \
                   nginx supervisor git ffmpeg libpq-dev python3-dev build-essential
```

## Step 2: Clone and Set Up Application

```bash
# Switch to formiq user
sudo su - formiq

# Clone the repository
git clone https://github.com/your-repo/formiq-app.git ~/formiq-app

# Create and activate a virtual environment
python3 -m venv ~/venv
source ~/venv/bin/activate

# Install dependencies
cd ~/formiq-app/backend
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]
```

## Step 3: Configure Environment

```bash
# Copy the production template
cp .env.production.template .env.production

# Edit the production environment file
nano .env.production
```

Fill in all required environment variables, particularly:

- Database credentials
- AWS credentials for S3 storage
- Stripe keys (if using payment functionality)
- SMTP settings for email
- JWT and application secret keys

### Generate Strong Secret Keys

```bash
# Generate a strong random key for SECRET_KEY and JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

## Step 4: Database Setup

### Configure PostgreSQL

```bash
# Create database and user
sudo -u postgres psql

postgres=# CREATE DATABASE formiq_prod;
postgres=# CREATE USER formiq_prod WITH PASSWORD 'your_secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE formiq_prod TO formiq_prod;
postgres=# \q
```

### Run Migrations

```bash
cd ~/formiq-app/backend
ENVIRONMENT=production alembic upgrade head
```

### Initialize Seed Data (if needed)

```bash
ENVIRONMENT=production python -m app.db.init_db
```

## Step 5: S3 Storage Setup

### Create S3 Bucket

1. Log in to the AWS Management Console
2. Navigate to S3 service
3. Create a new bucket named `formiq-videos-prod`
4. Configure CORS for the bucket:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
    "AllowedOrigins": ["https://formiq.app"],
    "ExposeHeaders": []
  }
]
```

### Set Bucket Policy

For public read access to videos (if needed):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadForVideos",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::formiq-videos-prod/*"
    }
  ]
}
```

### IAM User Setup

1. Create an IAM user with S3 access
2. Generate access keys
3. Update the `.env.production` file with these credentials

## Step 6: Configure Supervisor

```bash
# Copy the supervisor config
sudo cp ~/formiq-app/backend/deployment/formiq.conf /etc/supervisor/conf.d/

# Update the config if needed
sudo nano /etc/supervisor/conf.d/formiq.conf

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
```

## Step 7: Set Up Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/formiq
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name api.formiq.app;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name api.formiq.app;

    ssl_certificate /etc/letsencrypt/live/api.formiq.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.formiq.app/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Content-Security-Policy "default-src 'self'";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    client_max_body_size 100M;

    # API Proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # Static files for uploaded videos
    location /uploads/ {
        alias /home/formiq/formiq-app/backend/uploads/;
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/formiq /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 8: SSL Certificate with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.formiq.app
```

## Step 9: Testing the Deployment

```bash
# Check if the application is running
sudo supervisorctl status formiq-all

# Test the API endpoint
curl -k https://api.formiq.app/health

# View logs
sudo tail -f /var/log/formiq/app.log
```

## Deployment Checklist

Before going live, ensure:

- [ ] All environment variables are properly set
- [ ] Database migrations have been applied
- [ ] S3 bucket and permissions are configured
- [ ] SSL certificate is valid
- [ ] Health check endpoints return successfully
- [ ] User authentication works
- [ ] File uploads and downloads work correctly
- [ ] Error logging is configured
- [ ] Backups are set up for the database

## Troubleshooting

### Application Won't Start

Check the logs:
```bash
sudo tail -f /var/log/formiq/error.log
```

Common issues:
- Missing environment variables
- Database connection failures
- Port conflicts

### Database Connection Issues

Verify PostgreSQL is running:
```bash
sudo systemctl status postgresql
```

Check connection string:
```bash
# Test connection to the database
psql -h localhost -U formiq_prod -d formiq_prod
```

### S3 Storage Issues

- Verify AWS credentials are correct
- Check bucket permissions
- Test AWS CLI access:
```bash
aws s3 ls s3://formiq-videos-prod --profile formiq
```

### 502 Bad Gateway Errors

- Check if the application is running: `sudo supervisorctl status formiq`
- Verify Nginx configuration: `sudo nginx -t`
- Check Nginx access/error logs: `sudo tail -f /var/log/nginx/error.log`

## Backup and Recovery

### Database Backup

```bash
# Create a backup script
cat > ~/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/formiq/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -h localhost -U formiq_prod formiq_prod > $BACKUP_DIR/formiq_db_$TIMESTAMP.sql

# Compress backup
gzip $BACKUP_DIR/formiq_db_$TIMESTAMP.sql

# Backup env file
cp /home/formiq/formiq-app/backend/.env.production $BACKUP_DIR/env_$TIMESTAMP.backup

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/formiq_db_$TIMESTAMP.sql.gz s3://formiq-backups/
EOF

chmod +x ~/backup.sh

# Schedule daily backups with cron
(crontab -l 2>/dev/null; echo "0 2 * * * /home/formiq/backup.sh") | crontab -
```

### Recovery

```bash
# Restore database
gunzip -c backup_file.sql.gz | psql -h localhost -U formiq_prod -d formiq_prod
```

## Monitoring

Consider setting up:
- Prometheus + Grafana for metrics
- ELK stack for log aggregation
- Sentry for error tracking
- Uptime monitoring with Uptime Robot or similar

## Scaling Considerations

For higher load:
- Increase worker processes in supervisor config
- Set up a PostgreSQL read replica
- Configure Redis for caching
- Consider containerization with Docker and Kubernetes 
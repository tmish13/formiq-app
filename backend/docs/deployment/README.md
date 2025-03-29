# Deployment Guide

## Overview

This guide covers the deployment of the Formiq application in various environments, from development to production.

## Deployment Options

1. Docker Compose (Recommended for small to medium deployments)
2. Kubernetes (Recommended for large-scale deployments)
3. Manual Deployment (For custom setups)

## Docker Compose Deployment

### 1. Prerequisites

- Docker 20.10 or higher
- Docker Compose 2.0 or higher
- Domain name (for production)
- SSL certificate (for production)

### 2. Environment Setup

1. Create production environment file:
```bash
cp .env.example .env.prod
```

2. Configure production environment variables:
```env
# Database
DATABASE_URL=postgresql://user:password@db:5432/formiq

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET=your-secure-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASSWORD=your-password

# Storage
STORAGE_TYPE=s3
S3_BUCKET=your-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=your-region

# Security
CORS_ORIGINS=https://your-domain.com
ENVIRONMENT=production
```

### 3. Deployment Steps

1. Build and start the services:
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

2. Run database migrations:
```bash
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

3. Verify services are running:
```bash
docker-compose -f docker-compose.prod.yml ps
```

4. Check logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

## Kubernetes Deployment

### 1. Prerequisites

- Kubernetes cluster
- kubectl configured
- Helm (optional)
- Domain name
- SSL certificate

### 2. Kubernetes Resources

1. Create namespace:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: formiq
```

2. Create secrets:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: formiq-secrets
  namespace: formiq
type: Opaque
data:
  DATABASE_URL: <base64-encoded-url>
  REDIS_HOST: <base64-encoded-host>
  JWT_SECRET: <base64-encoded-secret>
  STRIPE_SECRET_KEY: <base64-encoded-key>
  # ... other secrets
```

3. Deploy PostgreSQL:
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: formiq
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:13
        env:
        - name: POSTGRES_DB
          value: formiq
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: formiq-secrets
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: formiq-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

4. Deploy Redis:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: formiq
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:6
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
```

5. Deploy API:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: formiq
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: formiq-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: formiq-secrets
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
```

6. Create services:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: formiq
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 3. Deployment Steps

1. Apply Kubernetes resources:
```bash
kubectl apply -f k8s/
```

2. Run database migrations:
```bash
kubectl exec -it -n formiq deploy/api -- alembic upgrade head
```

3. Verify deployment:
```bash
kubectl get pods -n formiq
kubectl get services -n formiq
```

## Manual Deployment

### 1. Server Requirements

- Ubuntu 20.04 LTS or higher
- 4+ CPU cores
- 8GB+ RAM
- 50GB+ storage
- Public IP address
- Domain name
- SSL certificate

### 2. Server Setup

1. Update system:
```bash
sudo apt update && sudo apt upgrade -y
```

2. Install dependencies:
```bash
sudo apt install -y python3.9 python3.9-venv postgresql-13 redis-server nginx
```

3. Configure PostgreSQL:
```bash
sudo -u postgres psql
CREATE DATABASE formiq;
CREATE USER formiq WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE formiq TO formiq;
```

4. Configure Redis:
```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

5. Set up application:
```bash
cd /opt
sudo git clone https://github.com/yourusername/formiq-app.git
cd formiq-app
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

6. Configure Nginx:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

7. Set up systemd service:
```ini
[Unit]
Description=Formiq API
After=network.target

[Service]
User=formiq
Group=formiq
WorkingDirectory=/opt/formiq-app
Environment="PATH=/opt/formiq-app/venv/bin"
ExecStart=/opt/formiq-app/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

8. Start services:
```bash
sudo systemctl enable formiq-api
sudo systemctl start formiq-api
sudo systemctl restart nginx
```

## Monitoring and Maintenance

### 1. Health Checks

- API health endpoint: `/api/health`
- Database connection
- Redis connection
- Storage access

### 2. Logging

- Application logs: `journalctl -u formiq-api`
- Nginx logs: `/var/log/nginx/`
- Database logs: `/var/log/postgresql/`

### 3. Backup

1. Database backup:
```bash
pg_dump -U formiq formiq > backup.sql
```

2. Redis backup:
```bash
redis-cli SAVE
cp /var/lib/redis/dump.rdb /backup/
```

3. File storage backup:
```bash
aws s3 sync s3://your-bucket s3://your-backup-bucket
```

### 4. Updates

1. Pull latest changes:
```bash
cd /opt/formiq-app
git pull
```

2. Update dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

3. Run migrations:
```bash
alembic upgrade head
```

4. Restart services:
```bash
sudo systemctl restart formiq-api
```

## Security Considerations

1. SSL/TLS configuration
2. Firewall rules
3. Database security
4. API rate limiting
5. Input validation
6. Error handling
7. Logging security
8. Backup security

## Troubleshooting

1. Check service status:
```bash
sudo systemctl status formiq-api
```

2. Check logs:
```bash
journalctl -u formiq-api -f
```

3. Check database:
```bash
sudo -u postgres psql -d formiq
```

4. Check Redis:
```bash
redis-cli ping
```

5. Check Nginx:
```bash
sudo nginx -t
```

## Support

For deployment support:
- Check the [Setup Guide](../setup/README.md)
- Review the [Development Guide](../development/README.md)
- Contact support@formiq.com 
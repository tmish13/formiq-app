# Setup Instructions

## Prerequisites

- Python 3.9 or higher
- PostgreSQL 13 or higher
- Redis 6 or higher
- Node.js 16 or higher (for frontend)
- Docker and Docker Compose (optional)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/formiq-app.git
cd formiq-app
```

### 2. Backend Setup

1. Create and activate a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt  # For development
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/formiq

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET=your-secret-key
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
STORAGE_TYPE=local  # or s3
S3_BUCKET=your-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=your-region
```

4. Initialize the database:
```bash
alembic upgrade head
```

5. Run the development server:
```bash
uvicorn app.main:app --reload
```

### 3. Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_STRIPE_PUBLIC_KEY=your-stripe-public-key
```

3. Run the development server:
```bash
npm run dev
```

## Docker Setup

### 1. Development Environment

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis server
- Backend API
- Frontend development server

### 2. Production Environment

```bash
docker-compose -f docker-compose.prod.yml up -d
```

This will start:
- PostgreSQL database
- Redis server
- Backend API (with production settings)
- Nginx reverse proxy
- Frontend production build

## Database Setup

### 1. Create Database

```sql
CREATE DATABASE formiq;
```

### 2. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 3. Seed Initial Data (Optional)

```bash
cd backend
python scripts/seed_data.py
```

## Redis Setup

### 1. Install Redis

On macOS:
```bash
brew install redis
brew services start redis
```

On Ubuntu:
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### 2. Verify Redis Connection

```bash
redis-cli ping
# Should return PONG
```

## Testing Setup

1. Install test dependencies:
```bash
cd backend
pip install -r requirements-test.txt
```

2. Set up test database:
```bash
createdb formiq_test
```

3. Run tests:
```bash
pytest
```

4. Generate coverage report:
```bash
pytest --cov=app --cov-report=html
```

## Common Issues and Solutions

### 1. Database Connection Issues

- Check if PostgreSQL is running
- Verify database credentials in `.env`
- Ensure database exists
- Check network connectivity

### 2. Redis Connection Issues

- Check if Redis is running
- Verify Redis configuration in `.env`
- Check network connectivity

### 3. Migration Issues

- Check if all migrations are in order
- Verify database schema
- Check for conflicting migrations

### 4. Environment Variables

- Ensure all required variables are set
- Check for typos in variable names
- Verify values are correct

## Development Tools

### 1. Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Run hooks manually:
```bash
pre-commit run --all-files
```

### 2. Code Formatting

Format code:
```bash
black .
isort .
```

### 3. Type Checking

Run type checks:
```bash
mypy .
```

## Getting Help

- Check the [API Documentation](../api/README.md)
- Review the [Development Guide](../development/README.md)
- Check the [Deployment Guide](../deployment/README.md)
- Contact support@formiq.com 
#!/bin/bash
set -e

# Function to wait for database to be ready
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    
    RETRIES=10
    until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_SERVER" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
        echo "Waiting for PostgreSQL server, $((RETRIES--)) remaining attempts..."
        sleep 3
    done
    
    if [ $RETRIES -eq 0 ]; then
        echo "Failed to connect to PostgreSQL"
        exit 1
    fi
    
    echo "PostgreSQL is ready!"
}

# Print environment
echo "Starting FormIQ API in $ENVIRONMENT environment"

if [ "$ENVIRONMENT" = "production" ]; then
    # Only run these steps in production
    if [ -n "$POSTGRES_SERVER" ] && [ "$POSTGRES_SERVER" != "localhost" ]; then
        wait_for_postgres
    fi
    
    # Run migrations
    echo "Running database migrations..."
    alembic upgrade head
    
    echo "FormIQ is ready to start!"
else
    echo "Development mode detected, skipping migration checks"
fi

# Forward arguments to CMD
exec "$@" 
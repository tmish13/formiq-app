#!/bin/bash

# Function to handle database operations
manage_db() {
    local action=$1
    local db_name=$2
    
    case $action in
        "init")
            echo "Initializing database..."
            cd backend && python scripts/setup_db.py
            ;;
        "reset")
            echo "Resetting database..."
            cd backend && python scripts/reset_migrations.py
            ;;
        "migrate")
            echo "Running migrations..."
            cd backend && python scripts/run_migrations.py
            ;;
        *)
            echo "Unknown action: $action"
            echo "Available actions: init, reset, migrate"
            exit 1
            ;;
    esac
}

# Check if action is provided
if [ -z "$1" ]; then
    echo "Please provide an action: init, reset, or migrate"
    exit 1
fi

manage_db "$1" "$2" 
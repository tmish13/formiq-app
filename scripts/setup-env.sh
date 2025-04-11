#!/bin/bash

# Function to copy environment file if it doesn't exist
setup_env_file() {
    local template=$1
    local target=$2
    
    if [ ! -f "$target" ]; then
        echo "Creating $target from template..."
        cp "$template" "$target"
        echo "Please update $target with your configuration values"
    else
        echo "$target already exists, skipping..."
    fi
}

# Setup frontend environment
setup_env_file "config/templates/frontend.env.example" "frontend/.env"
setup_env_file "config/templates/frontend.env.example" "frontend/.env.production"

# Setup backend environment
setup_env_file "config/templates/backend.env.example" "backend/.env"
setup_env_file "config/templates/backend.env.example" "backend/.env.production"

echo "Environment setup complete!" 
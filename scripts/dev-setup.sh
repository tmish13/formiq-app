#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check Node.js
    if ! command_exists node; then
        echo "Node.js is not installed. Please install Node.js first."
        exit 1
    fi
    
    # Check npm
    if ! command_exists npm; then
        echo "npm is not installed. Please install npm first."
        exit 1
    fi
    
    # Check Python
    if ! command_exists python3; then
        echo "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check pip
    if ! command_exists pip3; then
        echo "pip3 is not installed. Please install pip3 first."
        exit 1
    fi
    
    echo "All prerequisites are satisfied!"
}

# Function to setup frontend
setup_frontend() {
    echo "Setting up frontend..."
    cd frontend
    
    # Install dependencies
    npm install
    
    # Setup environment
    cp .env.example .env
    
    echo "Frontend setup complete!"
}

# Function to setup backend
setup_backend() {
    echo "Setting up backend..."
    cd backend
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Setup environment
    cp .env.example .env
    
    echo "Backend setup complete!"
}

# Main setup process
echo "Starting development setup..."

# Check prerequisites
check_prerequisites

# Setup frontend
setup_frontend

# Setup backend
setup_backend

echo "Development setup complete! You can now start developing."
echo "To start the frontend: cd frontend && npm start"
echo "To start the backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload" 
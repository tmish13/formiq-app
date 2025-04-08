#!/bin/bash
# start_formiq.sh - Script to safely start the FormIQ application
# 
# This script ensures proper startup of the FormIQ application by:
# 1. Checking for existing processes and cleaning them up
# 2. Starting the server with the specified configuration
# 3. Providing informative output about the startup process
#
# Usage: ./start_formiq.sh [port] [host] [workers] [environment]
#   port: Port to listen on (default: 8000)
#   host: Host to bind to (default: 0.0.0.0)
#   workers: Number of worker processes (default: 1 for dev, 4 for prod)
#   environment: deployment environment (default: development)

# Set default values
PORT=${1:-8000}
HOST=${2:-0.0.0.0}
ENVIRONMENT=${4:-development}

# Set workers based on environment
if [ "$ENVIRONMENT" = "production" ]; then
  WORKERS=${3:-4}
else
  WORKERS=${3:-1}
fi

# Determine the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Print startup message
echo "================================================"
echo "Starting FormIQ API on $HOST:$PORT"
echo "Environment: $ENVIRONMENT"
echo "Workers: $WORKERS"
echo "================================================"

# Check for running instances and clean them up
echo "Checking for existing FormIQ processes..."
EXISTING_PIDS=$(pgrep -f "uvicorn app.main:app")

if [ -n "$EXISTING_PIDS" ]; then
  echo "Found existing FormIQ processes: $EXISTING_PIDS"
  echo "Stopping existing processes..."
  
  # Kill existing processes
  for PID in $EXISTING_PIDS; do
    echo "Stopping process $PID..."
    kill -15 $PID 2>/dev/null || kill -9 $PID 2>/dev/null
  done
  
  # Give processes time to shut down
  sleep 2
  
  # Check if any processes are still running
  if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "Warning: Some processes are still running. Using force kill..."
    pkill -9 -f "uvicorn app.main:app"
    sleep 1
  fi
  
  echo "Cleanup complete."
else
  echo "No existing FormIQ processes found."
fi

# Check if the port is already in use
if lsof -i:$PORT -t >/dev/null ; then
  echo "Warning: Port $PORT is already in use by another process."
  echo "Attempting to free the port..."
  
  # Try to kill the process using the port
  lsof -i:$PORT -t | xargs kill -15 2>/dev/null || lsof -i:$PORT -t | xargs kill -9 2>/dev/null
  sleep 1
  
  # Check if port is still in use
  if lsof -i:$PORT -t >/dev/null ; then
    echo "Error: Could not free port $PORT. Please choose a different port."
    exit 1
  else
    echo "Port $PORT has been freed."
  fi
fi

# Start the application
echo "Starting FormIQ API..."

if [ "$ENVIRONMENT" = "production" ]; then
  # Production mode - no reload
  uvicorn app.main:app --host $HOST --port $PORT --workers $WORKERS
else
  # Development mode with auto-reload
  uvicorn app.main:app --host $HOST --port $PORT --reload
fi 
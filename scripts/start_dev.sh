#!/bin/bash

# Start development servers

# Start the backend server
start_backend() {
    echo "Starting backend server..."
    cd backend
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ..
    echo "Backend server started with PID: $BACKEND_PID"
}

# Start the frontend server
start_frontend() {
    echo "Starting frontend server..."
    cd frontend
    npm start &
    FRONTEND_PID=$!
    cd ..
    echo "Frontend server started with PID: $FRONTEND_PID"
}

# Handle shutdown
cleanup() {
    echo "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
    fi
    exit 0
}

# Register cleanup handler
trap cleanup INT TERM

# Start servers
start_backend
start_frontend

echo "Development servers are running."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both servers."

# Wait for Ctrl+C
wait

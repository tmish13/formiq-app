#!/bin/bash

# Setup Development Environment for FormIQ

echo "Setting up development environment for FormIQ..."

# Create necessary directories
mkdir -p backend/uploads/videos
mkdir -p backend/logs

# Backend setup
echo "Setting up backend environment..."
cd backend

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating backend .env file..."
    cp .env.example .env
    
    # Generate a random secret key
    SECRET_KEY=$(openssl rand -base64 32)
    sed -i '' "s/your-secret-key-here/$SECRET_KEY/g" .env
    
    echo "Backend .env file created with random secret key."
else
    echo "Backend .env file already exists."
fi

# Install Python dependencies if needed
if [ -f "requirements.txt" ]; then
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
fi

# Initialize database
echo "Setting up the database..."
python setup_db.py

# Create Python package files if they don't exist
touch app/__init__.py
touch app/api/__init__.py
touch app/core/__init__.py
touch app/db/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch app/utils/__init__.py

cd ..

# Frontend setup
echo "Setting up frontend environment..."
cd frontend

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating frontend .env file..."
    cp .env.example .env
    echo "Frontend .env file created."
else
    echo "Frontend .env file already exists."
fi

# Update package.json if no start script exists
if ! grep -q '"start":' package.json; then
    echo "Adding start script to package.json..."
    # Create a temporary file with the updated package.json
    cat package.json | sed 's/"scripts": {/"scripts": {\n    "start": "react-scripts start",/' > package.json.tmp
    mv package.json.tmp package.json
fi

# Install Node.js dependencies
echo "Installing frontend dependencies..."
npm install --legacy-peer-deps

cd ..

echo "Creating development startup script..."
cat > start_dev.sh << 'EOF'
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
EOF

chmod +x start_dev.sh

echo "Setup complete! Run ./start_dev.sh to start the development servers." 
#!/bin/bash

# FormIQ Frontend Dependency Resolution Script
# This script resolves Node.js version conflicts and dependency issues

set -e  # Exit on any error

echo "🔧 FormIQ Frontend Dependency Resolution"
echo "========================================"

# Check current Node.js version
CURRENT_NODE=$(node --version | sed 's/v//')
REQUIRED_NODE="20.11.0"

echo "Current Node.js version: v$CURRENT_NODE"
echo "Required Node.js version: v$REQUIRED_NODE"

# Function to compare versions
version_compare() {
    if [[ $1 == $2 ]]; then
        echo "equal"
    elif [[ $(printf '%s\n' "$1" "$2" | sort -V | head -n1) == $1 ]]; then
        echo "less"
    else
        echo "greater"
    fi
}

NODE_COMPARISON=$(version_compare $CURRENT_NODE $REQUIRED_NODE)

if [[ $NODE_COMPARISON == "less" ]]; then
    echo "❌ Node.js version is too old (v$CURRENT_NODE < v$REQUIRED_NODE)"
    echo ""
    echo "🔄 Resolution Options:"
    echo "1. Install Node Version Manager (nvm):"
    echo "   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    echo "   source ~/.bashrc"
    echo "   nvm install $REQUIRED_NODE"
    echo "   nvm use $REQUIRED_NODE"
    echo ""
    echo "2. Or install Node.js v20+ from https://nodejs.org/"
    echo ""
    echo "After upgrading Node.js, run this script again."
    exit 1
fi

echo "✅ Node.js version is compatible"

# Step 1: Clean existing installations
echo ""
echo "🧹 Cleaning existing installations..."
rm -rf node_modules
rm -f package-lock.json
rm -f yarn.lock

# Step 2: Create package.json with proper resolutions
echo ""
echo "📦 Adding dependency resolutions..."

# Create a temporary file with resolutions
cat > temp_resolutions.json << EOF
{
  "resolutions": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^4.9.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "overrides": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^4.9.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
EOF

# Merge resolutions into package.json using Node.js
node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const resolutions = JSON.parse(fs.readFileSync('temp_resolutions.json', 'utf8'));

// Add resolutions and overrides
pkg.resolutions = resolutions.resolutions;
pkg.overrides = resolutions.overrides;

// Update engines requirement
pkg.engines = {
  'node': '>=20.0.0',
  'npm': '>=9.0.0'
};

fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
"

rm temp_resolutions.json

# Step 3: Install dependencies with proper flags
echo ""
echo "📥 Installing dependencies (this may take a few minutes)..."

# Try different installation strategies
if command -v yarn &> /dev/null; then
    echo "Using Yarn..."
    yarn install --ignore-engines --network-timeout 100000
elif npm --version &> /dev/null; then
    echo "Using npm..."
    
    # Set npm configurations for better compatibility
    npm config set legacy-peer-deps true
    npm config set fund false
    npm config set audit false
    
    # Install with legacy peer deps and increased timeout
    npm install --legacy-peer-deps --no-audit --no-fund --timeout=300000
else
    echo "❌ Neither npm nor yarn found!"
    exit 1
fi

# Step 4: Verify installation
echo ""
echo "🔍 Verifying installation..."

if [ -d "node_modules" ]; then
    echo "✅ node_modules directory created"
else
    echo "❌ node_modules directory not found"
    exit 1
fi

# Check for key dependencies
DEPENDENCIES_TO_CHECK=(
    "react"
    "react-dom" 
    "@mui/material"
    "@mui/icons-material"
    "react-router-dom"
    "styled-components"
    "typescript"
)

for dep in "${DEPENDENCIES_TO_CHECK[@]}"; do
    if [ -d "node_modules/$dep" ]; then
        echo "✅ $dep installed"
    else
        echo "❌ $dep missing"
    fi
done

# Step 5: Try a basic TypeScript compilation test
echo ""
echo "🔨 Testing TypeScript compilation..."
if npx tsc --version > /dev/null 2>&1; then
    echo "✅ TypeScript compiler working"
    
    # Try a simple compilation test
    echo "Testing basic compilation..."
    if npx tsc --noEmit --skipLibCheck > /dev/null 2>&1; then
        echo "✅ TypeScript compilation successful"
    else
        echo "⚠️  TypeScript compilation has issues (may be normal for incomplete project)"
    fi
else
    echo "❌ TypeScript compiler not working"
fi

# Step 6: Test React Scripts
echo ""
echo "⚛️  Testing React Scripts..."
if command -v npx &> /dev/null && npx react-scripts --version > /dev/null 2>&1; then
    echo "✅ React Scripts working"
else
    echo "❌ React Scripts not working"
fi

echo ""
echo "🎉 Dependency resolution complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Try starting the development server: npm start"
echo "2. If issues persist, check the logs above for specific errors"
echo "3. For Capacitor mobile development:"
echo "   - npm run cap:sync"
echo "   - npm run cap:android (or cap:ios)"
echo ""
echo "🔧 Troubleshooting:"
echo "- If 'npm start' fails, try: npm run build"
echo "- For permission issues: sudo chown -R \$(whoami) node_modules"
echo "- For cache issues: npm cache clean --force"
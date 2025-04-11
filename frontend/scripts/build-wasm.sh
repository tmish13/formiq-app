#!/bin/bash

# Exit on error
set -e

# Navigate to the wasm directory
cd "$(dirname "$0")/../wasm"

# Check if wasm-pack is installed
if ! command -v wasm-pack &> /dev/null; then
    echo "wasm-pack is not installed. Installing..."
    cargo install wasm-pack
fi

# Build the WebAssembly module
echo "Building WebAssembly module..."
wasm-pack build --target web

# Create the output directory if it doesn't exist
mkdir -p ../src/wasm

# Copy the built files to the src/wasm directory
echo "Copying built files to src/wasm directory..."
cp pkg/pose_calculations_bg.wasm ../src/wasm/
cp pkg/pose_calculations.js ../src/wasm/
cp pkg/pose_calculations.d.ts ../src/wasm/

echo "WebAssembly module built successfully!" 
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const WASM_DIR = path.join(__dirname, '../src/wasm');
const RUST_DIR = path.join(__dirname, '../rust');

// Ensure directories exist
if (!fs.existsSync(WASM_DIR)) {
  fs.mkdirSync(WASM_DIR, { recursive: true });
}

// Build Rust code to WebAssembly
console.log('Building WebAssembly module...');
try {
  // Change to Rust directory
  process.chdir(RUST_DIR);
  
  // Build using wasm-pack
  execSync('wasm-pack build --target web --out-dir ../frontend/src/wasm', {
    stdio: 'inherit'
  });
  
  console.log('WebAssembly build successful!');
} catch (error) {
  console.error('Error building WebAssembly:', error);
  process.exit(1);
} 
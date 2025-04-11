const fs = require('fs');
const path = require('path');

const WASM_SOURCE_DIR = path.join(__dirname, '../src/wasm');
const WASM_DEST_DIR = path.join(__dirname, '../public/wasm');

// Ensure destination directory exists
if (!fs.existsSync(WASM_DEST_DIR)) {
  fs.mkdirSync(WASM_DEST_DIR, { recursive: true });
}

// Copy WASM files
console.log('Copying WebAssembly files...');
try {
  const files = fs.readdirSync(WASM_SOURCE_DIR);
  for (const file of files) {
    if (file.endsWith('.wasm') || file.endsWith('.js')) {
      fs.copyFileSync(
        path.join(WASM_SOURCE_DIR, file),
        path.join(WASM_DEST_DIR, file)
      );
    }
  }
  console.log('WebAssembly files copied successfully!');
} catch (error) {
  console.error('Error copying WebAssembly files:', error);
  process.exit(1);
} 
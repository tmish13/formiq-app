const fs = require('fs');
const path = require('path');

console.log('Copying WebAssembly files...');

const sourceDir = path.join(__dirname, '../rust/pkg');
const targetDir = path.join(__dirname, '../public/wasm');

// Check if source directory exists
if (!fs.existsSync(sourceDir)) {
  console.log('WebAssembly source directory not found. Skipping copy operation.');
  process.exit(0); // Exit gracefully
}

// Create target directory if it doesn't exist
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

// Create a placeholder WASM file if no real files exist
const createPlaceholder = () => {
  console.log('Creating placeholder WASM file...');
  
  // Create minimal JavaScript wrapper
  const jsWrapper = `
export function initWasm() {
  console.log('WebAssembly module placeholder loaded');
  return {
    add: (a, b) => a + b,
    loaded: true
  };
}

export default { initWasm };
`;
  
  fs.writeFileSync(path.join(targetDir, 'formiq_wasm.js'), jsWrapper);
};

try {
  // Read all files from source directory
  const files = fs.readdirSync(sourceDir);
  
  if (files.length === 0) {
    createPlaceholder();
  } else {
    // Copy each file to target directory
    let copied = 0;
    
    files.forEach(file => {
      const sourcePath = path.join(sourceDir, file);
      const targetPath = path.join(targetDir, file);
      
      // Only copy .js and .wasm files
      if (file.endsWith('.js') || file.endsWith('.wasm')) {
        fs.copyFileSync(sourcePath, targetPath);
        copied++;
      }
    });
    
    if (copied === 0) {
      createPlaceholder();
    } else {
      console.log('WebAssembly files copied successfully!');
    }
  }
} catch (error) {
  console.error('Error copying WebAssembly files:', error);
  createPlaceholder();
  process.exit(0); // Exit gracefully
} 
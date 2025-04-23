const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Log output from the build process
console.log('Building WebAssembly module...');

// Check if rust directory exists
const rustDir = path.join(__dirname, '..', 'rust');
if (!fs.existsSync(rustDir)) {
  console.log('Rust directory not found, creating a minimal structure...');
  
  try {
    // Create rust directory
    fs.mkdirSync(rustDir, { recursive: true });
    
    // Create a minimal lib.rs file
    const libRsPath = path.join(rustDir, 'lib.rs');
    const minimalLibRs = `
// This is a placeholder Rust WebAssembly module
#[no_mangle]
pub extern "C" fn add(a: i32, b: i32) -> i32 {
    a + b
}
    `;
    
    fs.writeFileSync(libRsPath, minimalLibRs);
    
    // Create a minimal Cargo.toml
    const cargoTomlPath = path.join(rustDir, 'Cargo.toml');
    const minimalCargoToml = `
[package]
name = "formiq-wasm"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
wasm-bindgen = "0.2.83"
    `;
    
    fs.writeFileSync(cargoTomlPath, minimalCargoToml);
    
    console.log('Created minimal Rust WASM project structure.');
  } catch (err) {
    console.error('Failed to create Rust directory:', err);
    process.exit(0); // Exit gracefully to allow the rest of the build to continue
  }
}

// Function to compile WebAssembly
function compileWasm() {
  try {
    // Change to the rust directory
    process.chdir(rustDir);
    
    // Run wasm-pack build
    exec('wasm-pack build --target web', (error, stdout, stderr) => {
      if (error) {
        console.error('Error building WebAssembly:', error);
        console.log('Proceeding with build without WebAssembly components...');
        process.exit(0); // Exit gracefully to allow the rest of the build to continue
      }
      
      console.log(stdout);
      console.error(stderr);
      console.log('WebAssembly build successful!');
    });
  } catch (err) {
    console.error('Error during WebAssembly build:', err);
    console.log('Proceeding with build without WebAssembly components...');
    process.exit(0); // Exit gracefully to allow the rest of the build to continue
  }
}

// Check if wasm-pack is installed
exec('which wasm-pack', (error) => {
  if (error) {
    console.log('wasm-pack not found. Skipping WebAssembly build...');
    process.exit(0); // Exit gracefully to allow the rest of the build to continue
  } else {
    // wasm-pack is installed, proceed with compilation
    compileWasm();
  }
}); 
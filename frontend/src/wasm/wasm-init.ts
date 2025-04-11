import { initializeWasm } from './pose_calculations';

let wasmInitialized = false;

export async function initWasmModule() {
    if (!wasmInitialized) {
        try {
            await initializeWasm();
            wasmInitialized = true;
            console.log('WebAssembly module initialized successfully');
        } catch (error) {
            console.error('Failed to initialize WebAssembly module:', error);
            throw error;
        }
    }
    return wasmInitialized;
}

export function isWasmInitialized() {
    return wasmInitialized;
} 
import wasmModule from './pose_calculations.wasm';
import { WasmModule } from './pose_calculations';

export class PoseCalculations {
  private module: WasmModule | null = null;
  private memory: WebAssembly.Memory | null = null;

  async initialize(): Promise<void> {
    try {
      const wasm = await WebAssembly.instantiateStreaming(fetch(wasmModule));
      this.module = wasm.instance.exports as unknown as WasmModule;
      this.memory = wasm.instance.exports.memory as WebAssembly.Memory;
    } catch (error) {
      console.error('Failed to initialize WebAssembly module:', error);
      throw error;
    }
  }

  calculateAngles(points: Float32Array): Float32Array {
    if (!this.module) {
      throw new Error('WebAssembly module not initialized');
    }

    const length = points.length / 2; // Each point has x and y coordinates
    return this.module.calculateAngles(points, length);
  }

  calculateVelocities(current: Float32Array, previous: Float32Array): Float32Array {
    if (!this.module) {
      throw new Error('WebAssembly module not initialized');
    }

    const length = current.length / 2;
    return this.module.calculateVelocities(current, previous, length);
  }

  calculateConfidence(scores: Float32Array): number {
    if (!this.module) {
      throw new Error('WebAssembly module not initialized');
    }

    return this.module.calculateConfidence(scores, scores.length);
  }

  calculateCenterOfMass(points: Float32Array): Float32Array {
    if (!this.module) {
      throw new Error('WebAssembly module not initialized');
    }

    const length = points.length / 2;
    return this.module.calculateCenterOfMass(points, length);
  }
}

// Export a singleton instance
export const poseCalculations = new PoseCalculations(); 
// Mock TensorFlow.js backend functionality
const backend = {
  // WebGL backend
  webgl: {
    setupRegistry: jest.fn(),
    MathBackendWebGL: jest.fn().mockImplementation(() => ({
      setDataMover: jest.fn(),
      dispose: jest.fn()
    }))
  },

  // CPU backend
  cpu: {
    MathBackendCPU: jest.fn().mockImplementation(() => ({
      dispose: jest.fn()
    }))
  },

  // WASM backend
  wasm: {
    setWasmPaths: jest.fn(),
    MathBackendWasm: jest.fn().mockImplementation(() => ({
      dispose: jest.fn()
    }))
  }
};

module.exports = backend; 
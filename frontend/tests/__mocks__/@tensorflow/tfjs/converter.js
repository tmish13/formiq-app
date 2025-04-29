// Mock TensorFlow.js converter functionality
const converter = {
  // GraphModel conversion
  GraphModel: jest.fn().mockImplementation(() => ({
    predict: jest.fn().mockReturnValue({
      dataSync: jest.fn().mockReturnValue(new Float32Array([0.5, 0.5])),
      dispose: jest.fn()
    }),
    execute: jest.fn().mockReturnValue({
      dataSync: jest.fn().mockReturnValue(new Float32Array([0.5, 0.5])),
      dispose: jest.fn()
    }),
    dispose: jest.fn()
  })),

  // Model conversion utilities
  convertTensorflowModel: jest.fn().mockResolvedValue({
    modelTopology: {},
    weightSpecs: [],
    weightData: new ArrayBuffer(0)
  }),

  loadGraphModel: jest.fn().mockResolvedValue({
    predict: jest.fn().mockReturnValue({
      dataSync: jest.fn().mockReturnValue(new Float32Array([0.5, 0.5])),
      dispose: jest.fn()
    }),
    execute: jest.fn().mockReturnValue({
      dataSync: jest.fn().mockReturnValue(new Float32Array([0.5, 0.5])),
      dispose: jest.fn()
    }),
    dispose: jest.fn()
  })
};

module.exports = converter; 
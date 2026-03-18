// Stub for @tensorflow/tfjs-backend-webgpu.
// The WebGPU backend is not used by FormIQ (we use WebGL via tfjs-backend-webgl).
// @tensorflow-models/pose-detection includes a static reference to this package
// in its dist bundle; this stub satisfies the import without pulling in WebGPU code.
module.exports = {};

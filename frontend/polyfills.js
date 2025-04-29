const { TextEncoder, TextDecoder } = require('util');

// Initialize Jest globals
global.jest = require('jest-mock');

Object.assign(global, {
  TextEncoder,
  TextDecoder,
  jest,
}); 
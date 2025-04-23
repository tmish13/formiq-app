// This file runs once before all tests
const { TextEncoder, TextDecoder } = require('util');

module.exports = async () => {
  // Set up globals for all tests
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}; 
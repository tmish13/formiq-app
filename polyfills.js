const { TextEncoder, TextDecoder } = require('util');
const { Readable } = require('stream');
const { ReadableStream, WritableStream, TransformStream } = require('web-streams-polyfill');

// Polyfill TextEncoder and TextDecoder globally
Object.assign(global, {
  TextEncoder,
  TextDecoder,
  ReadableStream,
  WritableStream,
  TransformStream,
});

// Mock streaming APIs
global.fetch = global.fetch || require('node-fetch');

// Add response.json polyfill if not available
if (typeof Response !== 'undefined' && !Response.prototype.json) {
  Response.prototype.json = function() {
    return Promise.resolve({});
  };
} 
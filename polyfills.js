import { TextEncoder, TextDecoder } from 'util';
import { Readable } from 'stream';
import { ReadableStream, WritableStream, TransformStream } from 'web-streams-polyfill';
import fetch from 'node-fetch';

// Polyfill TextEncoder and TextDecoder globally
Object.assign(global, {
  TextEncoder,
  TextDecoder,
  ReadableStream,
  WritableStream,
  TransformStream,
});

// Mock streaming APIs
global.fetch = global.fetch || fetch;

// Add response.json polyfill if not available
if (typeof Response !== 'undefined' && !Response.prototype.json) {
  Response.prototype.json = function() {
    return Promise.resolve({});
  };
} 
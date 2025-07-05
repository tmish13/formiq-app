const { TextEncoder, TextDecoder } = require('util');
const fetch = require('node-fetch');
require('web-streams-polyfill');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Enhanced fetch setup for MSW compatibility
if (!global.fetch) {
  global.fetch = fetch;
  global.Headers = fetch.Headers;
  global.Request = fetch.Request;
  global.Response = fetch.Response;
}

// AbortController polyfill for MSW
if (!global.AbortController) {
  global.AbortController = class AbortController {
    constructor() {
      this.signal = {
        aborted: false,
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => {}
      };
    }
    abort() {
      this.signal.aborted = true;
    }
  };
} 
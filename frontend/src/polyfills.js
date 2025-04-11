const { TextEncoder, TextDecoder } = require('util');
const fetch = require('node-fetch');
require('web-streams-polyfill');

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
global.fetch = fetch;
global.Headers = fetch.Headers;
global.Request = fetch.Request;
global.Response = fetch.Response; 
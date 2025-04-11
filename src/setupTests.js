import { TextEncoder as NodeTextEncoder, TextDecoder as NodeTextDecoder } from 'util';
import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Polyfill TextEncoder/TextDecoder
global.TextEncoder = NodeTextEncoder;
global.TextDecoder = NodeTextDecoder;

// This configures a request mocking server with the given request handlers.
export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close()); 
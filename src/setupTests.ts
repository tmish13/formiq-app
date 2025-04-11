import { TextEncoder as NodeTextEncoder, TextDecoder as NodeTextDecoder } from 'util';
import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Polyfill TextEncoder/TextDecoder
global.TextEncoder = NodeTextEncoder as typeof global.TextEncoder;
global.TextDecoder = NodeTextDecoder as typeof global.TextDecoder;

// This configures a request mocking server with the given request handlers.
export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close()); 
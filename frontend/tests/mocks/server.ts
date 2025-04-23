import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { handlers } from './handlers';

// This configures a Service Worker with the given request handlers.
export const server = setupServer(...handlers);

// Do not include lifecycle hooks here as they should be in setup.tsx
// to avoid duplication and conflicts when imported in individual test files 
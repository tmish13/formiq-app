import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

// Define handlers
const handlers = [
  // Default handlers for API endpoints
  http.get('/api/user', () => {
    return HttpResponse.json({ id: '1', name: 'Test User', email: 'test@example.com' });
  }),
  
  // Add more handlers as needed for different endpoints
];

// Setup MSW server
export const server = setupServer(...handlers); 
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { handlers } from '../../src/services/api/handlers';

// This configures a request mocking server with the given request handlers.
export const server = setupServer(...handlers);

// Export individual handlers for test-specific overrides
export { handlers };

// Define common request handlers
export const commonHandlers = [
  rest.get('/api/user', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ 
        id: '1', 
        name: 'Test User', 
        email: 'test@example.com' 
      })
    );
  }),
  
  rest.post('/api/auth/login', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'mock_token',
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user',
        }
      })
    );
  }),
  
  rest.post('/api/auth/logout', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  }),
  
  rest.get('/api/form-checks', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: 1,
          user_id: 1,
          exercise_type: 'squat',
          video_url: 'https://example.com/video1.mp4',
          score: 85,
          overall_feedback: 'Good form overall',
          issues: ['Slight knee valgus'],
          created_at: new Date().toISOString(),
          status: 'completed',
          updated_at: new Date().toISOString(),
        }
      ])
    );
  }),
  
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const id = req.params.id as string;
    return res(
      ctx.status(200),
      ctx.json({
        id: parseInt(id),
        user_id: 1,
        exercise_type: 'squat',
        video_url: 'https://example.com/video1.mp4',
        score: 85,
        overall_feedback: 'Good form overall',
        issues: ['Slight knee valgus'],
        created_at: new Date().toISOString(),
        status: 'completed',
        updated_at: new Date().toISOString(),
      })
    );
  }),
];

// Establish API mocking before all tests.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished.
afterAll(() => server.close());

// Test server usage:
// 1. Import server & handlers in tests
// 2. Call server.listen() in beforeAll
// 3. Call server.resetHandlers() in afterEach
// 4. Call server.close() in afterAll 
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Define common request handlers
export const commonHandlers = [
  rest.get('/api/user', (req, res, ctx) => {
    return res(ctx.json({ 
      id: '1', 
      name: 'Test User', 
      email: 'test@example.com' 
    }));
  }),
  
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
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
  
  rest.post('/api/auth/logout', (req, res, ctx) => {
    return res(ctx.json({ success: true }));
  }),
  
  rest.get('/api/form-checks', (req, res, ctx) => {
    return res(
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

// Create the server with default handlers
export const server = setupServer(...commonHandlers);

// Test server usage:
// 1. Import server & handlers in tests
// 2. Call server.listen() in beforeAll
// 3. Call server.resetHandlers() in afterEach
// 4. Call server.close() in afterAll 
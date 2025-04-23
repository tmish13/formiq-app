import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Default handlers for common API endpoints
const handlers = [
  rest.get('/api/user', (req, res, ctx) => {
    return res(ctx.json({ id: '1', name: 'Test User', email: 'test@example.com' }));
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
    const { id } = req.params;
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
const server = setupServer(...handlers);

// Export both the server and the handlers
export { server, handlers }; 
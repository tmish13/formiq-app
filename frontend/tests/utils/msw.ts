import { setupServer } from 'msw/node';
import { rest } from 'msw';

/**
 * MSW (Mock Service Worker) configuration for API mocking in tests.
 * This file provides the global setup of MSW and default handlers.
 */

// Define default handlers for common API endpoints
export const defaultHandlers = [
  // Auth endpoints
  rest.post('/api/auth/login', (req, res, ctx) => {
    const { email, password } = req.body as any;
    
    if (email === 'test@example.com' && password === 'password123') {
      return res(
        ctx.status(200),
        ctx.json({
          token: 'mock-jwt-token',
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            role: 'user',
          }
        })
      );
    }
    
    return res(
      ctx.status(401),
      ctx.json({ error: 'Invalid credentials' })
    );
  }),
  
  rest.post('/api/auth/register', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        user: {
          id: '2',
          email: (req.body as any)?.email || 'new@example.com',
          name: (req.body as any)?.name || 'New User',
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
  
  // User profile
  rest.get('/api/users/me', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
        created_at: '2023-01-01T00:00:00.000Z',
        updated_at: '2023-01-01T00:00:00.000Z'
      })
    );
  }),
  
  // Form check endpoints
  rest.get('/api/form-checks', (_, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: '1',
          user_id: '1',
          exercise_type: 'squat',
          video_url: 'https://example.com/video1.mp4',
          score: 85,
          feedback: 'Good form overall',
          issues: ['Slight knee valgus'],
          created_at: '2023-01-01T00:00:00.000Z',
          status: 'completed',
        },
        {
          id: '2',
          user_id: '1',
          exercise_type: 'pushup',
          video_url: 'https://example.com/video2.mp4',
          score: 72,
          feedback: 'Form needs improvement',
          issues: ['Elbows flaring', 'Core not engaged'],
          created_at: '2023-01-02T00:00:00.000Z',
          status: 'completed',
        }
      ])
    );
  }),
  
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const id = req.params.id as string;
    
    return res(
      ctx.status(200),
      ctx.json({
        id,
        user_id: '1',
        exercise_type: 'squat',
        video_url: 'https://example.com/video1.mp4',
        score: 85,
        feedback: 'Good form overall',
        issues: ['Slight knee valgus'],
        created_at: '2023-01-01T00:00:00.000Z',
        status: 'completed',
        analysis_data: {
          frames: [/* pose data would go here */],
          angles: {
            knees: [75, 80, 78],
            hips: [110, 105, 108],
            back: [170, 168, 172]
          }
        }
      })
    );
  }),
  
  // Add other common API endpoints as needed
];

// Create and export the MSW server
export const server = setupServer(...defaultHandlers);

/**
 * Setup MSW for a test file
 * Usage:
 * ```
 * import { setupMockServer } from '../utils/msw';
 * const server = setupMockServer();
 * ```
 * @param customHandlers Optional additional handlers for specific tests
 */
export const setupMockServer = (customHandlers: any[] = []) => {
  // Add custom handlers if provided
  if (customHandlers.length > 0) {
    server.use(...customHandlers);
  }
  
  // Setup and return server with test lifecycle hooks
  beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  
  return server;
};

// Export convenience function for creating response data
export const mockResponse = <T>(data: T, status = 200) => {
  return (req: any, res: any, ctx: any) => {
    return res(
      ctx.status(status),
      ctx.json(data)
    );
  };
}; 
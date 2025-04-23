import { rest } from 'msw';

/**
 * Default mock responses for common API endpoints
 */
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  username: 'testuser',
  roles: ['user'],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  subscription_tier: 'basic',
  subscription_end_date: new Date(Date.now() + 86400000).toISOString(),
  is_email_verified: true,
  preferences: {
    theme: 'light',
    notifications: true
  }
};

export const mockTokens = {
  accessToken: 'mock-jwt-token',
  refreshToken: 'mock-refresh-token',
  expiresIn: 3600
};

export const mockFormCheck = {
  id: 'fc-123',
  user_id: 'user-123',
  exercise_type: 'squat',
  video_url: 'https://example.com/video.mp4',
  status: 'completed',
  score: 95,
  feedback: [
    { timestamp: 1.5, message: 'Good depth', severity: 'success' },
    { timestamp: 3.2, message: 'Keep your back straight', severity: 'warning' }
  ],
  created_at: '2024-01-01T12:00:00Z',
  updated_at: '2024-01-01T12:30:00Z'
};

/**
 * Mock MSW handlers for common API endpoints
 */
export const handlers = [
  // Auth endpoints
  rest.post('*/auth/login', (req, res, ctx) => {
    return res(
      ctx.json({ 
        user: mockUser, 
        tokens: mockTokens 
      })
    );
  }),
  
  rest.post('*/auth/register', (req, res, ctx) => {
    return res(
      ctx.json({ 
        user: mockUser, 
        tokens: mockTokens 
      })
    );
  }),
  
  rest.post('*/auth/logout', (req, res, ctx) => {
    return res(
      ctx.json({ success: true })
    );
  }),
  
  rest.post('*/auth/refresh', (req, res, ctx) => {
    return res(
      ctx.json({ tokens: mockTokens })
    );
  }),
  
  rest.get('*/auth/me', (req, res, ctx) => {
    return res(
      ctx.json(mockUser)
    );
  }),
  
  // Form checks endpoints
  rest.get('*/form-checks', (req, res, ctx) => {
    return res(
      ctx.json([mockFormCheck])
    );
  }),
  
  rest.get('*/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.json({
        ...mockFormCheck,
        id
      })
    );
  }),
  
  rest.post('*/form-checks', (req, res, ctx) => {
    return res(
      ctx.json(mockFormCheck)
    );
  }),
  
  rest.post('*/form-checks/upload', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'upload-123',
        url: 'https://example.com/uploaded-video.mp4'
      })
    );
  }),
  
  rest.delete('*/form-checks/:id', (req, res, ctx) => {
    return res(
      ctx.status(204)
    );
  }),
  
  // Error handlers
  rest.get('*/error/404', (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({ message: 'Resource not found' })
    );
  }),
  
  rest.get('*/error/401', (req, res, ctx) => {
    return res(
      ctx.status(401),
      ctx.json({ message: 'Unauthorized' })
    );
  }),
  
  rest.get('*/error/500', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ message: 'Internal server error' })
    );
  }),
  
  // CSRF token
  rest.get('*/api/v1/auth/csrf-token', (req, res, ctx) => {
    return res(
      ctx.json({ token: 'mock-csrf-token' })
    );
  }),
  
  // Test endpoint for basic sanity checks
  rest.get('/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Test successful' }));
  }),
  
  // Fallback handler for unmocked requests
  rest.all('*', (req, res, ctx) => {
    console.warn(`Unhandled ${req.method} request to ${req.url.toString()}`);
    
    return res(
      ctx.status(501),
      ctx.json({ message: 'Not implemented in MSW' })
    );
  }),
]; 
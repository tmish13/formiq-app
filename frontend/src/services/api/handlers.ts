import { rest } from 'msw'
import type { RequestHandler } from 'msw'

const baseUrl = process.env.REACT_APP_API_URL || '/api';

/**
 * TODO: Fix MSW type issues properly by either:
 * 1. Creating proper type definitions for MSW v1.3.2
 * 2. Upgrading to MSW v2 which has better TypeScript support
 * 3. Implementing correct response types for all handlers
 * Current solution uses @ts-ignore as a temporary workaround
 */

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
  feedback_items: [
    { 
      type: 'form',
      description: 'Good depth',
      severity: 'low',
      suggestions: '',
      timestamp: 1.5
    },
    { 
      type: 'form',
      description: 'Keep your back straight',
      severity: 'medium',
      suggestions: 'Engage your core',
      timestamp: 3.2
    }
  ],
  created_at: '2024-01-01T12:00:00Z',
  updated_at: '2024-01-01T12:30:00Z'
};

/**
 * Mock MSW handlers for common API endpoints
 */
export const handlers: RequestHandler[] = [
  // Auth endpoints
  rest.post(`${baseUrl}/auth/login`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'mock-token',
        user: {
          id: 1,
          email: 'test@example.com',
          name: 'Test User'
        }
      })
    );
  }),

  rest.post(`${baseUrl}/auth/register`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'mock-token',
        user: {
          id: 1,
          email: 'test@example.com',
          name: 'Test User'
        }
      })
    );
  }),
  
  rest.post('/api/auth/logout', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  }),
  
  rest.post('/api/auth/refresh', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ tokens: mockTokens })
    );
  }),
  
  rest.get('/api/auth/me', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(mockUser)
    );
  }),
  
  // Form checks endpoints
  rest.get(`${baseUrl}/form-checks`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: 1,
          status: 'completed',
          exercise_type: 'squat',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
          feedback_items: []
        }
      ])
    );
  }),
  
  rest.get(`${baseUrl}/form-checks/:id`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 1,
        status: 'completed',
        exercise_type: 'squat',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        feedback_items: []
      })
    );
  }),
  
  rest.post(`${baseUrl}/form-checks`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 1,
        status: 'pending',
        exercise_type: 'squat',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        feedback_items: []
      })
    );
  }),
  
  rest.post('/api/form-checks/upload', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 'upload-123',
        url: 'https://example.com/uploaded-video.mp4'
      })
    );
  }),
  
  rest.delete('/api/form-checks/:id', (req, res, ctx) => {
    return res(ctx.status(204));
  }),
  
  // Error handlers
  rest.get('/api/error/404', (req, res, ctx) => {
    return res(ctx.status(404));
  }),
  
  rest.get('/api/error/401', (req, res, ctx) => {
    return res(
      ctx.status(401),
      ctx.json({ message: 'Unauthorized' })
    );
  }),
  
  rest.get('/api/error/500', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ message: 'Internal server error' })
    );
  }),
  
  // CSRF token
  rest.get('/api/v1/auth/csrf-token', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ token: 'mock-csrf-token' })
    );
  }),
  
  // Test endpoint for basic sanity checks
  rest.get('/api/test', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ message: 'Test successful' })
    );
  }),
  
  // Social endpoints
  rest.get(`${baseUrl}/social/workouts`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([mockFormCheck])
    );
  }),

  // Fallback handler for unmocked requests
  rest.all('*', (req, res, ctx) => {
    console.warn(`Unhandled ${req.method} request to ${req.url}`);
    return res(
      ctx.status(404),
      ctx.json({ error: 'Not Found' })
    );
  })
] 
import { rest } from 'msw';
import { workoutHandlers } from './workout-handlers';

const baseUrl = process.env.REACT_APP_API_URL || '/api';

// Default mock data
const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  isActive: true,
  subscription: {
    tier: 'free',
    expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
};

// Mock tokens for auth tests
const mockTokens = {
  access: 'mock-access-token',
  refresh: 'mock-refresh-token',
};

const mockFormChecks = [
  {
    id: 'fc-1',
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    status: 'completed',
    analysis: {
      overall_score: 85,
      feedback: 'Good form overall, work on depth',
      scores: {
        posture: 90,
        stability: 80,
        depth: 85,
      },
    },
    created_at: new Date().toISOString(),
  },
];

export const handlers = [
  // Auth endpoints - exact URL matching
  rest.post('http://localhost:8000/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: mockTokens.access,
        refresh_token: mockTokens.refresh,
        user: mockUser,
      })
    );
  }),

  rest.post('http://localhost:8000/api/v1/auth/refresh', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'new-access-token',
        expires_in: 3600,
      })
    );
  }),

  rest.post('http://localhost:8000/api/v1/auth/logout', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ success: true }));
  }),

  // Form check endpoints
  rest.get('http://localhost:8000/api/v1/form-checks/history', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json(mockFormChecks));
  }),

  rest.post('http://localhost:8000/api/v1/form-checks', async (req, res, ctx) => {
    const data = await req.json();
    const newFormCheck = {
      id: `fc-${Date.now()}`,
      ...data,
      status: 'processing',
      created_at: new Date().toISOString(),
    };
    
    return res(ctx.status(201), ctx.json(newFormCheck));
  }),

  rest.get('http://localhost:8000/api/v1/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = mockFormChecks.find(fc => fc.id === id);

    if (!formCheck) {
      return res(ctx.status(404));
    }
    
    return res(ctx.status(200), ctx.json(formCheck));
  }),
];
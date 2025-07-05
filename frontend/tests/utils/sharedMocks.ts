/**
 * Shared Mock Utilities for API Integration Tests
 * Provides standardized mock data and MSW setup functions
 */

import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Mock data factories
export const createMockUser = (overrides: Partial<any> = {}) => ({
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  isActive: true,
  subscription: {
    tier: 'free',
    expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  },
  ...overrides
});

export const createMockFormCheck = (overrides: Partial<any> = {}) => ({
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
  ...overrides
});

export const createMockFormChecks = (count: number = 2) => {
  return Array.from({ length: count }, (_, i) => 
    createMockFormCheck({ 
      id: `fc-${i + 1}`,
      exercise_type: i % 2 === 0 ? 'squat' : 'pushup'
    })
  );
};

// Health check handler for API status tests
export const healthHandlers = [
  // Relative URL for test components
  rest.get('/api/health', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ status: 'ok', timestamp: new Date().toISOString() })
    );
  }),
  // Absolute URL for apiService calls
  rest.get('http://localhost:8000/api/v1/health', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ status: 'ok', timestamp: new Date().toISOString() })
    );
  }),
];

// User handlers for profile tests
export const userHandlers = [
  // Relative URL for test components
  rest.get('/api/users/:userId', (req, res, ctx) => {
    const { userId } = req.params;
    
    if (userId === 'user-123') {
      return res(
        ctx.status(200),
        ctx.json(createMockUser({ id: userId }))
      );
    }
    
    return res(
      ctx.status(404),
      ctx.json({ error: 'User not found' })
    );
  }),

  rest.get('/api/users/me', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(createMockUser())
    );
  }),

  // Absolute URL for apiService calls
  rest.get('http://localhost:8000/api/v1/users/:userId', (req, res, ctx) => {
    const { userId } = req.params;
    
    if (userId === 'user-123') {
      return res(
        ctx.status(200),
        ctx.json(createMockUser({ id: userId }))
      );
    }
    
    return res(
      ctx.status(404),
      ctx.json({ error: 'User not found' })
    );
  }),

  rest.get('http://localhost:8000/api/v1/users/me', (req, res, ctx) => {
    console.log('🎯 MSW Handler hit for GET /users/me');
    return res(
      ctx.status(200),
      ctx.json(createMockUser())
    );
  }),
];

// Auth handlers - supporting both relative and absolute URLs
export const authHandlers = [
  // Relative URLs for test components
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        user: createMockUser(),
      })
    );
  }),

  rest.post('/api/auth/refresh', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'new-access-token',
        expires_in: 3600,
      })
    );
  }),

  rest.post('/api/auth/logout', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ success: true }));
  }),

  // Absolute URLs for apiService calls (already exists in handlers.ts, keeping for completeness)
  rest.post('http://localhost:8000/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        user: createMockUser(),
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
];

// Form check handlers - supporting both relative and absolute URLs
export const formCheckHandlers = [
  // Relative URLs for test components
  rest.get('/api/form-checks', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json(createMockFormChecks()));
  }),

  rest.post('/api/form-checks', async (req, res, ctx) => {
    const data = await req.json();
    const newFormCheck = createMockFormCheck({
      id: `fc-${Date.now()}`,
      ...data,
      status: 'processing',
    });
    
    return res(ctx.status(201), ctx.json(newFormCheck));
  }),

  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = createMockFormCheck({ id });
    return res(ctx.status(200), ctx.json(formCheck));
  }),

  rest.delete('/api/form-checks/:id', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json({ success: true }));
  }),

  // Absolute URLs for apiService calls (already exists in handlers.ts)
  rest.get('http://localhost:8000/api/v1/form-checks/history', (req, res, ctx) => {
    return res(ctx.status(200), ctx.json(createMockFormChecks()));
  }),

  rest.post('http://localhost:8000/api/v1/form-checks', async (req, res, ctx) => {
    const data = await req.json();
    const newFormCheck = createMockFormCheck({
      id: `fc-${Date.now()}`,
      ...data,
      status: 'processing',
    });
    
    return res(ctx.status(201), ctx.json(newFormCheck));
  }),

  rest.get('http://localhost:8000/api/v1/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = createMockFormCheck({ id });
    return res(ctx.status(200), ctx.json(formCheck));
  }),
];

// Exercise handlers for library tests
export const exerciseHandlers = [
  // Relative URLs for test components
  rest.get('/api/exercises', (req, res, ctx) => {
    const category = req.url.searchParams.get('category');
    const exercises = [
      { id: 'ex1', name: 'Squat', category: 'legs', difficulty: 'intermediate' },
      { id: 'ex2', name: 'Push-up', category: 'chest', difficulty: 'beginner' },
      { id: 'ex3', name: 'Deadlift', category: 'legs', difficulty: 'advanced' },
      { id: 'ex4', name: 'Bench Press', category: 'chest', difficulty: 'intermediate' },
      { id: 'ex5', name: 'Plank', category: 'core', difficulty: 'beginner' }
    ];

    if (category) {
      return res(ctx.json({
        items: exercises.filter(ex => ex.category === category)
      }));
    }
    
    return res(ctx.json({ items: exercises }));
  }),

  rest.get('/api/exercises/:id', (req, res, ctx) => {
    const { id } = req.params;
    const exercise = {
      id,
      name: 'Squat',
      category: 'legs',
      difficulty: 'intermediate',
      description: 'A fundamental lower body exercise',
      instructions: ['Stand with feet shoulder-width apart', 'Lower down as if sitting in a chair', 'Return to standing position']
    };
    
    return res(ctx.status(200), ctx.json(exercise));
  }),

  // Absolute URLs for apiService calls
  rest.get('http://localhost:8000/api/v1/exercises', (req, res, ctx) => {
    const category = req.url.searchParams.get('category');
    const exercises = [
      { id: 'ex1', name: 'Squat', category: 'legs', difficulty: 'intermediate' },
      { id: 'ex2', name: 'Push-up', category: 'chest', difficulty: 'beginner' },
      { id: 'ex3', name: 'Deadlift', category: 'legs', difficulty: 'advanced' },
      { id: 'ex4', name: 'Bench Press', category: 'chest', difficulty: 'intermediate' },
      { id: 'ex5', name: 'Plank', category: 'core', difficulty: 'beginner' }
    ];

    if (category) {
      return res(ctx.json({
        items: exercises.filter(ex => ex.category === category)
      }));
    }
    
    return res(ctx.json({ items: exercises }));
  }),

  rest.get('http://localhost:8000/api/v1/exercises/:id', (req, res, ctx) => {
    const { id } = req.params;
    const exercise = {
      id,
      name: 'Squat',
      category: 'legs',
      difficulty: 'intermediate',
      description: 'A fundamental lower body exercise',
      instructions: ['Stand with feet shoulder-width apart', 'Lower down as if sitting in a chair', 'Return to standing position']
    };
    
    return res(ctx.status(200), ctx.json(exercise));
  }),
];

// Server setup functions
export const setupMockServer = (additionalHandlers: any[] = []) => {
  const allHandlers = [
    ...healthHandlers,
    ...userHandlers, 
    ...authHandlers, 
    ...formCheckHandlers,
    ...exerciseHandlers,
    ...additionalHandlers
  ];
  return setupServer(...allHandlers);
};

export const setupServerLifecycle = (server: any) => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  return server;
};
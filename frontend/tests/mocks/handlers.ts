import { http, HttpResponse } from 'msw';
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

const mockWorkouts = [
  {
    id: 'workout-1',
    name: 'Full Body Workout',
    description: 'A complete workout for the entire body',
    exercises: [
      { id: 'ex-1', name: 'Squat', sets: 3, reps: 10 },
      { id: 'ex-2', name: 'Push-up', sets: 3, reps: 15 },
    ],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'workout-2',
    name: 'Upper Body Focus',
    description: 'Focusing on chest, back, and arms',
    exercises: [
      { id: 'ex-3', name: 'Bench Press', sets: 4, reps: 8 },
      { id: 'ex-4', name: 'Pull-up', sets: 3, reps: 8 },
    ],
    createdAt: new Date().toISOString(),
  },
];

const mockFormChecks = [
  {
    id: 'fc-1',
    exercise: 'Squat',
    videoUrl: 'https://example.com/video1.mp4',
    feedback: [
      { timestamp: 1.5, message: 'Keep your back straight', severity: 'warning' },
      { timestamp: 3.2, message: 'Good depth', severity: 'success' },
    ],
    score: 85,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'fc-2',
    exercise: 'Deadlift',
    videoUrl: 'https://example.com/video2.mp4',
    feedback: [
      { timestamp: 2.0, message: 'Hips too high', severity: 'error' },
      { timestamp: 4.5, message: 'Good lockout', severity: 'success' },
    ],
    score: 72,
    createdAt: new Date().toISOString(),
  },
];

// MSW Handlers
export const handlers = [
  // Auth endpoints with v1 prefix for AuthContext tests
  http.post('/api/v1/auth/login', () => {
    return HttpResponse.json({
      user: mockUser,
      tokens: mockTokens,
    });
  }),

  http.post('/api/v1/auth/register', () => {
    return HttpResponse.json({
      user: mockUser,
      tokens: mockTokens,
    });
  }),

  http.get('/api/v1/auth/validate', () => {
    return HttpResponse.json(mockUser);
  }),

  http.post('/api/v1/auth/refresh', () => {
    return HttpResponse.json({
      tokens: mockTokens,
      user: mockUser,
    });
  }),

  http.post('/api/v1/auth/logout', () => {
    return HttpResponse.json({ success: true });
  }),

  // Original Auth endpoints
  http.post(`${baseUrl}/auth/login`, () => {
    return HttpResponse.json({
      user: mockUser,
      token: 'mock-jwt-token',
    });
  }),

  http.post(`${baseUrl}/auth/register`, () => {
    return HttpResponse.json({
      user: mockUser,
      token: 'mock-jwt-token',
    });
  }),

  http.get(`${baseUrl}/auth/me`, () => {
    return HttpResponse.json(mockUser);
  }),

  // Workout endpoints
  http.get(`${baseUrl}/workouts`, () => {
    return HttpResponse.json(mockWorkouts);
  }),

  http.get(`${baseUrl}/workouts/:id`, ({ params }) => {
    const id = params.id;
    const workout = mockWorkouts.find(w => w.id === id);

    if (!workout) {
      return new HttpResponse(null, { status: 404 });
    }
    
    return HttpResponse.json(workout);
  }),

  http.post(`${baseUrl}/workouts`, async ({ request }) => {
    const data = await request.json();
    const newWorkout = {
      id: `workout-${Date.now()}`,
      ...data,
      createdAt: new Date().toISOString(),
    };
    
    return HttpResponse.json(newWorkout, { status: 201 });
  }),

  http.put(`${baseUrl}/workouts/:id`, async ({ params, request }) => {
    const id = params.id;
    const data = await request.json();
    const workout = mockWorkouts.find(w => w.id === id);

    if (!workout) {
      return new HttpResponse(null, { status: 404 });
    }

    const updatedWorkout = { ...workout, ...data };
    return HttpResponse.json(updatedWorkout);
  }),

  http.delete(`${baseUrl}/workouts/:id`, ({ params }) => {
    const id = params.id;
    const workout = mockWorkouts.find(w => w.id === id);

    if (!workout) {
      return new HttpResponse(null, { status: 404 });
    }

    return HttpResponse.json({ success: true });
  }),

  // Form Check endpoints
  http.get(`${baseUrl}/form-checks`, () => {
    return HttpResponse.json(mockFormChecks);
  }),

  http.get(`${baseUrl}/form-checks/:id`, ({ params }) => {
    const id = params.id;
    const formCheck = mockFormChecks.find(fc => fc.id === id);

    if (!formCheck) {
      return new HttpResponse(null, { status: 404 });
    }
    
    return HttpResponse.json(formCheck);
  }),

  http.post(`${baseUrl}/form-checks`, async ({ request }) => {
    const data = await request.json();
    const newFormCheck = {
      id: `fc-${Date.now()}`,
      ...data,
      createdAt: new Date().toISOString(),
    };
    
    return HttpResponse.json(newFormCheck, { status: 201 });
  }),

  // Mock CSRF token endpoint
  http.get('/api/v1/auth/csrf-token', () => {
    return HttpResponse.json({ token: 'mock-csrf-token' }, { status: 200 });
  }),

  // Add handlers for form analysis endpoints
  http.get('/api/form-analysis/history', () => {
    return HttpResponse.json({
      data: [
        {
          confidence: 0.9,
          isReliable: true,
          keypoints: [],
          angles: {},
          feedback: [{
            type: 'success',
            message: 'Good form',
            confidence: 0.9,
            jointName: 'leftKnee'
          }],
          timestamp: Date.now()
        }
      ]
    });
  }),

  http.post('/api/form-analysis', () => {
    return new HttpResponse(null, { status: 200 });
  }),

  // Add test endpoint handlers
  http.get('/test', () => {
    return HttpResponse.json({ message: 'Success' }, { status: 200 });
  }),

  // Default handler for unmatched requests
  http.all('*', ({ request }) => {
    console.warn(`Unhandled request in MSW: ${request.method} ${request.url.toString()}`);
    return HttpResponse.json(
      { message: 'Not found - No MSW handler defined for this endpoint' },
      { status: 404 }
    );
  }),

  // Subscription endpoints
  http.get(`${baseUrl}/subscriptions/plans`, () => {
    return HttpResponse.json([
      {
        id: '1',
        name: 'Basic Plan',
        description: 'Basic features',
        price: 9.99,
        interval: 'monthly',
        features: ['Feature 1', 'Feature 2'],
        stripe_price_id: 'price_basic',
        stripe_product_id: 'prod_basic',
        is_popular: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: '2',
        name: 'Pro Plan',
        description: 'Pro features',
        price: 19.99,
        interval: 'monthly',
        features: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4'],
        stripe_price_id: 'price_pro',
        stripe_product_id: 'prod_pro',
        is_popular: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  }),

  http.post(`${baseUrl}/subscriptions`, () => {
    return HttpResponse.json({
      id: '1',
      user_id: mockUser.id,
      tier: 'pro',
      status: 'active',
      start_date: new Date().toISOString(),
      end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      cancel_at_period_end: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),

  // Include all workout handlers
  ...workoutHandlers
]; 
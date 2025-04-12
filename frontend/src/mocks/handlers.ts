import { rest } from 'msw';
import { ExerciseType, FormCheck, User, SubscriptionTier } from '../types';

const baseUrl = process.env.REACT_APP_API_URL || '/api';

const mockUser: User = {
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  subscription_tier: 'basic' as SubscriptionTier,
  subscription_end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockFormChecks: FormCheck[] = [
  {
    id: 1,
    user_id: 1,
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    score: 8.5,
    overall_feedback: 'Good form overall',
    issues: ['Slight knee valgus'],
    created_at: new Date().toISOString(),
    status: 'completed',
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    user_id: 1,
    exercise_type: 'deadlift',
    video_url: 'https://example.com/video2.mp4',
    score: 7.8,
    overall_feedback: 'Decent form with some issues',
    issues: ['Rounded back', 'Bar path not straight'],
    created_at: new Date().toISOString(),
    status: 'completed',
    updated_at: new Date().toISOString(),
  },
];

export const handlers = [
  // Auth endpoints
  rest.post(`${baseUrl}/auth/register`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: '123',
        email: 'test@example.com',
        token: 'fake-jwt-token'
      })
    );
  }),

  rest.post(`${baseUrl}/auth/login`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'fake-jwt-token',
        user: {
          id: '123',
          email: 'test@example.com',
          fullName: 'Test User'
        }
      })
    );
  }),

  rest.post(`${baseUrl}/auth/logout`, (req, res, ctx) => {
    return res(ctx.status(200));
  }),

  // Form check endpoints
  rest.post(`${baseUrl}/form-checks/analyze`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '456',
        exercise: 'squat',
        feedback: ['Good depth', 'Keep chest up'],
        score: 85
      })
    );
  }),

  rest.get(`${baseUrl}/form-checks`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: '456',
          exercise: 'squat',
          feedback: ['Good depth', 'Keep chest up'],
          score: 85,
          createdAt: new Date().toISOString()
        }
      ])
    );
  }),

  rest.get(`${baseUrl}/form-checks/:id`, (req, res, ctx) => {
    const id = req.params.id;
    return res(
      ctx.status(200),
      ctx.json({
        id,
        exercise: 'squat',
        feedback: ['Good depth', 'Keep chest up'],
        score: 85,
        createdAt: new Date().toISOString()
      })
    );
  }),

  // User endpoints
  rest.get(`${baseUrl}/users/me`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '123',
        email: 'test@example.com',
        fullName: 'Test User'
      })
    );
  }),

  // Subscription endpoints
  rest.get(`${baseUrl}/subscriptions/plans`, () => {
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
    ], { status: 200 });
  }),

  rest.post(`${baseUrl}/subscriptions`, () => {
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
    }, { status: 200 });
  }),

  rest.post(`${baseUrl}/form-checks`, async ({ request }) => {
    const formData = await request.json() as {
      exercise_type: ExerciseType;
      video_url: string;
    };
    
    const newFormCheck: FormCheck = {
      id: mockFormChecks.length + 1,
      user_id: 1,
      exercise_type: formData.exercise_type,
      video_url: formData.video_url,
      score: Math.round(Math.random() * 10 * 10) / 10,
      overall_feedback: 'Feedback will be generated after processing',
      issues: [],
      created_at: new Date().toISOString(),
      status: 'pending',
      updated_at: new Date().toISOString(),
    };

    return HttpResponse.json(newFormCheck, { status: 201 });
  }),
]; 
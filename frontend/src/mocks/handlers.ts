import { http, HttpResponse } from 'msw';
import { ExerciseType, FormCheck, User, SubscriptionTier } from '../types';

const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
  },
];

export const handlers = [
  // Auth endpoints
  http.post(`${baseUrl}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      user: mockUser,
    }, { status: 200 });
  }),

  http.post(`${baseUrl}/auth/register`, () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      user: mockUser,
    }, { status: 201 });
  }),

  http.post(`${baseUrl}/auth/logout`, () => {
    return new HttpResponse(null, { status: 200 });
  }),

  http.get(`${baseUrl}/users/me`, ({ request }) => {
    const auth = request.headers.get('Authorization');
    
    if (!auth?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }

    return HttpResponse.json(mockUser, { status: 200 });
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
    ], { status: 200 });
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
    }, { status: 200 });
  }),

  // Form checks endpoints
  http.get(`${baseUrl}/form-checks`, () => {
    return HttpResponse.json(mockFormChecks, { status: 200 });
  }),

  http.get(`${baseUrl}/form-checks/:id`, ({ params }) => {
    const formCheck = mockFormChecks.find(check => check.id === Number(params.id));
    
    if (!formCheck) {
      return HttpResponse.json(
        { detail: 'Form check not found' },
        { status: 404 }
      );
    }

    return HttpResponse.json(formCheck, { status: 200 });
  }),

  http.post(`${baseUrl}/form-checks`, async ({ request }) => {
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
    };

    return HttpResponse.json(newFormCheck, { status: 201 });
  }),
]; 
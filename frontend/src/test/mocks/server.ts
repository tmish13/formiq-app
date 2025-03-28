import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { rest } from 'msw';

const handlers = [
  // Auth endpoints
  http.post('/api/v1/auth/login', async () => {
    return HttpResponse.json({
      token: 'mock-token',
      refreshToken: 'mock-refresh-token',
      user: {
        id: '1',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
      },
    }, { status: 200 });
  }),

  http.post('/api/v1/auth/register', async () => {
    return HttpResponse.json({
      token: 'mock-token',
      refreshToken: 'mock-refresh-token',
      user: {
        id: '1',
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
      },
    }, { status: 201 });
  }),

  http.post('/api/v1/auth/refresh', async () => {
    return HttpResponse.json({
      token: 'new-mock-token',
      refreshToken: 'new-mock-refresh-token',
    }, { status: 200 });
  }),

  // Form check endpoints
  http.post('/api/v1/form-checks', async () => {
    return HttpResponse.json({
      id: '1',
      exerciseName: 'Squat',
      timestamp: new Date().toISOString(),
      feedback: [
        {
          type: 'success',
          message: 'Good form!',
        },
      ],
    }, { status: 201 });
  }),

  http.get('/api/v1/form-checks', async () => {
    return HttpResponse.json([
      {
        id: '1',
        exerciseName: 'Squat',
        timestamp: new Date().toISOString(),
        feedback: [
          {
            type: 'success',
            message: 'Good form!',
          },
        ],
      },
    ], { status: 200 });
  }),

  // Subscription endpoints
  http.get('/api/v1/subscriptions/plans', async () => {
    return HttpResponse.json([
      {
        id: '1',
        name: 'Basic',
        price: 9.99,
        features: ['Basic form analysis', '5 checks per month'],
        interval: 'monthly',
      },
    ], { status: 200 });
  }),

  http.get('/api/v1/subscriptions/current', async () => {
    return HttpResponse.json({
      id: '1',
      userId: '1',
      planId: '1',
      status: 'active',
      startDate: new Date().toISOString(),
      endDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      autoRenew: true,
    }, { status: 200 });
  }),
];

export const server = setupServer(...handlers); 
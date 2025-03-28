import { http, HttpResponse } from 'msw';

export const handlers = [
  // Auth endpoints
  http.post('/api/v1/auth/login', () => {
    return HttpResponse.json({
      access_token: 'mock-token',
      token_type: 'bearer',
    });
  }),

  // User endpoints
  http.get('/api/v1/users/me', () => {
    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      name: 'Test User',
    });
  }),

  // Form check endpoints
  http.post('/api/v1/form-checks', () => {
    return HttpResponse.json({
      id: 1,
      status: 'processing',
      created_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  http.get('/api/v1/form-checks/:id', () => {
    return HttpResponse.json({
      id: 1,
      status: 'completed',
      results: {
        score: 85,
        feedback: 'Good form overall',
      },
      created_at: new Date().toISOString(),
    });
  }),
]; 
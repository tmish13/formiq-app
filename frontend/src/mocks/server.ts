import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const handlers = [
  // Test API
  http.get('*/api/test', () => {
    return HttpResponse.json({ message: 'Success' });
  }),
  http.post('*/api/test', () => {
    return HttpResponse.json({ message: 'Success' });
  }),
  http.put('*/api/test', () => {
    return HttpResponse.json({ message: 'Success' });
  }),
  http.delete('*/api/test', () => {
    return HttpResponse.json({ message: 'Success' });
  }),
  
  // User API
  http.get('*/api/user', () => {
    return HttpResponse.json({ id: '1', name: 'Test User', email: 'test@example.com' });
  }),
  
  // Form Check API
  http.get('*/api/form-checks', () => {
    return HttpResponse.json([{ 
      id: 1, 
      user_id: 1,
      exercise_type: 'squat',
      video_url: 'https://example.com/video.mp4',
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }]);
  }),
  
  http.get('*/api/form-checks/:id', ({ params }) => {
    const { id } = params;
    return HttpResponse.json({ 
      id: Number(id), 
      user_id: 1,
      exercise_type: 'squat',
      video_url: 'https://example.com/video.mp4',
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }),
  
  http.post('*/api/form-checks', () => {
    return HttpResponse.json({ 
      id: 1, 
      user_id: 1,
      exercise_type: 'squat',
      video_url: 'https://example.com/video.mp4',
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }),
  
  http.post('*/api/form-checks/:id/complete', ({ params }) => {
    const { id } = params;
    return HttpResponse.json({ 
      id: Number(id), 
      user_id: 1,
      exercise_type: 'squat',
      video_url: 'https://example.com/video.mp4',
      status: 'completed',
      score: 85,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
  }),
  
  http.delete('*/api/form-checks/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),
  
  http.get('*/api/form-checks/exercise/:type', ({ params }) => {
    const { type } = params;
    return HttpResponse.json([{
      id: 1, 
      user_id: 1,
      exercise_type: type,
      video_url: 'https://example.com/video.mp4',
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }]);
  }),
  
  // Workout API
  http.get('*/api/workouts', () => {
    return HttpResponse.json([{
      id: '1',
      userId: 'user1',
      name: 'Test Workout', 
      description: 'Test Description', 
      exercises: [{ id: '1', name: 'Test Exercise', sets: 3, reps: 10, weight: 100, notes: 'Test Notes' }],
      duration: 60,
      difficulty: 'intermediate',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }]);
  }),
  
  http.get('*/api/workouts/:id', ({ params }) => {
    const { id } = params;
    return HttpResponse.json({
      id,
      userId: 'user1',
      name: 'Test Workout', 
      description: 'Test Description', 
      exercises: [{ id: '1', name: 'Test Exercise', sets: 3, reps: 10, weight: 100, notes: 'Test Notes' }],
      duration: 60,
      difficulty: 'intermediate',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
  }),
  
  http.post('*/api/workouts', () => {
    return HttpResponse.json({
      id: '1',
      userId: 'user1',
      name: 'Test Workout', 
      description: 'Test Description', 
      exercises: [{ id: '1', name: 'Test Exercise', sets: 3, reps: 10, weight: 100, notes: 'Test Notes' }],
      duration: 60,
      difficulty: 'intermediate',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
  }),
  
  // CSRF token for API requests
  http.get('*/api/v1/auth/csrf-token', () => {
    return HttpResponse.json({ csrf_token: 'test-csrf-token' });
  }),

  // Error handlers for testing
  http.get('*/error', () => {
    return HttpResponse.json(
      { message: 'Internal Server Error' },
      { status: 500 }
    );
  }),

  http.get('*/network-error', () => {
    return HttpResponse.error();
  }),

  http.get('*/timeout', async () => {
    await new Promise(resolve => setTimeout(resolve, 5000));
    return HttpResponse.json({});
  }),

  http.get('*/auth-error', () => {
    return HttpResponse.json(
      { message: 'Unauthorized' },
      { status: 401 }
    );
  }),
  
  http.post('*/validation-error', () => {
    return HttpResponse.json(
      {
        message: 'Validation Error',
        errors: ['Field is required'],
      },
      { status: 400 }
    );
  }),
  
  http.get('*/rate-limit', () => {
    return HttpResponse.json(
      { message: 'Too Many Requests' },
      { status: 429 }
    );
  }),
];

export const server = setupServer(...handlers); 
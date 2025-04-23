import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient } from '../../src/services/apiClient';
import { formAnalysisService } from '../../src/services/formAnalysisService';
import { exerciseRecommendationService } from '../../src/services/exerciseRecommendationService';
import { handlers } from '../../src/mocks/handlers';

// Set up test server with production-like endpoints
const server = setupServer(...handlers);

// Mock endpoints that simulate production behavior
const productionHandlers = [
  rest.get('/api/form-analysis/:id', (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.json({
        id,
        userId: 'user-123',
        exerciseType: 'squat',
        score: 85,
        feedback: 'Good form with minor adjustments needed.',
        issues: [
          {
            id: 'issue-1',
            area: 'knee',
            description: 'Knees caving inward slightly.',
            severity: 'medium',
            timestamp: 3.5,
            recommendations: ['Keep knees aligned with toes', 'Consider lower weight until form improves'],
          },
        ],
        videoUrl: 'https://storage.example.com/videos/analysis-123.mp4',
        thumbnailUrl: 'https://storage.example.com/thumbnails/analysis-123.jpg',
        createdAt: new Date().toISOString(),
      })
    );
  }),

  rest.post('/api/form-analysis/upload', async (req, res, ctx) => {
    // Simulate file processing delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    return res(
      ctx.json({
        id: 'analysis-123',
        status: 'processing',
        message: 'Your video is being processed. Please check back in a few minutes.',
      })
    );
  }),

  rest.get('/api/form-analysis/status/:id', (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.json({
        id,
        status: 'completed',
        progress: 100,
      })
    );
  }),

  rest.get('/api/exercises/recommendations', (req, res, ctx) => {
    const fitnessLevel = req.url.searchParams.get('fitnessLevel') || 'beginner';
    let exercises = [];
    
    switch (fitnessLevel) {
      case 'beginner':
        exercises = [
          { id: 'ex-1', name: 'Bodyweight Squat', level: 'beginner', muscleGroups: ['quadriceps', 'glutes'] },
          { id: 'ex-2', name: 'Push-ups (Modified)', level: 'beginner', muscleGroups: ['chest', 'triceps'] },
        ];
        break;
      case 'intermediate':
        exercises = [
          { id: 'ex-3', name: 'Barbell Squat', level: 'intermediate', muscleGroups: ['quadriceps', 'glutes'] },
          { id: 'ex-4', name: 'Dumbbell Bench Press', level: 'intermediate', muscleGroups: ['chest', 'triceps'] },
        ];
        break;
      case 'advanced':
        exercises = [
          { id: 'ex-5', name: 'Bulgarian Split Squat', level: 'advanced', muscleGroups: ['quadriceps', 'glutes'] },
          { id: 'ex-6', name: 'Weighted Dips', level: 'advanced', muscleGroups: ['chest', 'triceps'] },
        ];
        break;
    }
    
    return res(
      ctx.json({
        recommendations: exercises,
        plan: {
          name: `${fitnessLevel.charAt(0).toUpperCase() + fitnessLevel.slice(1)} workout plan`,
          frequency: fitnessLevel === 'beginner' ? 3 : fitnessLevel === 'intermediate' ? 4 : 5,
          exercises: exercises.map(ex => ({ ...ex, sets: 3, reps: 10 })),
        },
      })
    );
  }),

  // Add a deliberately slow endpoint to test loading states
  rest.get('/api/exercises/:id', async (req, res, ctx) => {
    const { id } = req.params;
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return res(
      ctx.json({
        id,
        name: 'Exercise Detail',
        description: 'Detailed exercise description',
        videoUrl: 'https://example.com/videos/exercise.mp4',
        muscleGroups: ['quadriceps', 'glutes'],
        equipment: ['barbell', 'rack'],
        difficulty: 'intermediate',
      })
    );
  }),

  // Add endpoint that returns different status codes
  rest.get('/api/health', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        status: 'healthy',
        version: '1.0.0',
        environment: 'test',
      })
    );
  }),

  // Edge case - 404 error
  rest.get('/api/nonexistent', (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({
        error: 'Resource not found',
        message: 'The requested resource does not exist.',
      })
    );
  }),

  // Edge case - 500 error
  rest.get('/api/error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({
        error: 'Internal server error',
        message: 'Something went wrong on the server.',
      })
    );
  }),

  // Edge case - Network timeout
  rest.get('/api/timeout', async (req, res, ctx) => {
    await new Promise(resolve => setTimeout(resolve, 5000)); // Delay longer than timeout
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  }),
];

beforeAll(() => {
  // Start the server and add production handlers
  server.listen();
  server.use(...productionHandlers);
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

// Configure API client for testing
apiClient.defaults.baseURL = 'http://localhost';
apiClient.defaults.timeout = 3000; // Set timeout for tests

describe('API Integration Tests', () => {
  it('successfully fetches form analysis data', async () => {
    const analysisId = 'analysis-123';
    const result = await formAnalysisService.getAnalysis(analysisId);
    
    expect(result).toBeDefined();
    expect(result.id).toBe(analysisId);
    expect(result.score).toBe(85);
    expect(result.issues).toHaveLength(1);
    expect(result.issues[0].area).toBe('knee');
  });

  it('handles form analysis upload with proper response', async () => {
    const mockFile = new File(['mock video content'], 'exercise.mp4', { type: 'video/mp4' });
    const result = await formAnalysisService.uploadVideo({
      video: mockFile,
      exerciseType: 'squat',
      userId: 'user-123',
    });
    
    expect(result).toBeDefined();
    expect(result.id).toBe('analysis-123');
    expect(result.status).toBe('processing');
  });

  it('checks analysis status correctly', async () => {
    const analysisId = 'analysis-123';
    const result = await formAnalysisService.checkStatus(analysisId);
    
    expect(result).toBeDefined();
    expect(result.id).toBe(analysisId);
    expect(result.status).toBe('completed');
    expect(result.progress).toBe(100);
  });

  it('fetches exercise recommendations based on fitness level', async () => {
    const beginner = await exerciseRecommendationService.getRecommendations({ fitnessLevel: 'beginner' });
    expect(beginner.recommendations).toHaveLength(2);
    expect(beginner.recommendations[0].level).toBe('beginner');
    expect(beginner.plan.frequency).toBe(3);
    
    const advanced = await exerciseRecommendationService.getRecommendations({ fitnessLevel: 'advanced' });
    expect(advanced.recommendations).toHaveLength(2);
    expect(advanced.recommendations[0].level).toBe('advanced');
    expect(advanced.plan.frequency).toBe(5);
  });

  it('handles 404 errors gracefully', async () => {
    try {
      await apiClient.get('/api/nonexistent');
      // Should not reach here
      fail('Should have thrown a 404 error');
    } catch (error) {
      expect(error.response.status).toBe(404);
      expect(error.response.data.error).toBe('Resource not found');
    }
  });

  it('handles 500 errors gracefully', async () => {
    try {
      await apiClient.get('/api/error');
      // Should not reach here
      fail('Should have thrown a 500 error');
    } catch (error) {
      expect(error.response.status).toBe(500);
      expect(error.response.data.error).toBe('Internal server error');
    }
  });

  it('handles network timeouts gracefully', async () => {
    try {
      await apiClient.get('/api/timeout');
      // Should not reach here
      fail('Should have thrown a timeout error');
    } catch (error) {
      expect(error.code).toBe('ECONNABORTED');
      expect(error.message).toContain('timeout');
    }
  });

  it('retries failed requests when configured', async () => {
    // Override handler to succeed on second try
    let attemptCount = 0;
    server.use(
      rest.get('/api/retry-test', (req, res, ctx) => {
        attemptCount++;
        if (attemptCount === 1) {
          return res(ctx.status(500));
        }
        return res(ctx.json({ success: true, attempt: attemptCount }));
      })
    );
    
    // Configure client with retry
    const clientWithRetry = apiClient.create({
      baseURL: 'http://localhost',
      timeout: 3000,
      retry: 1
    });
    
    const result = await clientWithRetry.get('/api/retry-test');
    expect(result.data.success).toBe(true);
    expect(result.data.attempt).toBe(2);
    expect(attemptCount).toBe(2);
  });
}); 
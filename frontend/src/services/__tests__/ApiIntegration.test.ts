import { rest } from 'msw';
import { setupServer } from 'msw/node';
import type { PathParams } from 'msw';
import { ApiService } from '../apiService';
import { formAnalysisService } from '../formAnalysisService';
import { exerciseRecommendationService } from '../exerciseRecommendationService';
import { ExerciseType } from '../exerciseLibraryService';
import type { Exercise } from '../exerciseLibraryService';
import type { ExerciseRecommendation, RecommendationRequest, RecommendationResponse } from '../exerciseRecommendationService';
import type { FormAnalysisResult } from '../../types/formAnalysis';
import type { AxiosError } from 'axios';

// Create a test subclass that exposes protected methods
class TestApiService extends ApiService {
  public get<T>(url: string, config?: any) {
    return super.get<T>(url, config);
  }

  public post<T>(url: string, data?: any, config?: any) {
    return super.post<T>(url, data, config);
  }

  public put<T>(url: string, data?: any, config?: any) {
    return super.put<T>(url, data, config);
  }

  public delete<T>(url: string, config?: any) {
    return super.delete<T>(url, config);
  }
}

// Create test server
const server = setupServer(
  // Mock successful response
  rest.get('/api/form-analysis/:id', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'test-id',
        status: 'completed',
        results: {
          score: 85,
          feedback: ['Good form']
        }
      })
    );
  }),

  // Mock 404 response
  rest.get('/api/nonexistent', (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({
        error: 'Resource not found',
        message: 'The requested resource does not exist'
      })
    );
  }),

  // Mock 500 response
  rest.get('/api/error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({
        error: 'Server error',
        message: 'Internal server error occurred'
      })
    );
  }),

  // Mock timeout response
  rest.get('/api/timeout', (req, res, ctx) => {
    return res(
      ctx.status(408),
      ctx.json({
        error: 'Request timeout',
        message: 'Request timed out'
      })
    );
  })
);

// Initialize test service
const apiService = new TestApiService('http://localhost');

describe('API Integration Tests', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('handles 404 errors gracefully', async () => {
    try {
      await apiService.get('/api/nonexistent');
      fail('Should have thrown a 404 error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.response?.status).toBe(404);
      expect(axiosError.message).toContain('Request failed with status code 404');
    }
  });

  it('handles 500 errors gracefully', async () => {
    try {
      await apiService.get('/api/error');
      fail('Should have thrown a 500 error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.response?.status).toBe(500);
      expect(axiosError.message).toContain('Request failed with status code 500');
    }
  });

  it('handles network timeouts gracefully', async () => {
    try {
      await apiService.get('/api/timeout');
      fail('Should have thrown a timeout error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.response?.status).toBe(408);
      expect(axiosError.message).toContain('Request failed with status code 408');
    }
  });
}); 
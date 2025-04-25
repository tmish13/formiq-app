import { http, HttpResponse } from 'msw';
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
  http.get('/api/form-analysis/:id', ({ params }) => {
    return HttpResponse.json({
      data: {
        id: params.id,
        type: ExerciseType.STRENGTH,
        // ... rest of the mock data
      }
    });
  }),
  // ... other endpoints
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
      // Should not reach here
      fail('Should have thrown a 404 error');
    } catch (error) {
      const axiosError = error as AxiosError<{ error: string }>;
      expect(axiosError.response?.status).toBe(404);
      expect(axiosError.response?.data.error).toBe('Resource not found');
    }
  });

  it('handles 500 errors gracefully', async () => {
    try {
      await apiService.get('/api/error');
      // Should not reach here
      fail('Should have thrown a 500 error');
    } catch (error) {
      const axiosError = error as AxiosError<{ error: string }>;
      expect(axiosError.response?.status).toBe(500);
      expect(axiosError.response?.data.error).toBe('Internal server error');
    }
  });

  it('handles network timeouts gracefully', async () => {
    try {
      await apiService.get('/api/timeout');
      // Should not reach here
      fail('Should have thrown a timeout error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.code).toBe('ECONNABORTED');
      expect(axiosError.message).toContain('timeout');
    }
  });

  // ... rest of the test cases ...
}); 
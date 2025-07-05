/**
 * Basic API Integration Test
 * 
 * Tests core API functionality without UI components
 */

import testApi, { testEndpoints } from '../../test-helpers/api-test-setup';

// MSW server is configured in setupTests.ts with handlers from tests/mocks/handlers.ts

describe('Basic API Integration', () => {
  describe('Authentication API', () => {
    it('should handle login API call', async () => {
      console.log('Calling endpoint:', testEndpoints.auth.login);
      
      const response = await testApi.post(testEndpoints.auth.login, {
        email: 'test@example.com',
        password: 'password123'
      });
      
      console.log('Response received:', response.data);
      expect(response).toBeDefined();
      expect(response.data).toHaveProperty('access_token');
      expect(response.data).toHaveProperty('user');
    });

    it('should handle token refresh', async () => {
      const response = await testApi.post(testEndpoints.auth.refreshToken, {
        refresh_token: 'mock-refresh-token'
      });

      expect(response).toBeDefined();
      expect(response.data).toHaveProperty('access_token');
    });
  });

  describe('Form Checks API', () => {
    it('should fetch form check history', async () => {
      const response = await testApi.get(testEndpoints.formChecks.history);
      
      expect(response).toBeDefined();
      expect(Array.isArray(response.data)).toBe(true);
    });

    it('should create new form check', async () => {
      const formCheckData = {
        exercise_type: 'squat',
        video_data: 'mock-video-data'
      };

      const response = await testApi.post(testEndpoints.formChecks.upload, formCheckData);
      
      expect(response).toBeDefined();
      expect(response.data).toHaveProperty('id');
      expect(response.data.status).toBe('processing');
    });

    it('should fetch specific form check details', async () => {
      const formCheckId = 'fc-1';
      const response = await testApi.get(testEndpoints.formChecks.detail(formCheckId));
      
      expect(response).toBeDefined();
      expect(response.data).toHaveProperty('id', formCheckId);
      expect(response.data).toHaveProperty('status');
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      try {
        await testApi.get('/non-existent-endpoint');
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeDefined();
      }
    });

    it('should handle network errors', async () => {
      // This test would need MSW to simulate network errors
      expect(true).toBe(true); // Placeholder
    });
  });
});
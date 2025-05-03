import { endpoints } from '../../config/api';

describe('API Configuration', () => {
  describe('API Endpoints', () => {
    it('should have all required auth endpoints', () => {
      expect(endpoints.auth).toHaveProperty('login');
      expect(endpoints.auth).toHaveProperty('register');
      expect(endpoints.auth).toHaveProperty('refreshToken');
      expect(endpoints.auth).toHaveProperty('logout');
    });
    
    it('should have all required user endpoints', () => {
      expect(endpoints.user).toHaveProperty('profile');
      expect(endpoints.user).toHaveProperty('update');
      expect(endpoints.user).toHaveProperty('subscription');
    });
    
    it('should have all required workout endpoints', () => {
      expect(endpoints.workouts).toHaveProperty('list');
      expect(endpoints.workouts).toHaveProperty('detail');
      expect(endpoints.workouts).toHaveProperty('create');
      expect(endpoints.workouts).toHaveProperty('update');
      expect(endpoints.workouts).toHaveProperty('delete');
      
      // Test dynamic endpoint generation
      expect(endpoints.workouts.detail('123')).toBe('/workouts/123');
      expect(endpoints.workouts.update('456')).toBe('/workouts/456');
      expect(endpoints.workouts.delete('789')).toBe('/workouts/789');
    });
    
    it('should have all required form checks endpoints', () => {
      expect(endpoints.formChecks).toHaveProperty('upload');
      expect(endpoints.formChecks).toHaveProperty('detail');
      expect(endpoints.formChecks).toHaveProperty('list');
      expect(endpoints.formChecks).toHaveProperty('delete');
      expect(endpoints.formChecks).toHaveProperty('complete');
      expect(endpoints.formChecks).toHaveProperty('feedback');
      
      // Test dynamic endpoint generation
      expect(endpoints.formChecks.detail('123')).toBe('/form-checks/123');
      expect(endpoints.formChecks.delete('456')).toBe('/form-checks/456');
      expect(endpoints.formChecks.complete('789')).toBe('/form-checks/789/complete');
      expect(endpoints.formChecks.feedback('abc')).toBe('/form-checks/abc/feedback');
    });
  });
}); 
/**
 * MSW Debug Test - Verify MSW is working
 */

import { server } from './mocks/server';
import { handlers } from './mocks/handlers';

describe('MSW Debug Test', () => {
  beforeAll(() => {
    console.log('🔧 MSW Debug: Total handlers loaded:', handlers.length);
    handlers.slice(0, 3).forEach((handler, i) => {
      console.log(`🔍 Handler ${i}:`, handler.info.header);
    });
  });

  it('should have MSW server available', () => {
    expect(server).toBeDefined();
    console.log('✅ MSW server is defined');
  });

  it('should have handlers loaded', () => {
    expect(handlers).toBeDefined();
    expect(handlers.length).toBeGreaterThan(0);
    console.log('✅ Handlers loaded:', handlers.length);
  });

  it('should make a simple fetch request', async () => {
    // Make a request that should be intercepted
    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'test@test.com', password: 'password' })
      });
      
      console.log('🌐 Fetch response status:', response.status);
      console.log('🌐 Fetch response ok:', response.ok);
      
      if (response.ok) {
        const data = await response.json();
        console.log('📦 Response data:', data);
        expect(data).toHaveProperty('access_token');
      } else {
        console.error('❌ Response not OK:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('💥 Fetch error:', error.message);
      console.error('🔍 Error details:', error);
    }
  });
});
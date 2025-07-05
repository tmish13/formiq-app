/**
 * Integration Test Setup for FormIQ
 * 
 * Provides utilities and setup for real backend integration testing,
 * mobile environment simulation, and comprehensive test infrastructure.
 */

import { beforeAll, afterAll, beforeEach, afterEach } from '@jest/globals';
import { getIntegrationConfig, IntegrationTestConfig } from './integration.config';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import fetch from 'node-fetch';

// Global test configuration
export const config = getIntegrationConfig();

// Mock server for fallback scenarios
export const mockServer = setupServer();

// Test utilities
export class IntegrationTestUtils {
  private static authToken: string | null = null;
  private static testUserId: string | null = null;

  /**
   * Setup real backend connection or mock fallback
   */
  static async setupBackend(): Promise<void> {
    if (config.backend.enableRealApi) {
      await this.setupRealBackend();
    } else {
      await this.setupMockBackend();
    }
  }

  /**
   * Setup connection to real backend
   */
  private static async setupRealBackend(): Promise<void> {
    try {
      // Test backend connectivity
      const healthResponse = await fetch(`${config.backend.baseUrl}/health`, {
        method: 'GET',
        timeout: config.backend.timeout,
      });

      if (!healthResponse.ok) {
        throw new Error(`Backend health check failed: ${healthResponse.status}`);
      }

      console.log('✅ Real backend connection established');
      
      // Authenticate test user if auth flow enabled
      if (config.auth.enableAuthFlow) {
        await this.authenticateTestUser();
      }
    } catch (error) {
      if (config.backend.mockFallback) {
        console.warn('⚠️ Real backend unavailable, falling back to mocks');
        await this.setupMockBackend();
      } else {
        throw new Error(`Backend setup failed: ${error}`);
      }
    }
  }

  /**
   * Setup mock backend for testing
   */
  private static async setupMockBackend(): Promise<void> {
    mockServer.use(
      // Health check endpoint
      rest.get(`${config.backend.baseUrl}/health`, (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ status: 'healthy', service: 'mock' }));
      }),

      // Authentication endpoints
      rest.post(`${config.backend.baseUrl}/auth/login`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            access_token: 'mock_access_token',
            refresh_token: 'mock_refresh_token',
            token_type: 'bearer',
            expires_in: 3600,
            user: {
              id: 'mock_user_id',
              email: config.auth.mockCredentials.username,
              first_name: 'Test',
              last_name: 'User',
            },
          })
        );
      }),

      // Token refresh endpoint
      rest.post(`${config.backend.baseUrl}/auth/refresh`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            access_token: 'new_mock_access_token',
            expires_in: 3600,
          })
        );
      }),

      // Video upload endpoints
      rest.post(`${config.backend.baseUrl}/videos/upload-url`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            upload_url: 'https://mock-s3-bucket.amazonaws.com/upload',
            video_id: 'mock_video_id',
            expires_at: new Date(Date.now() + 3600000).toISOString(),
          })
        );
      }),

      // Form analysis endpoints
      rest.post(`${config.backend.baseUrl}/form-analysis/analyze`, (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            analysis_id: 'mock_analysis_id',
            status: 'completed',
            scores: {
              posture_score: 85,
              stability_score: 78,
              overall_score: 82,
            },
            feedback: {
              summary: 'Good form overall. Work on knee tracking.',
              detailed_points: [
                'Keep knees aligned with toes',
                'Maintain upright torso',
                'Full depth achieved well',
              ],
            },
            timestamp: new Date().toISOString(),
          })
        );
      }),

      // WebSocket connection mock
      rest.get(`${config.backend.baseUrl}/ws/*`, (req, res, ctx) => {
        return res(ctx.status(101)); // WebSocket upgrade
      })
    );

    mockServer.listen({ onUnhandledRequest: 'warn' });
    console.log('🔧 Mock backend server started');
  }

  /**
   * Authenticate test user for real API testing
   */
  private static async authenticateTestUser(): Promise<void> {
    try {
      const response = await fetch(`${config.backend.baseUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: config.auth.mockCredentials.username,
          password: config.auth.mockCredentials.password,
        }),
      });

      if (!response.ok) {
        throw new Error(`Authentication failed: ${response.status}`);
      }

      const authData = await response.json();
      this.authToken = authData.access_token;
      this.testUserId = authData.user.id;
      
      console.log('✅ Test user authenticated');
    } catch (error) {
      throw new Error(`Test user authentication failed: ${error}`);
    }
  }

  /**
   * Get authentication headers for API requests
   */
  static getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  /**
   * Create a test video file for upload testing
   */
  static createTestVideoFile(): File {
    // Create a minimal MP4 file blob for testing
    const arrayBuffer = new ArrayBuffer(1024);
    const uint8Array = new Uint8Array(arrayBuffer);
    
    // Fill with mock MP4 header data
    uint8Array[0] = 0x00;
    uint8Array[1] = 0x00;
    uint8Array[2] = 0x00;
    uint8Array[3] = 0x20;
    
    const blob = new Blob([uint8Array], { type: 'video/mp4' });
    return new File([blob], 'test-video.mp4', { type: 'video/mp4' });
  }

  /**
   * Simulate mobile environment
   */
  static simulateMobileEnvironment(): void {
    if (config.mobile.simulateMobileEnvironment) {
      // Mock mobile user agent
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15',
      });

      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', { writable: true, value: 375 });
      Object.defineProperty(window, 'innerHeight', { writable: true, value: 812 });

      // Mock touch events
      window.TouchEvent = class TouchEvent extends Event {
        constructor(type: string, eventInitDict?: TouchEventInit) {
          super(type, eventInitDict);
        }
      } as any;

      console.log('📱 Mobile environment simulation enabled');
    }
  }

  /**
   * Setup Capacitor mocks for native feature testing
   */
  static setupCapacitorMocks(): void {
    if (config.mobile.testCapacitorPlugins) {
      // Mock Capacitor core
      (window as any).Capacitor = {
        isNativePlatform: () => true,
        getPlatform: () => 'ios',
        Plugins: {
          Camera: {
            getPhoto: jest.fn().mockResolvedValue({
              webPath: 'data:image/jpeg;base64,mock_image_data',
              format: 'jpeg',
            }),
            requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
          },
          Filesystem: {
            writeFile: jest.fn().mockResolvedValue({ uri: 'file://mock/path' }),
            readFile: jest.fn().mockResolvedValue({ data: 'mock_file_data' }),
          },
          Network: {
            getStatus: jest.fn().mockResolvedValue({
              connected: true,
              connectionType: 'wifi',
            }),
          },
          PushNotifications: {
            requestPermissions: jest.fn().mockResolvedValue({ receive: 'granted' }),
            register: jest.fn().mockResolvedValue(),
          },
        },
      };

      console.log('📲 Capacitor mocks initialized');
    }
  }

  /**
   * Cleanup test environment
   */
  static async cleanup(): Promise<void> {
    this.authToken = null;
    this.testUserId = null;
    
    if (mockServer.listHandlers().length > 0) {
      mockServer.resetHandlers();
    }
  }

  /**
   * Wait for async operations with timeout
   */
  static async waitFor(
    condition: () => boolean | Promise<boolean>,
    timeout: number = 5000,
    interval: number = 100
  ): Promise<void> {
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      const result = await condition();
      if (result) return;
      
      await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    throw new Error(`Condition not met within ${timeout}ms`);
  }
}

// Global setup and teardown
beforeAll(async () => {
  await IntegrationTestUtils.setupBackend();
  IntegrationTestUtils.simulateMobileEnvironment();
  IntegrationTestUtils.setupCapacitorMocks();
});

afterAll(async () => {
  await IntegrationTestUtils.cleanup();
  mockServer.close();
});

beforeEach(() => {
  // Reset any per-test state
  jest.clearAllMocks();
});

afterEach(() => {
  // Cleanup per-test state
  mockServer.resetHandlers();
});

export { IntegrationTestUtils };
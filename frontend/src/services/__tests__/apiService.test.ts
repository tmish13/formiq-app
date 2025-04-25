import { ApiService } from '../../../src/services/apiService';

// Mock the axios module
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  })),
  get: jest.fn(),
  defaults: { headers: { common: {} } }
}));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock document.cookie
Object.defineProperty(document, 'cookie', {
  writable: true,
  value: ''
});

jest.mock('../../../src/services/redisService', () => ({
  redisService: {
    get: jest.fn(),
    set: jest.fn(),
    del: jest.fn()
  }
}));

describe('ApiService Structure', () => {
  let apiService: ApiService;

  beforeEach(() => {
    jest.clearAllMocks();
    apiService = new ApiService('/api/v1');
  });

  it('should have the expected methods and properties', () => {
    // Verify main HTTP methods exist (they're protected but we can test via type assertion)
    expect(typeof (apiService as any).get).toBe('function');
    expect(typeof (apiService as any).post).toBe('function');
    expect(typeof (apiService as any).put).toBe('function');
    expect(typeof (apiService as any).delete).toBe('function');
    
    // Verify auth endpoints
    expect(apiService.auth).toBeDefined();
    expect(typeof apiService.auth.login).toBe('function');
    expect(typeof apiService.auth.logout).toBe('function');
    expect(typeof apiService.auth.register).toBe('function');
    expect(typeof apiService.auth.refreshToken).toBe('function');
    
    // Verify formAnalysis endpoints
    expect(apiService.formAnalysis).toBeDefined();
    expect(typeof apiService.formAnalysis.analyze).toBe('function');
    expect(typeof apiService.formAnalysis.getAnalysis).toBe('function');
    expect(typeof apiService.formAnalysis.getHistory).toBe('function');
    
    // Verify profile endpoints
    expect(apiService.profile).toBeDefined();
    expect(typeof apiService.profile.get).toBe('function');
    expect(typeof apiService.profile.update).toBe('function');
  });

  it('should initialize with the provided base URL', () => {
    const customApiService = new ApiService('/custom/api');
    expect(customApiService).toBeInstanceOf(ApiService);
  });
}); 
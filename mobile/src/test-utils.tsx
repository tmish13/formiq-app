import React from 'react';
import { render, RenderOptions } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import rootReducer from './store/rootReducer';

// Create a test store
export const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
  });
};

// Mock storage service
export class MockStorageService {
  private store: { [key: string]: string } = {};

  async get(key: string): Promise<string | null> {
    return this.store[key] || null;
  }

  async set(key: string, value: string): Promise<void> {
    this.store[key] = value;
  }

  async remove(key: string): Promise<void> {
    delete this.store[key];
  }

  async clear(): Promise<void> {
    this.store = {};
  }

  async keys(): Promise<string[]> {
    return Object.keys(this.store);
  }
}

// Mock network recovery service
export class MockNetworkRecoveryService {
  private isOnline = true;
  private pendingRequests: any[] = [];

  setOnline(online: boolean): void {
    this.isOnline = online;
  }

  async executeRequest(request: any): Promise<any> {
    if (!this.isOnline) {
      this.pendingRequests.push(request);
      throw new Error('Network offline');
    }
    return Promise.resolve({ status: 200, data: {} });
  }

  getPendingRequests(): any[] {
    return this.pendingRequests;
  }

  clearPendingRequests(): void {
    this.pendingRequests = [];
  }
}

// Custom render function that includes providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialState?: any;
  mockStorage?: MockStorageService;
  mockNetwork?: MockNetworkRecoveryService;
}

const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const store = createTestStore();
  const Stack = createNativeStackNavigator();
  
  return (
    <Provider store={store}>
      <NavigationContainer>
        <Stack.Navigator>
          <Stack.Screen name="Test" component={() => <>{children}</>} />
        </Stack.Navigator>
      </NavigationContainer>
    </Provider>
  );
};

const customRender = (
  ui: React.ReactElement,
  {
    initialState = {},
    mockStorage = new MockStorageService(),
    mockNetwork = new MockNetworkRecoveryService(),
    ...renderOptions
  }: CustomRenderOptions = {}
) => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    const store = createTestStore(initialState);
    const Stack = createNativeStackNavigator();
    
    return (
      <Provider store={store}>
        <NavigationContainer>
          <Stack.Navigator>
            <Stack.Screen name="Test" component={() => <>{children}</>} />
          </Stack.Navigator>
        </NavigationContainer>
      </Provider>
    );
  };

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    mockStorage,
    mockNetwork
  };
};

// Create a mock API error
export const createApiError = (
  status: number,
  message: string,
  code?: string,
  data?: unknown
) => ({
  name: 'ApiError',
  status,
  message,
  code,
  data,
  timestamp: new Date().toISOString()
});

// Mock response creator
export const createMockApiResponse = <T extends unknown>(data: T) => ({
  data,
  status: 200,
  metadata: {
    timestamp: new Date().toISOString(),
    requestId: Math.random().toString(36).substring(7)
  }
});

// Mock file creator
export const createMockFile = (
  name: string,
  type: string,
  size: number
) => {
  return {
    name,
    type,
    size,
    uri: `file://${name}`,
  };
};

// Mock Capacitor plugins
export const mockCapacitor = {
  Camera: {
    checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
    requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
    getPhoto: jest.fn().mockResolvedValue({
      path: 'path/to/photo.jpg',
      webPath: 'blob:photo.jpg',
      format: 'jpeg'
    })
  },
  Preferences: {
    get: jest.fn().mockResolvedValue({ value: 'test-token' }),
    set: jest.fn().mockResolvedValue(undefined)
  },
  Network: {
    getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
    addListener: jest.fn().mockReturnValue({ remove: jest.fn() })
  }
};

// Test data generators
export const generateTestUser = (overrides = {}) => ({
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  ...overrides
});

// re-export everything
export * from '@testing-library/react-native';

// override render method
export { customRender as render }; 
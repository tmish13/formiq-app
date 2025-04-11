import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from '../ThemeProvider';
import { Provider } from 'react-redux';
import { store } from '../store';
import { BrowserRouter } from 'react-router-dom';
import ErrorBoundary from '../components/ErrorBoundary';
import { ApiError } from '../services/apiService';

// Custom render function that includes providers
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => {
  const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    return (
      <Provider store={store}>
        <ThemeProvider>
          <BrowserRouter>
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    );
  };

  return render(ui, { wrapper: AllTheProviders, ...options });
};

// Create a mock API error
const createApiError = (
  status: number,
  message: string,
  code?: string,
  data?: unknown
): ApiError => ({
  name: 'ApiError',
  status,
  message,
  code,
  data,
  timestamp: new Date().toISOString()
});

// Mock response creator
const createMockApiResponse = <T extends unknown>(data: T) => ({
  data,
  status: 200,
  metadata: {
    timestamp: new Date().toISOString(),
    requestId: Math.random().toString(36).substring(7)
  }
});

// Mock form data helper
const createFormData = (obj: Record<string, any>): FormData => {
  const formData = new FormData();
  Object.entries(obj).forEach(([key, value]) => {
    if (value instanceof Blob) {
      formData.append(key, value);
    } else if (typeof value === 'object') {
      formData.append(key, JSON.stringify(value));
    } else {
      formData.append(key, String(value));
    }
  });
  return formData;
};

// Mock file creator
const createMockFile = (
  name: string,
  type: string,
  size: number
): File => {
  const file = new File([''], name, { type });
  Object.defineProperty(file, 'size', {
    get() {
      return size;
    }
  });
  return file;
};

// Mock video element
const createMockVideoElement = () => {
  const mockVideo = document.createElement('video');
  Object.defineProperty(mockVideo, 'readyState', {
    get() {
      return 4; // HAVE_ENOUGH_DATA
    }
  });
  Object.defineProperty(mockVideo, 'videoWidth', {
    get() {
      return 1280;
    }
  });
  Object.defineProperty(mockVideo, 'videoHeight', {
    get() {
      return 720;
    }
  });
  return mockVideo;
};

// Wait for element to be removed with timeout
const waitForElementToBeRemoved = async (
  callback: () => Element | null,
  timeout = 5000
) => {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (!callback()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Element not removed within timeout');
};

// Mock pose detection result
const createMockPoseDetection = (confidence = 0.9) => ({
  score: confidence,
  keypoints: [
    { x: 0, y: 0, score: confidence, name: 'nose' },
    { x: 10, y: 0, score: confidence, name: 'left_eye' },
    { x: -10, y: 0, score: confidence, name: 'right_eye' },
    // Add more keypoints as needed
  ]
});

export {
  customRender as render,
  createApiError,
  createMockApiResponse,
  createFormData,
  createMockFile,
  createMockVideoElement,
  waitForElementToBeRemoved,
  createMockPoseDetection
}; 
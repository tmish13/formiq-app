import React from 'react';
import { renderHook, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { useApi } from '../useApi';
import { AxiosProgressEvent } from 'axios';

interface TestResponse {
  message: string;
}

interface ApiConfig {
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
}

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (config?: ApiConfig) => Promise<T | null>;
  reset: () => void;
}

const mockData: TestResponse = { message: 'Success' };
const mockError: TestResponse = { message: 'Error occurred' };

const server = setupServer(
  http.get('/api/test', () => {
    return HttpResponse.json(mockData);
  }),
  http.post('/api/test', () => {
    return HttpResponse.json(mockData);
  }),
  http.put('/api/test', () => {
    return HttpResponse.json(mockData);
  }),
  http.delete('/api/test', () => {
    return HttpResponse.json(mockData);
  })
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  return React.createElement(MemoryRouter, null, children);
};

describe('useApi', () => {
  it('provides initial state', () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toBeNull();
  });

  it('handles GET request successfully', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(mockData);
  });

  it('handles GET request error', async () => {
    server.use(
      http.get('/api/test', () => {
        return new HttpResponse(JSON.stringify({ detail: 'Error occurred' }), { status: 500 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Error occurred');
    expect(result.current.data).toBeNull();
  });

  it('handles POST request successfully', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'post'));

    await act(async () => {
      await result.current.execute({ data: { test: 'data' } });
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(mockData);
  });

  it('handles POST request error', async () => {
    server.use(
      http.post('/api/test', () => {
        return new HttpResponse(JSON.stringify(mockError), { status: 500 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'post'));

    await act(async () => {
      await result.current.execute({ data: { test: 'data' } });
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Error occurred');
    expect(result.current.data).toBeNull();
  });

  it('handles PUT request successfully', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'put'));

    await act(async () => {
      await result.current.execute({ data: { test: 'data' } });
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(mockData);
  });

  it('handles PUT request error', async () => {
    server.use(
      http.put('/api/test', () => {
        return new HttpResponse(JSON.stringify(mockError), { status: 500 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'put'));

    await act(async () => {
      await result.current.execute({ data: { test: 'data' } });
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Error occurred');
    expect(result.current.data).toBeNull();
  });

  it('handles DELETE request successfully', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'delete'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(mockData);
  });

  it('handles DELETE request error', async () => {
    server.use(
      http.delete('/api/test', () => {
        return new HttpResponse(JSON.stringify(mockError), { status: 500 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test', 'delete'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Error occurred');
    expect(result.current.data).toBeNull();
  });

  it('sets loading state during request', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    let loadingDuringRequest = false;

    await act(async () => {
      result.current.execute().then(() => {
        loadingDuringRequest = result.current.loading;
      });
    });

    expect(loadingDuringRequest).toBe(true);
    expect(result.current.loading).toBe(false);
  });

  it('handles network errors', async () => {
    server.use(
      http.get('/api/test', () => {
        return new HttpResponse(null, { status: 0 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Network error occurred');
    expect(result.current.data).toBeNull();
  });

  it('handles unauthorized errors', async () => {
    server.use(
      http.get('/api/test', () => {
        return new HttpResponse(null, { status: 401 });
      })
    );

    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Unauthorized');
    expect(result.current.data).toBeNull();
  });

  it('clears error on new request', async () => {
    const { result } = renderHook(() => useApi<TestResponse>('/api/test'));

    server.use(
      http.get('/api/test', () => {
        return new HttpResponse(JSON.stringify(mockError), { status: 500 });
      })
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toBe('Error occurred');

    server.use(
      http.get('/api/test', () => {
        return HttpResponse.json(mockData);
      })
    );

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual(mockData);
  });
}); 
import { renderHook, act } from '@testing-library/react';
import { useApi } from './useApi';
import api from '../config/api';
import { apiCache } from '../utils/cache';

// Mock the API
jest.mock('../config/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('useApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    apiCache.clear();
  });

  it('should fetch data successfully', async () => {
    const mockData = { id: 1, name: 'test' };
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should handle errors', async () => {
    const errorMessage = 'API Error';
    mockedApi.request.mockRejectedValueOnce({
      response: { data: { detail: errorMessage } },
      message: errorMessage,
    });

    const { result } = renderHook(() => useApi('/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(errorMessage);
  });

  it('should handle network errors', async () => {
    mockedApi.request.mockRejectedValueOnce({
      message: 'Network Error',
    });

    const { result } = renderHook(() => useApi('/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Network Error');
  });

  it('should handle upload progress', async () => {
    const mockData = { id: 1, name: 'test' };
    const onUploadProgress = jest.fn();
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test'));

    await act(async () => {
      await result.current.execute({ onUploadProgress });
    });

    expect(mockedApi.request).toHaveBeenCalledWith(
      expect.objectContaining({
        onUploadProgress,
      })
    );
  });

  it('should cache GET requests', async () => {
    const mockData = { id: 1, name: 'test' };
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test'));

    // First request
    await act(async () => {
      await result.current.execute();
    });

    // Second request should use cached data
    mockedApi.request.mockClear();
    await act(async () => {
      await result.current.execute();
    });

    expect(mockedApi.request).not.toHaveBeenCalled();
    expect(result.current.data).toEqual(mockData);
  });

  it('should not cache non-GET requests', async () => {
    const mockData = { id: 1, name: 'test' };
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test', 'post'));

    // First request
    await act(async () => {
      await result.current.execute();
    });

    // Second request should not use cache
    mockedApi.request.mockClear();
    await act(async () => {
      await result.current.execute();
    });

    expect(mockedApi.request).toHaveBeenCalled();
  });

  it('should respect skipCache option', async () => {
    const mockData = { id: 1, name: 'test' };
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test'));

    // First request
    await act(async () => {
      await result.current.execute();
    });

    // Second request with skipCache should not use cache
    mockedApi.request.mockClear();
    await act(async () => {
      await result.current.execute({ skipCache: true });
    });

    expect(mockedApi.request).toHaveBeenCalled();
  });

  it('should reset state', async () => {
    const mockData = { id: 1, name: 'test' };
    mockedApi.request.mockResolvedValueOnce({ data: mockData });

    const { result } = renderHook(() => useApi('/test'));

    await act(async () => {
      await result.current.execute();
    });

    expect(result.current.data).toEqual(mockData);

    act(() => {
      result.current.reset();
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });
}); 
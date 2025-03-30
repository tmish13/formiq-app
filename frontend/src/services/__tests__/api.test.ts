import { apiService } from '../api';
import { server } from '../../mocks/server';
import { http, HttpResponse } from 'msw';
import { AxiosError } from 'axios';

interface ErrorResponse {
  message: string;
  errors?: string[];
}

describe('ApiService', () => {
  beforeAll(() => {
    server.listen();
  });

  afterEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  it('should make a GET request', async () => {
    const response = await apiService.get('/test');
    expect(response).toBeDefined();
  });

  it('should make a POST request', async () => {
    const data = { test: 'data' };
    const response = await apiService.post('/test', data);
    expect(response).toBeDefined();
  });

  it('should make a PUT request', async () => {
    const data = { test: 'data' };
    const response = await apiService.put('/test', data);
    expect(response).toBeDefined();
  });

  it('should make a DELETE request', async () => {
    const response = await apiService.delete('/test');
    expect(response).toBeDefined();
  });

  it('should handle errors', async () => {
    server.use(
      http.get('/error', () => {
        return HttpResponse.json(
          { message: 'Internal Server Error' },
          { status: 500 }
        );
      })
    );

    try {
      await apiService.get('/error');
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError<ErrorResponse>;
      expect(axiosError.response?.status).toBe(500);
      expect(axiosError.response?.data.message).toBe('Internal Server Error');
    }
  });

  it('should handle network errors', async () => {
    server.use(
      http.get('/network-error', () => {
        return HttpResponse.error();
      })
    );

    try {
      await apiService.get('/network-error');
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.message).toBe('Network Error');
    }
  });

  it('should handle request timeouts', async () => {
    server.use(
      http.get('/timeout', async () => {
        await new Promise(resolve => setTimeout(resolve, 5000));
        return HttpResponse.json({});
      })
    );

    try {
      await apiService.get('/timeout');
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError;
      expect(axiosError.code).toBe('ECONNABORTED');
    }
  });

  it('should handle authentication errors', async () => {
    server.use(
      http.get('/auth-error', () => {
        return HttpResponse.json(
          { message: 'Unauthorized' },
          { status: 401 }
        );
      })
    );

    try {
      await apiService.get('/auth-error');
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError<ErrorResponse>;
      expect(axiosError.response?.status).toBe(401);
      expect(axiosError.response?.data.message).toBe('Unauthorized');
    }
  });

  it('should handle validation errors', async () => {
    server.use(
      http.post('/validation-error', () => {
        return HttpResponse.json(
          {
            message: 'Validation Error',
            errors: ['Field is required'],
          },
          { status: 400 }
        );
      })
    );

    try {
      await apiService.post('/validation-error', {});
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError<ErrorResponse>;
      expect(axiosError.response?.status).toBe(400);
      expect(axiosError.response?.data.message).toBe('Validation Error');
      expect(axiosError.response?.data.errors).toEqual(['Field is required']);
    }
  });

  it('should handle rate limiting', async () => {
    server.use(
      http.get('/rate-limit', () => {
        return HttpResponse.json(
          { message: 'Too Many Requests' },
          { status: 429 }
        );
      })
    );

    try {
      await apiService.get('/rate-limit');
      fail('Should have thrown an error');
    } catch (error) {
      const axiosError = error as AxiosError<ErrorResponse>;
      expect(axiosError.response?.status).toBe(429);
      expect(axiosError.response?.data.message).toBe('Too Many Requests');
    }
  });
}); 
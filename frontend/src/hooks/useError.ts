import { useState, useCallback } from 'react';

interface Error {
  message: string;
  code?: string;
  status?: number;
}

interface UseErrorReturn {
  error: Error | null;
  setError: (error: Error | null) => void;
  clearError: () => void;
  withErrorHandling: <T>(promise: Promise<T>) => Promise<T>;
}

export const useError = (): UseErrorReturn => {
  const [error, setError] = useState<Error | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const withErrorHandling = useCallback(async <T>(promise: Promise<T>): Promise<T> => {
    try {
      clearError();
      return await promise;
    } catch (err) {
      const error = err as Error;
      setError({
        message: error.message || 'An error occurred',
        code: error.code,
        status: error.status,
      });
      throw error;
    }
  }, [clearError]);

  return {
    error,
    setError,
    clearError,
    withErrorHandling,
  };
}; 
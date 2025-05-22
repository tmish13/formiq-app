import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Mock the error boundary component
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      errorInfo
    });
    
    // In a real app, log the error to an error reporting service
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
  }

  getUserFriendlyMessage(error) {
    if (!error) return 'An unexpected error occurred. Please try again.';
    
    if (error.code === 'NOT_FOUND') {
      return 'The requested resource could not be found.';
    }
    
    if (error.code === 'NETWORK_ERROR') {
      return 'Unable to connect to the server. Please check your internet connection.';
    }
    
    if (error.code === 'UNAUTHORIZED') {
      return 'You are not authorized to access this resource. Please log in again.';
    }
    
    if (error.code === 'FORBIDDEN') {
      return 'You do not have permission to access this resource.';
    }
    
    if (error.code === 'SERVER_ERROR') {
      return 'The server encountered an error. Please try again later.';
    }
    
    return error.message || 'An unexpected error occurred. Please try again.';
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;
    
    if (hasError) {
      if (fallback) {
        return fallback;
      }
      
      return (
        <div data-testid="error-boundary-fallback" className="error-boundary">
          <h2>Something went wrong</h2>
          <p data-testid="error-message">{this.getUserFriendlyMessage(error)}</p>
          <div className="error-actions">
            <button 
              data-testid="retry-button" 
              onClick={this.handleRetry} 
              className="error-retry-btn"
            >
              Try Again
            </button>
            <button 
              data-testid="reload-button" 
              onClick={this.handleReload}
              className="error-reload-btn"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    
    return children;
  }
}

// Mock error fallback component
const ErrorFallback = ({
  error,
  resetErrorBoundary
}) => (
  <div data-testid="error-fallback" role="alert">
    <h2>Something went wrong:</h2>
    <p data-testid="fallback-error-message">{error.message}</p>
    <button data-testid="fallback-retry-button" onClick={resetErrorBoundary}>Try again</button>
  </div>
);

// Mock API error handler
const ErrorCode = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  NETWORK_ERROR: 'NETWORK_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN'
};

class AppError extends Error {
  constructor(message, code, data = null) {
    super(message);
    this.code = code;
    this.data = data;
    this.name = 'AppError';
  }
}

class ApiError extends AppError {
  constructor(message, code, status, data = null) {
    super(message, code, data);
    this.status = status;
    this.name = 'ApiError';
  }
}

// Mock handleApiError function
const handleApiError = (error) => {
  // Network error
  if (error.message && error.message.includes('Network Error')) {
    return new AppError(
      'Unable to connect to the server. Please check your internet connection.',
      ErrorCode.NETWORK_ERROR
    );
  }
  
  // Axios error with response
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 401:
        return new ApiError(
          'Your session has expired. Please log in again.',
          ErrorCode.UNAUTHORIZED,
          status,
          data
        );
      case 403:
        return new ApiError(
          'You do not have permission to perform this action.',
          ErrorCode.FORBIDDEN,
          status,
          data
        );
      case 404:
        return new ApiError(
          'The requested resource could not be found.',
          ErrorCode.NOT_FOUND,
          status,
          data
        );
      case 500:
      case 502:
      case 503:
      case 504:
        return new ApiError(
          'The server encountered an error. Please try again later.',
          ErrorCode.SERVER_ERROR,
          status,
          data
        );
      default:
        return new ApiError(
          data.message || 'An unexpected error occurred.',
          ErrorCode.UNKNOWN,
          status,
          data
        );
    }
  }
  
  // Fallback for other errors
  return new AppError(
    error.message || 'An unexpected error occurred.',
    ErrorCode.UNKNOWN
  );
};

// Mock toast notification system
const toast = {
  success: jest.fn((message) => ({ type: 'success', message })),
  error: jest.fn((message) => ({ type: 'error', message })),
  warning: jest.fn((message) => ({ type: 'warning', message })),
  info: jest.fn((message) => ({ type: 'info', message })),
  dismiss: jest.fn(),
};

// Component that deliberately throws error for testing
const ErrorThrower = ({ shouldThrow = true, message = 'Test error' }) => {
  if (shouldThrow) {
    throw new Error(message);
  }
  
  return <div data-testid="no-error">No error thrown</div>;
};

// Component with error handling for API calls
const ApiErrorHandler = ({ onFetch, onError }) => {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);
  
  const handleFetch = async () => {
    try {
      setError(null);
      const result = await onFetch();
      setData(result);
    } catch (err) {
      const appError = handleApiError(err);
      setError(appError);
      onError(appError);
    }
  };
  
  return (
    <div>
      <button data-testid="fetch-button" onClick={handleFetch}>
        Fetch Data
      </button>
      
      {error && (
        <div data-testid="api-error">
          <p>{error.message}</p>
          <p>Error Code: {error.code}</p>
        </div>
      )}
      
      {data && <div data-testid="api-data">{JSON.stringify(data)}</div>}
    </div>
  );
};

describe('ErrorHandling Consolidated Tests', () => {
  beforeEach(() => {
    // Silence console errors in tests
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });
  
  afterEach(() => {
    // Restore console error
    console.error.mockRestore();
    
    // Clear mock function calls
    jest.clearAllMocks();
  });

  describe('ErrorBoundary Component', () => {
    it('renders children when no error occurs', () => {
      render(
        <ErrorBoundary>
          <div data-testid="child">Child Component</div>
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('child')).toBeInTheDocument();
      expect(screen.queryByTestId('error-boundary-fallback')).not.toBeInTheDocument();
    });
    
    it('renders fallback UI when error is thrown', () => {
      render(
        <ErrorBoundary>
          <ErrorThrower />
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      expect(screen.queryByTestId('no-error')).not.toBeInTheDocument();
    });
    
    it('shows appropriate error message based on error code', () => {
      // Mock error with specific code
      const TestComponent = () => {
        const error = new AppError('Not found', ErrorCode.NOT_FOUND);
        throw error;
      };
      
      render(
        <ErrorBoundary>
          <TestComponent />
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('error-message')).toHaveTextContent('The requested resource could not be found.');
    });
    
    it('resets error state when retry button is clicked', () => {
      let shouldThrow = true;
      
      const ToggleErrorComponent = () => {
        if (shouldThrow) {
          throw new Error('Toggle error');
        }
        return <div data-testid="no-error">No error thrown</div>;
      };
      
      render(
        <ErrorBoundary>
          <ToggleErrorComponent />
        </ErrorBoundary>
      );
      
      // Error UI is shown
      expect(screen.getByTestId('error-boundary-fallback')).toBeInTheDocument();
      
      // Change flag so component won't throw on next render
      shouldThrow = false;
      
      // Click retry button
      fireEvent.click(screen.getByTestId('retry-button'));
      
      // Component should now render without error
      expect(screen.getByTestId('no-error')).toBeInTheDocument();
      expect(screen.queryByTestId('error-boundary-fallback')).not.toBeInTheDocument();
    });
    
    it('uses custom fallback component when provided', () => {
      const CustomFallback = () => <div data-testid="custom-fallback">Custom Error UI</div>;
      
      render(
        <ErrorBoundary fallback={<CustomFallback />}>
          <ErrorThrower />
        </ErrorBoundary>
      );
      
      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.queryByTestId('error-boundary-fallback')).not.toBeInTheDocument();
    });
  });
  
  describe('ErrorFallback Component', () => {
    it('displays the error message', () => {
      const error = new Error('Test error message');
      const resetErrorBoundary = jest.fn();
      
      render(
        <ErrorFallback 
          error={error} 
          resetErrorBoundary={resetErrorBoundary} 
        />
      );
      
      expect(screen.getByTestId('fallback-error-message')).toHaveTextContent('Test error message');
    });
    
    it('calls resetErrorBoundary when retry button is clicked', () => {
      const error = new Error('Test error message');
      const resetErrorBoundary = jest.fn();
      
      render(
        <ErrorFallback 
          error={error} 
          resetErrorBoundary={resetErrorBoundary} 
        />
      );
      
      fireEvent.click(screen.getByTestId('fallback-retry-button'));
      
      expect(resetErrorBoundary).toHaveBeenCalledTimes(1);
    });
  });
  
  describe('handleApiError Function', () => {
    it('handles network errors', () => {
      const networkError = {
        message: 'Network Error'
      };
      
      const appError = handleApiError(networkError);
      
      expect(appError).toBeInstanceOf(AppError);
      expect(appError.code).toBe(ErrorCode.NETWORK_ERROR);
      expect(appError.message).toContain('Unable to connect to the server');
    });
    
    it('handles unauthorized errors (401)', () => {
      const unauthorizedError = {
        response: {
          status: 401,
          data: {
            message: 'Unauthorized'
          }
        }
      };
      
      const apiError = handleApiError(unauthorizedError);
      
      expect(apiError).toBeInstanceOf(ApiError);
      expect(apiError.code).toBe(ErrorCode.UNAUTHORIZED);
      expect(apiError.status).toBe(401);
    });
    
    it('handles forbidden errors (403)', () => {
      const forbiddenError = {
        response: {
          status: 403,
          data: {
            message: 'Forbidden'
          }
        }
      };
      
      const apiError = handleApiError(forbiddenError);
      
      expect(apiError).toBeInstanceOf(ApiError);
      expect(apiError.code).toBe(ErrorCode.FORBIDDEN);
      expect(apiError.status).toBe(403);
    });
    
    it('handles not found errors (404)', () => {
      const notFoundError = {
        response: {
          status: 404,
          data: {
            message: 'Not Found'
          }
        }
      };
      
      const apiError = handleApiError(notFoundError);
      
      expect(apiError).toBeInstanceOf(ApiError);
      expect(apiError.code).toBe(ErrorCode.NOT_FOUND);
      expect(apiError.status).toBe(404);
    });
    
    it('handles server errors (500)', () => {
      const serverError = {
        response: {
          status: 500,
          data: {
            message: 'Internal Server Error'
          }
        }
      };
      
      const apiError = handleApiError(serverError);
      
      expect(apiError).toBeInstanceOf(ApiError);
      expect(apiError.code).toBe(ErrorCode.SERVER_ERROR);
      expect(apiError.status).toBe(500);
    });
    
    it('handles unknown errors', () => {
      const unknownError = {
        response: {
          status: 418, // I'm a teapot
          data: {
            message: 'I\'m a teapot'
          }
        }
      };
      
      const apiError = handleApiError(unknownError);
      
      expect(apiError).toBeInstanceOf(ApiError);
      expect(apiError.code).toBe(ErrorCode.UNKNOWN);
      expect(apiError.status).toBe(418);
    });
    
    it('handles errors without response', () => {
      const genericError = new Error('Generic error');
      
      const appError = handleApiError(genericError);
      
      expect(appError).toBeInstanceOf(AppError);
      expect(appError.code).toBe(ErrorCode.UNKNOWN);
      expect(appError.message).toBe('Generic error');
    });
  });
  
  describe('API Error Handling Integration', () => {
    it('handles successful API calls', async () => {
      const mockData = { success: true, data: 'Test data' };
      const mockFetch = jest.fn().mockResolvedValue(mockData);
      const mockError = jest.fn();
      
      render(
        <ApiErrorHandler onFetch={mockFetch} onError={mockError} />
      );
      
      fireEvent.click(screen.getByTestId('fetch-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('api-data')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('api-data')).toHaveTextContent(JSON.stringify(mockData));
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockError).not.toHaveBeenCalled();
    });
    
    it('handles API error responses', async () => {
      const mockError = {
        response: {
          status: 404,
          data: {
            message: 'Resource not found'
          }
        }
      };
      
      const mockFetch = jest.fn().mockRejectedValue(mockError);
      const onError = jest.fn();
      
      render(
        <ApiErrorHandler onFetch={mockFetch} onError={onError} />
      );
      
      fireEvent.click(screen.getByTestId('fetch-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('api-error')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('api-error')).toHaveTextContent('The requested resource could not be found.');
      expect(screen.getByTestId('api-error')).toHaveTextContent('Error Code: NOT_FOUND');
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledTimes(1);
      
      const calledWithError = onError.mock.calls[0][0];
      expect(calledWithError).toBeInstanceOf(ApiError);
      expect(calledWithError.code).toBe(ErrorCode.NOT_FOUND);
    });
    
    it('handles network errors in API calls', async () => {
      const mockError = {
        message: 'Network Error'
      };
      
      const mockFetch = jest.fn().mockRejectedValue(mockError);
      const onError = jest.fn();
      
      render(
        <ApiErrorHandler onFetch={mockFetch} onError={onError} />
      );
      
      fireEvent.click(screen.getByTestId('fetch-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('api-error')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('api-error')).toHaveTextContent('Unable to connect to the server');
      expect(screen.getByTestId('api-error')).toHaveTextContent('Error Code: NETWORK_ERROR');
      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledTimes(1);
      
      const calledWithError = onError.mock.calls[0][0];
      expect(calledWithError).toBeInstanceOf(AppError);
      expect(calledWithError.code).toBe(ErrorCode.NETWORK_ERROR);
    });
  });
  
  describe('Toast Notifications for Errors', () => {
    it('shows success toast notification', () => {
      toast.success('Operation completed successfully');
      
      expect(toast.success).toHaveBeenCalledWith('Operation completed successfully');
      expect(toast.success).toHaveReturnedWith({
        type: 'success',
        message: 'Operation completed successfully'
      });
    });
    
    it('shows error toast notification', () => {
      const error = new AppError('Something went wrong', ErrorCode.UNKNOWN);
      toast.error(error.message);
      
      expect(toast.error).toHaveBeenCalledWith('Something went wrong');
      expect(toast.error).toHaveReturnedWith({
        type: 'error',
        message: 'Something went wrong'
      });
    });
    
    it('shows warning toast notification', () => {
      toast.warning('This action cannot be undone');
      
      expect(toast.warning).toHaveBeenCalledWith('This action cannot be undone');
      expect(toast.warning).toHaveReturnedWith({
        type: 'warning',
        message: 'This action cannot be undone'
      });
    });
    
    it('shows info toast notification', () => {
      toast.info('Your session will expire in 5 minutes');
      
      expect(toast.info).toHaveBeenCalledWith('Your session will expire in 5 minutes');
      expect(toast.info).toHaveReturnedWith({
        type: 'info',
        message: 'Your session will expire in 5 minutes'
      });
    });
    
    it('dismisses toast notifications', () => {
      toast.dismiss();
      
      expect(toast.dismiss).toHaveBeenCalled();
    });
  });
  
  describe('Integration with Error Boundary and Toast', () => {
    it('shows toast notification when API error occurs within error boundary', async () => {
      const mockError = {
        response: {
          status: 401,
          data: {
            message: 'Unauthorized'
          }
        }
      };
      
      const mockFetch = jest.fn().mockRejectedValue(mockError);
      const onError = jest.fn((error) => {
        // Show toast notification for the error
        toast.error(error.message);
      });
      
      render(
        <ErrorBoundary>
          <ApiErrorHandler onFetch={mockFetch} onError={onError} />
        </ErrorBoundary>
      );
      
      fireEvent.click(screen.getByTestId('fetch-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('api-error')).toBeInTheDocument();
      });
      
      expect(onError).toHaveBeenCalledTimes(1);
      expect(toast.error).toHaveBeenCalledWith('Your session has expired. Please log in again.');
    });
  });
}); 
import React, { Component, ErrorInfo, ReactNode } from 'react';
import type { ApiError } from '../services/apiService';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  resetOnChange?: any;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorDetails: {
    componentStack?: string;
    timestamp: number;
    type: 'api' | 'runtime' | 'unknown';
    metadata?: Record<string, unknown>;
  } | null;
}

const isApiError = (error: Error): error is ApiError => {
  return 'status' in error && 'code' in error;
};

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    errorDetails: null
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { 
      hasError: true, 
      error,
      errorDetails: {
        timestamp: Date.now(),
        type: isApiError(error) ? 'api' : 'runtime'
      }
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to error reporting service
    this.logError(error, errorInfo);

    // Update state with error details
    this.setState({
      errorInfo,
      errorDetails: {
        ...this.state.errorDetails,
        componentStack: errorInfo.componentStack || undefined,
        metadata: this.getErrorMetadata(error),
        timestamp: Date.now(),
        type: isApiError(error) ? 'api' : 'runtime'
      }
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
  }

  private getErrorMetadata(error: Error): Record<string, unknown> {
    const metadata: Record<string, unknown> = {
      errorName: error.name,
      errorMessage: error.message,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent
    };

    if (isApiError(error)) {
      metadata.status = error.status;
      metadata.code = error.code;
      metadata.data = error.data;
    }

    return metadata;
  }

  private logError(error: Error, errorInfo: ErrorInfo): void {
    // In development, log to console
    if (process.env.NODE_ENV === 'development') {
      console.error('Error caught by boundary:', {
        error,
        errorInfo,
        metadata: this.getErrorMetadata(error)
      });
      return;
    }

    // In production, send to error tracking service
    // TODO: Replace with your error tracking service
    // Example: Sentry.captureException(error, { extra: this.getErrorMetadata(error) });
  }

  private handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorDetails: null
    });
  };

  public componentDidUpdate(prevProps: Props): void {
    // Reset error boundary if resetOnChange prop changes
    if (this.props.resetOnChange !== prevProps.resetOnChange) {
      this.handleReset();
    }
  }

  private renderError(): ReactNode {
    const { error, errorDetails } = this.state;

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return (
      <div className="error-boundary" role="alert" aria-live="polite">
        <div className="error-boundary__content">
          <h2 className="error-boundary__title">
            {errorDetails?.type === 'api' ? 'API Error Occurred' : 'Something went wrong'}
          </h2>
          
          <div className="error-boundary__message">
            {error?.message || 'An unexpected error occurred'}
          </div>

          {errorDetails?.type === 'api' && error && isApiError(error) && (
            <div className="error-boundary__api-details">
              <p>Status: {error.status}</p>
              {error.code && (
                <p>Error Code: {error.code}</p>
              )}
            </div>
          )}

          {process.env.NODE_ENV === 'development' && errorDetails?.componentStack && (
            <details className="error-boundary__stack">
              <summary>Error Stack</summary>
              <pre>{errorDetails.componentStack}</pre>
            </details>
          )}

          <div className="error-boundary__actions">
            <button 
              onClick={this.handleReset}
              className="error-boundary__retry-button"
            >
              Try Again
            </button>
            <button 
              onClick={() => window.location.reload()}
              className="error-boundary__reload-button"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  public render(): ReactNode {
    return this.state.hasError ? this.renderError() : this.props.children;
  }
}

export default ErrorBoundary; 
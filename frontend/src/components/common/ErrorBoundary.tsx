import React, { Component, ErrorInfo } from 'react';
import { store } from '../../store';
import { setError } from '../../store/slices/authSlice';
import { errorHandlingService } from '../../services/errorHandlingService';
import { Button } from '../ui/button';
import { Card, CardContent } from '../ui/card';
import { AlertTriangle, RotateCcw, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetOnChange?: number;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Call onError prop if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error to error handling service
    errorHandlingService.handleError(error, {
      severity: 'error',
      source: 'client',
      context: {
        component: 'ErrorBoundary',
        componentStack: errorInfo.componentStack
      }
    });

    // Update global error state
    store.dispatch(setError(error.message));

    // Update state with error info
    this.setState({
      errorInfo
    });
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    // Reset error state when resetOnChange prop changes
    if (this.props.resetOnChange !== prevProps.resetOnChange) {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null
      });
    }
  }

  handleRetry = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  getUserFriendlyMessage(error: Error | null): string {
    if (!error) return 'An unexpected error occurred.';

    // Map technical errors to user-friendly messages
    const errorMessages: Record<string, string> = {
      NetworkError: 'Unable to connect to the server. Please check your internet connection.',
      TypeError: 'Something went wrong while processing your request.',
      AuthenticationError: 'Your session has expired. Please log in again.',
      ValidationError: 'Please check your input and try again.',
      NotFoundError: 'The requested resource could not be found.',
      default: 'An unexpected error occurred. Please try again.'
    };

    // Check for specific error types
    const errorType = error.name || error.constructor.name;
    return errorMessages[errorType] || errorMessages.default;
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <Card className="w-full max-w-md">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center space-y-4">
                <AlertTriangle className="h-12 w-12 text-destructive" />
                <h2 className="text-2xl font-semibold text-destructive">
                  Oops! Something went wrong
                </h2>
                <p className="text-muted-foreground max-w-sm">
                  {this.getUserFriendlyMessage(this.state.error)}
                </p>
                <div className="flex gap-3">
                  <Button
                    onClick={this.handleRetry}
                    className="flex items-center gap-2"
                  >
                    <RotateCcw className="h-4 w-4" />
                    Try Again
                  </Button>
                  <Button
                    variant="outline"
                    onClick={this.handleReload}
                    className="flex items-center gap-2"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reload Page
                  </Button>
                </div>
                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <pre className="mt-4 p-3 bg-muted rounded text-sm text-left w-full overflow-auto">
                    {this.state.error.message}
                  </pre>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary; 
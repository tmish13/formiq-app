import React, { Component, ErrorInfo, ReactNode } from 'react';
import ServerErrorPage from './ServerErrorPage';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to error reporting service
    console.error('Uncaught error:', error, errorInfo);
    
    // If we have Sentry configured, log the error
    if (window.Sentry) {
      window.Sentry.captureException(error);
    }
  }

  public resetError = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }
      
      return (
        <ServerErrorPage
          error={this.state.error || undefined}
          resetError={this.resetError}
        />
      );
    }

    return this.props.children;
  }
}

// Add window.Sentry type definition
declare global {
  interface Window {
    Sentry?: {
      captureException: (error: Error) => void;
    };
  }
}

export default ErrorBoundary; 
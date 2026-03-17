import React, { useEffect, Component, ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Provider, useSelector } from 'react-redux';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { Analytics } from '@vercel/analytics/react';
import { store, RootState } from './store';
import { AppRoutes } from './routes';
import { ModernThemeProvider } from './contexts/ModernThemeContext';
import { NetworkStatusProvider } from './contexts/NetworkStatusProvider';
import { websocketService } from './services/websocketService';
import './styles/globals.css';

// Error Boundary — catches runtime React render errors that would otherwise
// cause a blank white screen with no feedback.
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: '#c00' }}>
          <strong>Something went wrong.</strong>
          <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 12 }}>
            {this.state.error.message}
            {'\n'}
            {this.state.error.stack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// WebSocket provider component that runs inside Redux Provider
const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);
  const token = useSelector((state: RootState) => state.auth.token);

  useEffect(() => {
    // Only connect WebSocket when authenticated AND WebSocket features are enabled
    const shouldConnectWebSocket = isAuthenticated && 
                                   token && 
                                   process.env.REACT_APP_ENABLE_WEBSOCKET === 'true';
    
    if (shouldConnectWebSocket) {
      console.log('Connecting WebSocket...');
      
      // Test connection first to avoid errors
      websocketService.connect(token).catch((error) => {
        console.warn('WebSocket connection failed:', error.message);
        // Continue without WebSocket - app should still work
      });

      // Set up event listeners
      const unsubscribers = [
        websocketService.subscribe('processing_status', (data) => {
          console.log('Form check update:', data);
          store.dispatch({ type: 'formCheck/updateStatus', payload: data });
        }),

        websocketService.subscribe('processing_complete', (data) => {
          console.log('Analysis complete:', data);
          store.dispatch({ 
            type: 'notifications/showNotification', 
            payload: {
              type: 'success',
              message: 'Analysis complete! View your results.',
              data
            }
          });
        }),

        websocketService.subscribe('form_feedback', (data) => {
          console.log('Form feedback received:', data);
          store.dispatch({ 
            type: 'notifications/showNotification', 
            payload: {
              type: 'info',
              message: data.feedback.message,
              data
            }
          });
        })
      ];

      // Cleanup function
      return () => {
        unsubscribers.forEach(unsub => unsub());
        websocketService.disconnect();
      };
    } else {
      console.log('WebSocket disabled or user not authenticated');
    }
  }, [isAuthenticated, token]);

  return <>{children}</>;
};

// TODO(sentry): Wrap AppContent with Sentry.ErrorBoundary once @sentry/react is added.
// Integration steps:
//   1. npm install @sentry/react
//   2. Call Sentry.init({ dsn: process.env.REACT_APP_SENTRY_DSN }) before ReactDOM.render
//   3. Replace this comment with: import * as Sentry from '@sentry/react';
//      and wrap: <Sentry.ErrorBoundary fallback={<p>Something went wrong.</p>}>

// Main App component
const AppContent: React.FC = () => {
  return (
    <NetworkStatusProvider>
      <BrowserRouter>
        <WebSocketProvider>
          <AppRoutes />
        </WebSocketProvider>
      </BrowserRouter>
    </NetworkStatusProvider>
  );
};

// Build-time constant — CRA inlines process.env at bundle time so this never changes at runtime.
const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;

export const App: React.FC = () => {
  useEffect(() => {
    console.log('App mounted');
    if (!googleClientId) {
      console.error(
        'Missing REACT_APP_GOOGLE_CLIENT_ID. Google Sign-In will be disabled.'
      );
    }
  }, []);

  return (
    <ErrorBoundary>
      <Provider store={store}>
        <ModernThemeProvider>
          {googleClientId ? (
            <GoogleOAuthProvider clientId={googleClientId}>
              <AppContent />
            </GoogleOAuthProvider>
          ) : (
            <AppContent />
          )}
          <Analytics />
        </ModernThemeProvider>
      </Provider>
    </ErrorBoundary>
  );
};
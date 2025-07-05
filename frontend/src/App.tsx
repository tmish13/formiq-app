import React, { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { Provider, useSelector } from 'react-redux';
import { store, RootState } from './store';
import { AppRoutes } from './routes';
import { ModernThemeProvider } from './contexts/ModernThemeContext';
import { NetworkStatusProvider } from './contexts/NetworkStatusProvider';
import { websocketService } from './services/websocketService';
import './styles/globals.css';

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

export const App: React.FC = () => {
  useEffect(() => {
    console.log('App mounted');
  }, []);

  return (
    <Provider store={store}>
      <ModernThemeProvider>
        <AppContent />
      </ModernThemeProvider>
    </Provider>
  );
};
import React, { useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { ThemeProvider } from 'styled-components';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { store, persistor } from './store';
import { customTheme } from './styles/theme';
import { GlobalStyles } from './styles/globalStyles';
import { AppLayout } from './components/layout/AppLayout';
import { AppRoutes } from './routes';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSpinner } from './components/common/LoadingSpinner';
// Import Capacitor plugins
import { SplashScreen } from '@capacitor/splash-screen';
import { StatusBar, Style } from '@capacitor/status-bar';
import { Capacitor } from '@capacitor/core';
// Import network status components
import { NetworkStatusProvider } from './contexts/NetworkStatusProvider';
import { OfflineStatusBar } from './components/common/OfflineStatusBar';

export const App: React.FC = () => {
  useEffect(() => {
    // Initialize Capacitor plugins
    const initCapacitor = async () => {
      if (Capacitor.isNativePlatform()) {
        try {
          // Hide splash screen with a fade animation
          await SplashScreen.hide({
            fadeOutDuration: 500
          });
          
          if (Capacitor.getPlatform() === 'android' || Capacitor.getPlatform() === 'ios') {
            // Set status bar style
            await StatusBar.setStyle({ style: Style.Dark });
            
            // Set background color only on Android
            if (Capacitor.getPlatform() === 'android') {
              StatusBar.setBackgroundColor({ color: '#2196f3' });
            }
          }
        } catch (error) {
          console.error('Error initializing Capacitor plugins', error);
        }
      }
    };
    
    initCapacitor();
  }, []);

  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingSpinner />} persistor={persistor}>
        <ThemeProvider theme={customTheme}>
          <GlobalStyles />
          <NetworkStatusProvider>
            <ErrorBoundary>
              <Router>
                <OfflineStatusBar />
                <AppLayout>
                  <AppRoutes />
                </AppLayout>
              </Router>
            </ErrorBoundary>
          </NetworkStatusProvider>
        </ThemeProvider>
      </PersistGate>
    </Provider>
  );
}; 
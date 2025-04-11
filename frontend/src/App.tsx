import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { OnboardingWalkthrough } from './components/onboarding/OnboardingWalkthrough';
import { SplashScreen } from './components/splash/SplashScreen';
import { AuthProvider } from './contexts/AuthContext';
import { AppRoutes } from './routes';
import { GlobalStyle } from './styles/GlobalStyle';
import { Capacitor } from '@capacitor/core';
import { SplashScreen as CapacitorSplashScreen } from '@capacitor/splash-screen';

export const App: React.FC = () => {
  const [showOnboarding, setShowOnboarding] = useState(true);
  const [showSplash, setShowSplash] = useState(true);
  const isNative = Capacitor.isNativePlatform();

  useEffect(() => {
    const hasSeenOnboarding = localStorage.getItem('formiq_onboarding_complete');
    if (hasSeenOnboarding) {
      setShowOnboarding(false);
    }
  }, []);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
  };

  const handleSplashComplete = () => {
    setShowSplash(false);
    
    // Hide the native splash screen if we're on a native platform
    if (isNative) {
      CapacitorSplashScreen.hide();
    }
  };

  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <GlobalStyle />
          {showSplash ? (
            <SplashScreen onComplete={handleSplashComplete} />
          ) : (
            <>
              {showOnboarding && (
                <OnboardingWalkthrough onComplete={handleOnboardingComplete} />
              )}
              <AppRoutes />
            </>
          )}
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}; 
import React from 'react';
import { Box } from '@mui/material';
import styled from 'styled-components';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ROUTES } from '../../routes/constants';
import { Navigation } from './Navigation';
import { MobileNavigation } from './MobileNavigation';
import { ErrorBoundary } from './ErrorBoundary';

const LayoutContainer = styled(Box)`
  display: flex;
  flex-direction: column;
  min-height: 100vh;
`;

const MainContent = styled(Box)`
  flex: 1;
  padding: 24px;
  margin-top: 64px;
  
  @media (max-width: 768px) {
    margin-top: 0;
    padding: 16px;
  }
`;

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  
  const isAuthPage = location.pathname === ROUTES.LOGIN || 
                    location.pathname === ROUTES.REGISTER ||
                    location.pathname === ROUTES.FORGOT_PASSWORD ||
                    location.pathname === ROUTES.RESET_PASSWORD;

  return (
    <ErrorBoundary>
      <LayoutContainer>
        {isAuthenticated && !isAuthPage && <Navigation />}
        <MainContent>
          {children}
        </MainContent>
        {isAuthenticated && !isAuthPage && <MobileNavigation />}
      </LayoutContainer>
    </ErrorBoundary>
  );
}; 
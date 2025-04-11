import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAppSelector } from '../../store/hooks';
import { Button } from '../common/Button';
import styled from 'styled-components';
import { getThemeValue } from '../../utils/themeUtils';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  roles?: string[];
}

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: ${({ theme }) => theme.spacing.md};
`;

const LoadingText = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.large', '1.25rem')};
`;

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  roles = [],
}) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, user } = useAppSelector((state) => state.auth);

  if (isLoading) {
    return (
      <LoadingContainer>
        <LoadingText>Loading...</LoadingText>
        <Button variant="primary" isLoading>
          Please wait
        </Button>
      </LoadingContainer>
    );
  }

  if (requireAuth && !isAuthenticated) {
    // Redirect to login page but save the attempted URL
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!requireAuth && isAuthenticated) {
    // Redirect to dashboard if trying to access login/register while authenticated
    return <Navigate to="/dashboard" replace />;
  }

  if (roles.length > 0 && user && !roles.includes(user.role)) {
    // Redirect to dashboard if user doesn't have required role
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}; 
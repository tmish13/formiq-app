import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import LoadingSpinner from './atoms/LoadingSpinner';
import styled from 'styled-components';

const LoadingContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
`;

type ProtectedRouteProps = {
  children: React.ReactNode;
  requiredRoles?: string[];
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiredRoles = [] 
}) => {
  const { user, isLoading, isAuthenticated } = useAuth();
  const location = useLocation();
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [hasRequiredRole, setHasRequiredRole] = useState<boolean | null>(null);

  useEffect(() => {
    const validateSession = async () => {
      setIsValid(isAuthenticated);
      
      if (isAuthenticated && requiredRoles.length > 0) {
        const userHasRequiredRole = user && requiredRoles.some(role => 
          user.role === role
        );
        setHasRequiredRole(userHasRequiredRole || false);
      } else {
        setHasRequiredRole(true);
      }
    };
    
    validateSession();
  }, [isAuthenticated, requiredRoles, user]);

  if (isLoading || isValid === null) {
    return (
      <LoadingContainer>
        <LoadingSpinner />
      </LoadingContainer>
    );
  }

  if (!isValid) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (hasRequiredRole === false) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute; 
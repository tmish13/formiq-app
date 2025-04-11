import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../services/auth';
import LoadingSpinner from './atoms/LoadingSpinner';
import type { User } from '../types/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  roles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  roles = []
}) => {
  const [isValidating, setIsValidating] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [hasRequiredRole, setHasRequiredRole] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const validateSession = async () => {
      try {
        if (!authService.isAuthenticated()) {
          setIsAuthenticated(false);
          setIsValidating(false);
          return;
        }

        await authService.validateToken();
        const user = authService.getCurrentUser();
        
        setIsAuthenticated(true);
        setHasRequiredRole(
          roles.length === 0 || (user?.roles || []).some((role: string) => roles.includes(role))
        );
      } catch (error) {
        setIsAuthenticated(false);
        setHasRequiredRole(false);
      } finally {
        setIsValidating(false);
      }
    };

    validateSession();
  }, [roles]);

  if (isValidating) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <LoadingSpinner />
      </div>
    );
  }

  if (!requireAuth && isAuthenticated) {
    // Redirect already authenticated users away from auth pages
    return <Navigate to="/dashboard" replace />;
  }

  if (requireAuth && !isAuthenticated) {
    // Redirect unauthenticated users to login
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAuth && isAuthenticated && !hasRequiredRole) {
    // Redirect authenticated users without required role
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
}; 
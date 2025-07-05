import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { LoadingSpinner } from '../atoms/LoadingSpinner';

const AuthenticatedRoot: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [hasTimedOut, setHasTimedOut] = useState(false);

  useEffect(() => {
    // Add a timeout to prevent infinite loading
    const timeout = setTimeout(() => {
      if (isLoading) {
        console.warn('Auth loading timed out, proceeding without auth');
        setHasTimedOut(true);
      }
    }, 2000); // Reduced to 2 seconds for faster redirect to auth

    return () => clearTimeout(timeout);
  }, [isLoading]);

  // If loading has timed out, treat as unauthenticated
  if (hasTimedOut) {
    return <Navigate to="/auth" replace />;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Redirect based on authentication status
  return <Navigate to={isAuthenticated ? "/dashboard" : "/auth"} replace />;
};

export default AuthenticatedRoot;
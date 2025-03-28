import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { Box, Typography } from '@mui/material';
import { SubscriptionTier } from '../types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredSubscription?: SubscriptionTier;
}

const subscriptionLevels: { [key in SubscriptionTier]: number } = {
  free: 0,
  basic: 1,
  pro: 2,
};

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredSubscription,
}) => {
  const { user, loading, error } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <LoadingSpinner size="large" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <Typography color="error" variant="h6">
          {error}
        </Typography>
      </Box>
    );
  }

  if (!user) {
    // Save the attempted URL for redirection after login
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (requiredSubscription) {
    const userLevel = subscriptionLevels[user.subscription_tier];
    const requiredLevel = subscriptionLevels[requiredSubscription];

    if (userLevel < requiredLevel) {
      // Save the attempted URL for redirection after subscription upgrade
      return (
        <Navigate 
          to="/subscription" 
          state={{ 
            from: location.pathname,
            requiredTier: requiredSubscription 
          }} 
          replace 
        />
      );
    }
  }

  // Check if subscription has expired
  if (user.subscription_end_date) {
    const endDate = new Date(user.subscription_end_date);
    if (endDate < new Date()) {
      return (
        <Navigate 
          to="/subscription" 
          state={{ 
            from: location.pathname,
            expired: true 
          }} 
          replace 
        />
      );
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute; 
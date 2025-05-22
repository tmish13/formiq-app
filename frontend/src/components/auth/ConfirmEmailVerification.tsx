import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Typography, Paper, Alert, CircularProgress, Box, Button } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';

export const ConfirmEmailVerification: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [isVerified, setIsVerified] = useState(false);
  const { confirmEmailVerification, error } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const verifyEmail = async () => {
      try {
        // Extract token from URL query parameters
        const searchParams = new URLSearchParams(location.search);
        const token = searchParams.get('token');
        
        if (!token) {
          setIsLoading(false);
          return;
        }
        
        const success = await confirmEmailVerification(token);
        if (success) {
          setIsVerified(true);
        }
      } finally {
        setIsLoading(false);
      }
    };

    verifyEmail();
  }, [location, confirmEmailVerification]);

  const handleNavigateToLogin = () => {
    navigate('/login');
  };

  const handleNavigateToHome = () => {
    navigate('/');
  };

  if (isLoading) {
    return (
      <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4, textAlign: 'center' }}>
        <CircularProgress size={60} sx={{ my: 4 }} />
        <Typography variant="body1">
          Verifying your email address...
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        {isVerified ? 'Email Verified' : 'Email Verification Failed'}
      </Typography>
      
      {isVerified ? (
        <>
          <Alert severity="success" sx={{ mb: 3 }}>
            Your email address has been successfully verified.
          </Alert>
          <Typography variant="body1" sx={{ mb: 3 }}>
            Thank you for verifying your email address. You can now access all features of FormIQ.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
            <Button 
              variant="contained" 
              onClick={handleNavigateToLogin}
            >
              Go to Login
            </Button>
            <Button 
              variant="outlined" 
              onClick={handleNavigateToHome}
            >
              Go to Homepage
            </Button>
          </Box>
        </>
      ) : (
        <>
          <Alert severity="error" sx={{ mb: 3 }}>
            {error || "We couldn't verify your email address."}
          </Alert>
          <Typography variant="body1" sx={{ mb: 3 }}>
            The verification link may have expired or is invalid. Please request a new verification link.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
            <Button 
              variant="contained"
              onClick={() => navigate('/request-verification')}
            >
              Request New Verification
            </Button>
            <Button 
              variant="outlined" 
              onClick={handleNavigateToHome}
            >
              Go to Homepage
            </Button>
          </Box>
        </>
      )}
    </Paper>
  );
}; 
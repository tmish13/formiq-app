import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Alert,
  Paper,
  Container,
  CircularProgress
} from '@mui/material';
import { useAuth } from '../../hooks/useAuth';

const EmailVerification: React.FC = () => {
  const navigate = useNavigate();
  const { token } = useParams<{ token: string }>();
  const { verifyEmail, error } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [verificationStatus, setVerificationStatus] = useState<'pending' | 'success' | 'error'>('pending');

  useEffect(() => {
    const verifyEmailToken = async () => {
      try {
        await verifyEmail(token!);
        setVerificationStatus('success');
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } catch (err) {
        setVerificationStatus('error');
      } finally {
        setIsLoading(false);
      }
    };

    if (token) {
      verifyEmailToken();
    } else {
      setVerificationStatus('error');
      setIsLoading(false);
    }
  }, [token, verifyEmail, navigate]);

  const renderContent = () => {
    if (isLoading) {
      return (
        <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
          <CircularProgress />
          <Typography>Verifying your email...</Typography>
        </Box>
      );
    }

    if (verificationStatus === 'success') {
      return (
        <Alert severity="success">
          <Typography variant="h6">Email Verified Successfully!</Typography>
          <Typography>
            Your email has been verified. You will be redirected to the login page in a few seconds.
          </Typography>
        </Alert>
      );
    }

    return (
      <Alert severity="error">
        <Typography variant="h6">Verification Failed</Typography>
        <Typography>
          {error || 'The verification link is invalid or has expired. Please request a new verification email.'}
        </Typography>
      </Alert>
    );
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Email Verification
          </Typography>
          {renderContent()}
        </Paper>
      </Box>
    </Container>
  );
};

export default EmailVerification; 
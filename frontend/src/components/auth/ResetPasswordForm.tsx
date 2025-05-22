import React, { useState, FormEvent } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button, TextField, Typography, Box, Paper, Alert } from '@mui/material';

export const ResetPasswordForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { requestPasswordReset, error } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    const success = await requestPasswordReset(email);
    setIsLoading(false);
    if (success) {
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Password Reset Requested
        </Typography>
        <Alert severity="success">
          If an account exists with the email {email}, password reset instructions have been sent.
          Please check your inbox and spam folders.
        </Alert>
        <Typography variant="body2" sx={{ mt: 2 }}>
          The email contains a link that will expire in 30 minutes for security reasons.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Reset Your Password
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3 }}>
        Enter your email address and we'll send you instructions to reset your password.
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Box component="form" onSubmit={handleSubmit} noValidate>
        <TextField
          margin="normal"
          required
          fullWidth
          id="email"
          label="Email Address"
          name="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isLoading}
        />
        
        <Button
          type="submit"
          fullWidth
          variant="contained"
          sx={{ mt: 3, mb: 2 }}
          disabled={isLoading || !email}
        >
          {isLoading ? 'Sending...' : 'Reset Password'}
        </Button>
      </Box>
    </Paper>
  );
}; 
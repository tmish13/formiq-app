import React, { useState, FormEvent } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button, TextField, Typography, Box, Paper, Alert } from '@mui/material';

export const RequestEmailVerificationForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { requestEmailVerification, error } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    const success = await requestEmailVerification(email);
    setIsLoading(false);
    if (success) {
      setSubmitted(true);
    }
  };

  if (submitted) {
    return (
      <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Verification Email Sent
        </Typography>
        <Alert severity="success">
          If an account exists with the email {email}, verification instructions have been sent.
          Please check your inbox and spam folders.
        </Alert>
        <Typography variant="body2" sx={{ mt: 2 }}>
          The verification link will expire in 24 hours for security reasons.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Verify Your Email Address
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3 }}>
        Enter your email address and we'll send you a verification link.
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
          {isLoading ? 'Sending...' : 'Send Verification Email'}
        </Button>
      </Box>
    </Paper>
  );
}; 
import React, { useState, FormEvent, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { 
  Button, 
  TextField, 
  Typography, 
  Box, 
  Paper, 
  Alert,
  IconButton,
  InputAdornment
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

export const ConfirmPasswordResetForm: React.FC = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<{[key: string]: string}>({});
  
  const { confirmPasswordReset, error } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Extract token from URL query parameters
    const searchParams = new URLSearchParams(location.search);
    const tokenParam = searchParams.get('token');
    if (tokenParam) {
      setToken(tokenParam);
    }
  }, [location]);

  const validateForm = (): boolean => {
    const newErrors: {[key: string]: string} = {};
    
    if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }
    
    if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    if (!token) {
      newErrors.token = 'Reset token is missing';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsLoading(true);
    const success = await confirmPasswordReset(token, password);
    setIsLoading(false);
    
    if (success) {
      setSubmitted(true);
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    }
  };

  if (submitted) {
    return (
      <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Password Reset Complete
        </Typography>
        <Alert severity="success">
          Your password has been successfully reset. You will be redirected to the login page in a few seconds.
        </Alert>
      </Paper>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 4, maxWidth: 500, mx: 'auto', mt: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Reset Your Password
      </Typography>
      
      <Typography variant="body1" sx={{ mb: 3 }}>
        Enter your new password below.
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {errors.token && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors.token}
        </Alert>
      )}
      
      <Box component="form" onSubmit={handleSubmit} noValidate>
        {!token && (
          <TextField
            margin="normal"
            required
            fullWidth
            id="token"
            label="Reset Token"
            name="token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            error={!!errors.token}
            helperText={errors.token}
            disabled={isLoading}
          />
        )}
        
        <TextField
          margin="normal"
          required
          fullWidth
          name="password"
          label="New Password"
          type={showPassword ? 'text' : 'password'}
          id="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={!!errors.password}
          helperText={errors.password}
          disabled={isLoading}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  edge="end"
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        
        <TextField
          margin="normal"
          required
          fullWidth
          name="confirmPassword"
          label="Confirm New Password"
          type={showPassword ? 'text' : 'password'}
          id="confirmPassword"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          error={!!errors.confirmPassword}
          helperText={errors.confirmPassword}
          disabled={isLoading}
        />
        
        <Button
          type="submit"
          fullWidth
          variant="contained"
          sx={{ mt: 3, mb: 2 }}
          disabled={isLoading || !password || !confirmPassword}
        >
          {isLoading ? 'Resetting...' : 'Reset Password'}
        </Button>
      </Box>
    </Paper>
  );
}; 
import React from 'react';
import { Typography, Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 64px)',
        textAlign: 'center',
        gap: 3,
      }}
    >
      <Typography variant="h2" component="h1" gutterBottom>
        Welcome to FormIQ
      </Typography>
      <Typography variant="h5" color="text.secondary" paragraph>
        AI-powered fitness form analysis
      </Typography>
      {user ? (
        <Button
          variant="contained"
          size="large"
          onClick={() => navigate('/form-check')}
        >
          Start Form Check
        </Button>
      ) : (
        <Button
          variant="contained"
          size="large"
          onClick={() => navigate('/login')}
        >
          Login to Start
        </Button>
      )}
    </Box>
  );
} 
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Grid,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useApi } from '../hooks/useApi';
import { FormCheck } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundaryWrapper from '../components/ErrorBoundary';

const getScoreColor = (score: number) => {
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  return 'error';
};

const ResultsContent = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: result, loading, error, execute: fetchResult } = useApi<FormCheck>(`form-checks/${id}`, 'get');

  useEffect(() => {
    if (id) {
      fetchResult();
    }
  }, [id, fetchResult]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner size="large" />
      </Box>
    );
  }

  if (error || !result) {
    return (
      <Container maxWidth="md">
        <Paper elevation={3} sx={{ p: 4 }}>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error || 'Result not found'}
          </Alert>
          <Button
            variant="contained"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/history')}
          >
            Back to History
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, my: 4 }}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Typography variant="h4" component="h1">
                Form Analysis Results
              </Typography>
              <Chip
                label={`Score: ${result.score}%`}
                color={getScoreColor(result.score)}
                size="medium"
                sx={{ 
                  fontSize: '1.1rem',
                  '& .MuiChip-label': {
                    px: 2,
                  },
                }}
              />
            </Box>
            <Typography variant="subtitle1" color="text.secondary" gutterBottom>
              Exercise: {result.exercise_type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Analyzed on: {new Date(result.created_at).toLocaleString()}
            </Typography>
          </Grid>

          {result.video_url && (
            <Grid item xs={12}>
              <Box
                component="video"
                controls
                width="100%"
                height="auto"
                sx={{
                  borderRadius: 1,
                  backgroundColor: 'black',
                }}
                src={result.video_url}
              />
            </Grid>
          )}

          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              Overall Feedback
            </Typography>
            <Typography variant="body1" paragraph>
              {result.overall_feedback}
            </Typography>
          </Grid>

          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>
              Detailed Analysis
            </Typography>
            <List>
              {result.issues.length > 0 ? (
                result.issues.map((issue, index) => (
                  <ListItem key={index} sx={{ py: 1 }}>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText primary={issue} />
                  </ListItem>
                ))
              ) : (
                <ListItem sx={{ py: 1 }}>
                  <ListItemIcon>
                    <CheckCircleIcon color="success" />
                  </ListItemIcon>
                  <ListItemText primary="No issues found - Great form!" />
                </ListItem>
              )}
            </List>
          </Grid>

          <Grid item xs={12}>
            <Box display="flex" gap={2}>
              <Button
                variant="outlined"
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate('/history')}
              >
                Back to History
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={() => navigate('/')}
              >
                New Analysis
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

const Results = () => {
  const handleError = (error: Error) => {
    console.error('Results Error:', error);
  };

  return (
    <ErrorBoundaryWrapper onError={handleError}>
      <ResultsContent />
    </ErrorBoundaryWrapper>
  );
};

export default Results; 
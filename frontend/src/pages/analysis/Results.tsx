import React from 'react';
import { Box, Typography, Paper, Grid, List, ListItem, ListItemText, Divider } from '@mui/material';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';

const Results: React.FC = () => {
  const { currentFormCheck, isLoading, error } = useFormCheck();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  if (!currentFormCheck) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No form check selected</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Analysis Results
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Overall Score
            </Typography>
            <Typography variant="h3" color="primary">
              {currentFormCheck.score || 'N/A'}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Confidence Score
            </Typography>
            <Typography variant="h3" color="primary">
              {(currentFormCheck.confidence_score || 0) * 100}%
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Overall Feedback
            </Typography>
            <Typography paragraph>
              {currentFormCheck.overall_feedback || 'No feedback available'}
            </Typography>
          </Paper>
        </Grid>
        {currentFormCheck.feedback_items && currentFormCheck.feedback_items.length > 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Detailed Feedback
              </Typography>
              <List>
                {currentFormCheck.feedback_items.map((item, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemText
                        primary={`${item.type.charAt(0).toUpperCase() + item.type.slice(1)} (${item.severity})`}
                        secondary={
                          <>
                            <Typography component="span" variant="body2">
                              {item.description}
                            </Typography>
                            <Typography component="span" variant="body2" color="text.secondary">
                              {' '}Suggestion: {item.suggestions}
                            </Typography>
                          </>
                        }
                      />
                    </ListItem>
                    {index < currentFormCheck.feedback_items!.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default Results; 
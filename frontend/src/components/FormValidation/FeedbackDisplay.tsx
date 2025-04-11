import React from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemIcon, ListItemText, Chip, Divider } from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Warning, Info } from '@mui/icons-material';
import { FormAnalysisResult } from '../../types/formAnalysis';

interface FeedbackDisplayProps {
  result: FormAnalysisResult;
}

export const FeedbackDisplay: React.FC<FeedbackDisplayProps> = ({ result }) => {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getFeedbackIcon = (type: 'success' | 'warning' | 'error') => {
    switch (type) {
      case 'success':
        return <CheckCircle color="success" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <Info color="info" />;
    }
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>
          Form Analysis Results
        </Typography>
        <Chip
          label={`${Math.round(result.confidence * 100)}% Confidence`}
          color={getConfidenceColor(result.confidence)}
          size="small"
        />
      </Box>

      <Divider sx={{ my: 1 }} />

      <List>
        {result.feedback.map((item, index) => (
          <ListItem key={index}>
            <ListItemIcon>
              {getFeedbackIcon(item.type)}
            </ListItemIcon>
            <ListItemText
              primary={item.message}
              secondary={item.suggestion}
            />
          </ListItem>
        ))}
      </List>

      {result.angles && result.angles.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>
            Joint Angles
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {result.angles.map((angle, index) => (
              <Chip
                key={index}
                label={`${angle.joint}: ${Math.round(angle.angle)}°`}
                variant="outlined"
                size="small"
              />
            ))}
          </Box>
        </>
      )}

      {!result.isReliable && (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'warning.light', borderRadius: 1 }}>
          <Typography variant="body2" color="warning.dark">
            Note: The pose detection confidence is low. Please ensure you are fully visible in the frame and well-lit.
          </Typography>
        </Box>
      )}
    </Paper>
  );
}; 
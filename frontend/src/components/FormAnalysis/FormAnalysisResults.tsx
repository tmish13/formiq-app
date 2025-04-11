import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  useTheme
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Speed as SpeedIcon,
  Balance as BalanceIcon,
  Straighten as StraightenIcon,
  CompareArrows as CompareArrowsIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { FormAnalysisResult } from '../../types/formAnalysis';

interface FormAnalysisResultsProps {
  result: FormAnalysisResult;
}

const FormAnalysisResults: React.FC<FormAnalysisResultsProps> = React.memo(({ result }) => {
  const theme = useTheme();

  const getRiskLevelColor = useMemo(() => (level: string) => {
    switch (level.toLowerCase()) {
      case 'low':
        return theme.palette.success.main;
      case 'medium':
        return theme.palette.warning.main;
      case 'high':
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  }, [theme]);

  const getMetricIcon = useMemo(() => (metric: string) => {
    switch (metric) {
      case 'alignment':
        return <StraightenIcon />;
      case 'stability':
        return <BalanceIcon />;
      case 'symmetry':
        return <CompareArrowsIcon />;
      case 'consistency':
        return <TimelineIcon />;
      case 'joint_accuracy':
        return <AssessmentIcon />;
      case 'movement_quality':
        return <SpeedIcon />;
      default:
        return null;
    }
  }, []);

  const getMetricColor = useMemo(() => (value: number) => {
    if (value >= 0.8) return theme.palette.success.main;
    if (value >= 0.6) return theme.palette.warning.main;
    return theme.palette.error.main;
  }, [theme]);

  const metricsGrid = useMemo(() => (
    <Grid container spacing={2}>
      {Object.entries(result.metrics).map(([key, value]) => (
        <Grid item xs={12} sm={6} md={4} key={key}>
          <Box>
            <Box display="flex" alignItems="center" mb={1}>
              {getMetricIcon(key)}
              <Typography variant="body2" sx={{ ml: 1 }}>
                {key.replace('_', ' ').toUpperCase()}
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={value * 100}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: theme.palette.grey[200],
                '& .MuiLinearProgress-bar': {
                  backgroundColor: getMetricColor(value)
                }
              }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {Math.round(value * 100)}%
            </Typography>
          </Box>
        </Grid>
      ))}
    </Grid>
  ), [result.metrics, getMetricIcon, getMetricColor, theme]);

  return (
    <Box sx={{ mt: 3 }}>
      <Grid container spacing={3}>
        {/* Overall Score and Risk Level */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6" gutterBottom>
                  Overall Analysis
                </Typography>
                <Chip
                  label={`Risk Level: ${result.risk_level.toUpperCase()}`}
                  sx={{
                    backgroundColor: getRiskLevelColor(result.risk_level),
                    color: 'white'
                  }}
                />
              </Box>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Confidence Score
                </Typography>
                <Box display="flex" alignItems="center" sx={{ mt: 1 }}>
                  <Box flexGrow={1}>
                    <LinearProgress
                      variant="determinate"
                      value={result.confidence * 100}
                      sx={{
                        height: 10,
                        borderRadius: 5,
                        backgroundColor: theme.palette.grey[200],
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: getMetricColor(result.confidence)
                        }
                      }}
                    />
                  </Box>
                  <Typography variant="body2" sx={{ ml: 2 }}>
                    {Math.round(result.confidence * 100)}%
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Detailed Metrics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Form Metrics
              </Typography>
              {metricsGrid}
            </CardContent>
          </Card>
        </Grid>

        {/* Feedback and Suggestions */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Feedback
              </Typography>
              <List>
                {result.feedback.map((item, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {result.risk_level === 'high' ? (
                        <ErrorIcon color="error" />
                      ) : result.risk_level === 'medium' ? (
                        <WarningIcon color="warning" />
                      ) : (
                        <CheckCircleIcon color="success" />
                      )}
                    </ListItemIcon>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Suggestions
              </Typography>
              <List>
                {result.suggestions.map((item, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      <CheckCircleIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText primary={item} />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Comparison Score */}
        {result.comparison_score !== null && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Form Comparison
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Similarity to Ideal Form
                  </Typography>
                  <Box display="flex" alignItems="center" sx={{ mt: 1 }}>
                    <Box flexGrow={1}>
                      <LinearProgress
                        variant="determinate"
                        value={result.comparison_score * 100}
                        sx={{
                          height: 10,
                          borderRadius: 5,
                          backgroundColor: theme.palette.grey[200],
                          '& .MuiLinearProgress-bar': {
                            backgroundColor: getMetricColor(result.comparison_score)
                          }
                        }}
                      />
                    </Box>
                    <Typography variant="body2" sx={{ ml: 2 }}>
                      {Math.round(result.comparison_score * 100)}%
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
});

export default FormAnalysisResults; 
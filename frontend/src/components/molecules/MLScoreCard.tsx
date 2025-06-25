import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Grid,
  Tooltip,
  IconButton,
  Chip,
  useTheme
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Info,
  Assessment
} from '@mui/icons-material';
import { MLScores, MLScoreCardProps } from '../../types/ml';

/**
 * Component for displaying ML analysis scores with visual indicators
 * Supports detailed, summary, and compact variants
 */
export const MLScoreCard: React.FC<MLScoreCardProps> = ({
  scores,
  previousScores,
  variant = 'detailed',
  showTrend = false,
  showConfidence = true,
  onScoreClick
}) => {
  const theme = useTheme();

  // Helper function to get score color based on value
  const getScoreColor = (score: number): 'success' | 'warning' | 'error' => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  // Helper function to get trend indicator
  const getTrendIndicator = (current: number, previous?: number) => {
    if (!previous || !showTrend) return null;
    
    const diff = current - previous;
    const threshold = 2; // Minimum difference to show trend
    
    if (Math.abs(diff) < threshold) {
      return <TrendingFlat color="action" fontSize="small" />;
    }
    
    return diff > 0 ? (
      <TrendingUp color="success" fontSize="small" />
    ) : (
      <TrendingDown color="error" fontSize="small" />
    );
  };

  // Helper function to get score description
  const getScoreDescription = (scoreType: keyof MLScores, score: number): string => {
    const descriptions = {
      posture_score: {
        high: 'Excellent body alignment and positioning',
        medium: 'Good posture with minor adjustments needed',
        low: 'Significant posture improvements required'
      },
      stability_score: {
        high: 'Great balance and control throughout movement',
        medium: 'Adequate stability with some wobble',
        low: 'Poor balance affecting exercise quality'
      },
      depth_score: {
        high: 'Optimal range of motion achieved',
        medium: 'Good depth with room for improvement',
        low: 'Limited range of motion detected'
      }
    };

    const level = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';
    return descriptions[scoreType]?.[level] || 'Score analysis';
  };

  // Individual score component
  const ScoreItem: React.FC<{
    label: string;
    value: number;
    scoreType: keyof MLScores;
    showDetails?: boolean;
  }> = ({ label, value, scoreType, showDetails = true }) => (
    <Box 
      onClick={() => onScoreClick?.(scoreType)}
      sx={{ 
        cursor: onScoreClick ? 'pointer' : 'default',
        '&:hover': onScoreClick ? { bgcolor: 'action.hover', borderRadius: 1 } : {}
      }}
    >
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="body2" fontWeight={500}>
          {label}
        </Typography>
        <Box display="flex" alignItems="center" gap={0.5}>
          {getTrendIndicator(value, previousScores?.[scoreType])}
          <Typography variant="h6" color={getScoreColor(value) + '.main'} fontWeight="bold">
            {Math.round(value)}
          </Typography>
        </Box>
      </Box>
      
      <Box position="relative" display="inline-flex" width="100%" mb={showDetails ? 1 : 0}>
        <CircularProgress
          variant="determinate"
          value={value}
          size={variant === 'compact' ? 60 : 80}
          thickness={4}
          color={getScoreColor(value)}
          sx={{ 
            opacity: 0.3,
            position: 'absolute'
          }}
        />
        <CircularProgress
          variant="determinate"
          value={value}
          size={variant === 'compact' ? 60 : 80}
          thickness={4}
          color={getScoreColor(value)}
        />
        <Box
          sx={{
            top: 0,
            left: 0,
            bottom: 0,
            right: 0,
            position: 'absolute',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography variant="caption" fontWeight="bold">
            {Math.round(value)}%
          </Typography>
        </Box>
      </Box>

      {showDetails && variant === 'detailed' && (
        <Typography 
          variant="caption" 
          color="text.secondary"
          sx={{ display: 'block', textAlign: 'center' }}
        >
          {getScoreDescription(scoreType, value)}
        </Typography>
      )}
    </Box>
  );

  // Compact variant for dashboard/summary views
  if (variant === 'compact') {
    return (
      <Card sx={{ minWidth: 200 }}>
        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
          <Box display="flex" alignItems="center" gap={1} mb={1}>
            <Assessment color="primary" fontSize="small" />
            <Typography variant="h6" fontWeight="bold">
              ML Analysis
            </Typography>
            {showConfidence && scores.confidence && (
              <Chip 
                label={`${Math.round(scores.confidence * 100)}%`}
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Box>
          
          <Grid container spacing={1}>
            <Grid item xs={4}>
              <ScoreItem 
                label="Posture" 
                value={scores.posture_score} 
                scoreType="posture_score"
                showDetails={false}
              />
            </Grid>
            <Grid item xs={4}>
              <ScoreItem 
                label="Stability" 
                value={scores.stability_score} 
                scoreType="stability_score"
                showDetails={false}
              />
            </Grid>
            <Grid item xs={4}>
              <ScoreItem 
                label="Depth" 
                value={scores.depth_score} 
                scoreType="depth_score"
                showDetails={false}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  }

  // Summary variant for results pages
  if (variant === 'summary') {
    const avgScore = (scores.posture_score + scores.stability_score + scores.depth_score) / 3;
    
    return (
      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="between" mb={2}>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              Form Analysis Scores
            </Typography>
            {showConfidence && scores.confidence && (
              <Tooltip title="Model confidence in analysis accuracy">
                <Chip 
                  label={`Confidence: ${Math.round(scores.confidence * 100)}%`}
                  color="info"
                  variant="outlined"
                  icon={<Info />}
                />
              </Tooltip>
            )}
          </Box>

          {/* Overall Score */}
          <Box textAlign="center" mb={3}>
            <Typography variant="h4" color={getScoreColor(avgScore) + '.main'} fontWeight="bold">
              {Math.round(avgScore)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Overall Form Score
            </Typography>
          </Box>

          <Grid container spacing={3}>
            <Grid item xs={12} sm={4}>
              <ScoreItem 
                label="Posture" 
                value={scores.posture_score} 
                scoreType="posture_score"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <ScoreItem 
                label="Stability" 
                value={scores.stability_score} 
                scoreType="stability_score"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <ScoreItem 
                label="Depth" 
                value={scores.depth_score} 
                scoreType="depth_score"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  }

  // Detailed variant (default)
  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="between" mb={3}>
          <Typography variant="h5" fontWeight="bold">
            ML Form Analysis
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {scores.ml_model_version && (
              <Tooltip title={`Model version: ${scores.ml_model_version}`}>
                <IconButton size="small">
                  <Info fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {showConfidence && scores.confidence && (
              <Chip 
                label={`${Math.round(scores.confidence * 100)}% confidence`}
                color="info"
                variant="outlined"
              />
            )}
          </Box>
        </Box>

        <Grid container spacing={4}>
          <Grid item xs={12} md={4}>
            <ScoreItem 
              label="Posture Alignment" 
              value={scores.posture_score} 
              scoreType="posture_score"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <ScoreItem 
              label="Movement Stability" 
              value={scores.stability_score} 
              scoreType="stability_score"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <ScoreItem 
              label="Range of Motion" 
              value={scores.depth_score} 
              scoreType="depth_score"
            />
          </Grid>
        </Grid>

        {showTrend && previousScores && (
          <Box mt={3} p={2} bgcolor="grey.50" borderRadius={1}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Compared to your previous session:
            </Typography>
            <Box display="flex" gap={2}>
              <Typography variant="caption">
                Posture: {scores.posture_score - previousScores.posture_score > 0 ? '+' : ''}
                {(scores.posture_score - previousScores.posture_score).toFixed(1)} points
              </Typography>
              <Typography variant="caption">
                Stability: {scores.stability_score - previousScores.stability_score > 0 ? '+' : ''}
                {(scores.stability_score - previousScores.stability_score).toFixed(1)} points
              </Typography>
              <Typography variant="caption">
                Depth: {scores.depth_score - previousScores.depth_score > 0 ? '+' : ''}
                {(scores.depth_score - previousScores.depth_score).toFixed(1)} points
              </Typography>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default MLScoreCard;
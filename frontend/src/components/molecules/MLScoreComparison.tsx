import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  LinearProgress,
  Chip,
  Divider,
  useTheme
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Target,
  Timeline,
  Assessment
} from '@mui/icons-material';
import { MLScores, MLScoreComparisonProps } from '../../types/ml';

/**
 * Component for comparing ML scores across different time periods
 * Shows current vs previous scores, progress toward targets, and trends
 */
export const MLScoreComparison: React.FC<MLScoreComparisonProps> = ({
  currentScores,
  previousScores,
  targetScores,
  timeframe = 'session',
  exerciseType
}) => {
  const theme = useTheme();

  // Helper function to get score color
  const getScoreColor = (score: number): string => {
    if (score >= 80) return theme.palette.success.main;
    if (score >= 60) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  // Helper function to calculate percentage change
  const getPercentageChange = (current: number, previous: number): number => {
    return previous === 0 ? 0 : ((current - previous) / previous) * 100;
  };

  // Helper function to get trend icon
  const getTrendIcon = (current: number, previous?: number) => {
    if (!previous) return <TrendingFlat color="action" />;
    
    const diff = current - previous;
    if (Math.abs(diff) < 1) return <TrendingFlat color="action" />;
    
    return diff > 0 ? (
      <TrendingUp color="success" />
    ) : (
      <TrendingDown color="error" />
    );
  };

  // Helper function to get progress toward target
  const getTargetProgress = (current: number, target: number): number => {
    return Math.min((current / target) * 100, 100);
  };

  // Score comparison row component
  const ScoreComparisonRow: React.FC<{
    label: string;
    current: number;
    previous?: number;
    target?: number;
    description: string;
  }> = ({ label, current, previous, target, description }) => {
    const change = previous ? current - previous : 0;
    const percentChange = previous ? getPercentageChange(current, previous) : 0;
    
    return (
      <Box py={2}>
        <Box display="flex" alignItems="center" justifyContent="between" mb={1}>
          <Typography variant="h6" fontWeight={500}>
            {label}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            {getTrendIcon(current, previous)}
            <Typography 
              variant="h6" 
              sx={{ color: getScoreColor(current) }}
              fontWeight="bold"
            >
              {Math.round(current)}%
            </Typography>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" mb={2}>
          {description}
        </Typography>

        {/* Current vs Previous */}
        {previous && (
          <Box mb={2}>
            <Box display="flex" justifyContent="between" alignItems="center" mb={0.5}>
              <Typography variant="caption" color="text.secondary">
                vs {timeframe === 'session' ? 'Previous Session' : `Last ${timeframe}`}
              </Typography>
              <Box display="flex" alignItems="center" gap={0.5}>
                <Typography 
                  variant="caption" 
                  color={change >= 0 ? 'success.main' : 'error.main'}
                  fontWeight="bold"
                >
                  {change >= 0 ? '+' : ''}{change.toFixed(1)} points
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ({percentChange >= 0 ? '+' : ''}{percentChange.toFixed(1)}%)
                </Typography>
              </Box>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={getTargetProgress(current, 100)}
              sx={{ 
                height: 6, 
                borderRadius: 3,
                backgroundColor: 'grey.200',
                '& .MuiLinearProgress-bar': {
                  backgroundColor: getScoreColor(current)
                }
              }}
            />
          </Box>
        )}

        {/* Progress toward target */}
        {target && (
          <Box>
            <Box display="flex" justifyContent="between" alignItems="center" mb={0.5}>
              <Typography variant="caption" color="text.secondary">
                Target: {target}%
              </Typography>
              <Typography 
                variant="caption" 
                color={current >= target ? 'success.main' : 'primary.main'}
                fontWeight="bold"
              >
                {current >= target ? 'Target Achieved!' : `${(target - current).toFixed(1)} points to go`}
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={getTargetProgress(current, target)}
              sx={{ 
                height: 4, 
                borderRadius: 2,
                backgroundColor: 'grey.200'
              }}
              color={current >= target ? 'success' : 'primary'}
            />
          </Box>
        )}
      </Box>
    );
  };

  // Calculate overall improvement
  const calculateOverallImprovement = (): number => {
    if (!previousScores) return 0;
    
    const currentAvg = (currentScores.posture_score + currentScores.stability_score + currentScores.depth_score) / 3;
    const previousAvg = (previousScores.posture_score + previousScores.stability_score + previousScores.depth_score) / 3;
    
    return currentAvg - previousAvg;
  };

  const overallImprovement = calculateOverallImprovement();

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" alignItems="center" gap={2} mb={3}>
          <Assessment color="primary" />
          <Box>
            <Typography variant="h5" fontWeight="bold">
              Score Comparison
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {exerciseType} - {timeframe === 'session' ? 'Session' : timeframe} analysis
            </Typography>
          </Box>
        </Box>

        {/* Overall Summary */}
        {previousScores && (
          <Box mb={3} p={2} bgcolor="grey.50" borderRadius={1}>
            <Box display="flex" alignItems="center" gap={2} mb={1}>
              <Timeline color="primary" />
              <Typography variant="h6" fontWeight={500}>
                Overall Progress
              </Typography>
            </Box>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="body1">
                Your form has 
                <Typography 
                  component="span" 
                  fontWeight="bold"
                  color={overallImprovement >= 0 ? 'success.main' : 'error.main'}
                  sx={{ mx: 0.5 }}
                >
                  {overallImprovement >= 0 ? 'improved' : 'declined'} by {Math.abs(overallImprovement).toFixed(1)} points
                </Typography>
                since your {timeframe === 'session' ? 'last session' : `last ${timeframe}`}.
              </Typography>
              {overallImprovement >= 0 ? (
                <TrendingUp color="success" />
              ) : (
                <TrendingDown color="error" />
              )}
            </Box>
          </Box>
        )}

        {/* Individual Score Comparisons */}
        <Grid container spacing={0}>
          <Grid item xs={12}>
            <ScoreComparisonRow
              label="Posture Alignment"
              current={currentScores.posture_score}
              previous={previousScores?.posture_score}
              target={targetScores?.posture_score}
              description="Body alignment and positioning throughout the exercise"
            />
            <Divider />
          </Grid>
          
          <Grid item xs={12}>
            <ScoreComparisonRow
              label="Movement Stability"
              current={currentScores.stability_score}
              previous={previousScores?.stability_score}
              target={targetScores?.stability_score}
              description="Balance and control during the movement"
            />
            <Divider />
          </Grid>
          
          <Grid item xs={12}>
            <ScoreComparisonRow
              label="Range of Motion"
              current={currentScores.depth_score}
              previous={previousScores?.depth_score}
              target={targetScores?.depth_score}
              description="Depth and full range of motion achieved"
            />
          </Grid>
        </Grid>

        {/* Target Summary */}
        {targetScores && (
          <Box mt={3} p={2} bgcolor="primary.50" borderRadius={1}>
            <Box display="flex" alignItems="center" gap={2} mb={2}>
              <Target color="primary" />
              <Typography variant="h6" fontWeight={500}>
                Target Achievement
              </Typography>
            </Box>
            
            <Grid container spacing={2}>
              {[
                { label: 'Posture', current: currentScores.posture_score, target: targetScores.posture_score },
                { label: 'Stability', current: currentScores.stability_score, target: targetScores.stability_score },
                { label: 'Depth', current: currentScores.depth_score, target: targetScores.depth_score }
              ].map(({ label, current, target }) => (
                <Grid item xs={4} key={label}>
                  <Box textAlign="center">
                    <Chip
                      label={current >= target ? '✓' : `${(target - current).toFixed(0)}`}
                      color={current >= target ? 'success' : 'default'}
                      size="small"
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="caption" display="block">
                      {label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {current.toFixed(0)}/{target.toFixed(0)}
                    </Typography>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* Insights */}
        <Box mt={3} p={2} bgcolor="info.50" borderRadius={1}>
          <Typography variant="body2" fontWeight={500} mb={1}>
            💡 Quick Insights
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {currentScores.posture_score >= 80 && currentScores.stability_score >= 80 && currentScores.depth_score >= 80
              ? "Excellent form across all metrics! Keep up the great work."
              : currentScores.posture_score < 60 || currentScores.stability_score < 60 || currentScores.depth_score < 60
              ? "Focus on the areas marked in red for the biggest improvements."
              : "Good progress! Small adjustments in highlighted areas will boost your scores."
            }
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default MLScoreComparison;
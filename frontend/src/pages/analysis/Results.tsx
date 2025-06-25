import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Container, Grid, Box, Alert, Typography, Tab, Tabs } from '@mui/material';
import FormCheckFeedback from '../../components/FormCheckFeedback';
import VideoPlayer from '../../components/VideoPlayer';
import { LoadingSpinner } from '../../components/atoms/LoadingSpinner';
import MLScoreCard from '../../components/molecules/MLScoreCard';
import MLScoreComparison from '../../components/molecules/MLScoreComparison';
import PoseComparisonView from '../../components/molecules/PoseComparisonView';
import { formCheckService } from '../../services/formCheckService';
import { MLScores, PoseData, PoseIssue } from '../../types/ml';
import { FormCheck } from '../../types/formCheck';


export const Results: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formCheck, setFormCheck] = useState<FormCheck | null>(null);
  const [previousFormCheck, setPreviousFormCheck] = useState<FormCheck | null>(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [poseData, setPoseData] = useState<PoseData[]>([]);
  const [detectedIssues, setDetectedIssues] = useState<PoseIssue[]>([]);

  useEffect(() => {
    const fetchFormCheck = async () => {
      if (!id) {
        setError('No form check ID provided');
        setLoading(false);
        return;
      }

      try {
        // Fetch current form check
        const formCheckData = await formCheckService.getFormCheck(id);
        setFormCheck(formCheckData);

        // Fetch previous form check for comparison (if available)
        try {
          const history = await formCheckService.getHistory();
          const previousCheck = history.find((check, index) => 
            index > 0 && history[index - 1].id === formCheckData.id
          );
          if (previousCheck) {
            setPreviousFormCheck(previousCheck);
          }
        } catch {
          // Previous check fetch failed, continue without comparison
        }

        // Mock pose data and issues for now (will be fetched from API later)
        // This should come from the backend once ML integration is complete
        if (formCheckData.results?.pose_data) {
          setPoseData(formCheckData.results.pose_data);
        }
        if (formCheckData.results?.detected_issues) {
          setDetectedIssues(formCheckData.results.detected_issues);
        }

      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred while fetching the form check');
      } finally {
        setLoading(false);
      }
    };

    fetchFormCheck();
  }, [id]);

  // Helper function to get ML scores from form check
  const getMLScores = (formCheck: FormCheck): MLScores | null => {
    if (!formCheck.posture_score || !formCheck.stability_score || !formCheck.depth_score) {
      return null;
    }
    return {
      posture_score: formCheck.posture_score,
      stability_score: formCheck.stability_score,
      depth_score: formCheck.depth_score,
      confidence: formCheck.classification_confidence,
      ml_model_version: formCheck.ml_model_version
    };
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleExportFrame = (frameIndex: number) => {
    // Implementation for exporting frame
    console.log('Exporting frame:', frameIndex);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <LoadingSpinner data-testid="loading-spinner" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" data-testid="error-message">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!formCheck) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="info" data-testid="error-message">
          Form check not found
        </Alert>
      </Container>
    );
  }

  const currentMLScores = getMLScores(formCheck);
  const previousMLScores = previousFormCheck ? getMLScores(previousFormCheck) : undefined;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }} data-testid="results-container">
      <Typography variant="h3" fontWeight="bold" gutterBottom data-testid="results-title">
        Form Analysis Results
      </Typography>
      
      <Typography variant="h5" color="text.secondary" gutterBottom>
        {formCheck.exercise_type} - {new Date(formCheck.created_at).toLocaleDateString()}
      </Typography>

      {/* Tab Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="ML Analysis" />
          <Tab label="Pose Comparison" />
          <Tab label="Progress" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      {currentTab === 0 && (
        <Grid container spacing={3}>
          {/* Video and Basic Info */}
          <Grid item xs={12} md={8}>
            {formCheck.video_url ? (
              <Box mb={3} data-testid="video-container">
                <VideoPlayer 
                  videoUrl={formCheck.video_url} 
                  data-testid="video-player" 
                />
              </Box>
            ) : (
              <Alert severity="info" data-testid="no-video-message">
                No video available for this form check
              </Alert>
            )}
            
            {/* Traditional Feedback */}
            <FormCheckFeedback
              feedback={formCheck.overall_feedback ?? ''}
              score={formCheck.score ?? 0}
              data-testid="form-check-feedback"
            />
          </Grid>

          {/* ML Scores Summary */}
          <Grid item xs={12} md={4}>
            {currentMLScores ? (
              <MLScoreCard
                scores={currentMLScores}
                previousScores={previousMLScores}
                variant="summary"
                showTrend={!!previousMLScores}
                showConfidence={true}
              />
            ) : (
              <Alert severity="info">
                ML analysis scores not available for this form check
              </Alert>
            )}
          </Grid>
        </Grid>
      )}

      {currentTab === 1 && (
        <Grid container spacing={3}>
          {/* Detailed ML Scores */}
          <Grid item xs={12}>
            {currentMLScores ? (
              <MLScoreCard
                scores={currentMLScores}
                previousScores={previousMLScores}
                variant="detailed"
                showTrend={!!previousMLScores}
                showConfidence={true}
              />
            ) : (
              <Alert severity="warning">
                ML analysis is not available for this form check. This may be because:
                <ul style={{ marginTop: 8, marginBottom: 0 }}>
                  <li>The analysis is still processing</li>
                  <li>The video quality was insufficient for ML analysis</li>
                  <li>This form check was created before ML features were available</li>
                </ul>
              </Alert>
            )}
          </Grid>

          {/* Issues and Recommendations */}
          {detectedIssues.length > 0 && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Detected Issues ({detectedIssues.length})
              </Typography>
              <Grid container spacing={2}>
                {detectedIssues.map((issue, index) => (
                  <Grid item xs={12} md={6} key={index}>
                    <Alert 
                      severity={issue.severity === 'high' ? 'error' : issue.severity === 'medium' ? 'warning' : 'info'}
                      sx={{ mb: 1 }}
                    >
                      <Typography variant="subtitle2" fontWeight="bold">
                        {issue.type} Issue
                      </Typography>
                      <Typography variant="body2">
                        {issue.description}
                      </Typography>
                      {issue.suggestions.length > 0 && (
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          <strong>Suggestion:</strong> {issue.suggestions[0]}
                        </Typography>
                      )}
                    </Alert>
                  </Grid>
                ))}
              </Grid>
            </Grid>
          )}
        </Grid>
      )}

      {currentTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <PoseComparisonView
              formCheckId={formCheck.id.toString()}
              exerciseType={formCheck.exercise_type}
              userPoseData={poseData}
              detectedIssues={detectedIssues}
              showTimeline={true}
              allowScrubbing={true}
              onExportFrame={handleExportFrame}
            />
          </Grid>
        </Grid>
      )}

      {currentTab === 3 && (
        <Grid container spacing={3}>
          <Grid item xs={12}>
            {currentMLScores && previousMLScores ? (
              <MLScoreComparison
                currentScores={currentMLScores}
                previousScores={previousMLScores}
                timeframe="session"
                exerciseType={formCheck.exercise_type}
              />
            ) : (
              <Alert severity="info">
                Progress comparison requires at least two form check sessions.
                Complete more analyses to see your improvement over time.
              </Alert>
            )}
          </Grid>
        </Grid>
      )}
    </Container>
  );
};
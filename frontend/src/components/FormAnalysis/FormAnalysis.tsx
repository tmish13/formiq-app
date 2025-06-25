import React, { useState, useRef, useCallback } from 'react';
import { formAnalysisService } from '../../services/formAnalysisService';
import { FormAnalysisResult, FormAnalysisRequest } from '../../types/formAnalysis';
import { Button, Card, Alert, Stack, Typography, Box, CircularProgress, CardContent } from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';
import styles from './FormAnalysis.module.css';

export const FormAnalysis: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<FormAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const handleVideoUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setAnalyzing(true);
      setError(null);
      setResult(null);

      // Create video URL
      const videoUrl = URL.createObjectURL(file);

      // Wait for video metadata to load
      await new Promise<void>((resolve) => {
        if (videoRef.current) {
          videoRef.current.src = videoUrl;
          videoRef.current.onloadedmetadata = () => resolve();
        }
      });

      const request: FormAnalysisRequest = {
        videoUrl,
        keypoints: [], // Will be populated by pose analysis
        duration: videoRef.current?.duration || 0
      };

      const analysisResult = await formAnalysisService.analyzeForm(request);
      setResult(analysisResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to analyze form';
      setError(errorMessage);
    } finally {
      setAnalyzing(false);
    }
  }, []);

  const renderResult = () => {
    if (!result) return null;

    const getProgressColor = (value: number) => {
      return value >= 0.7 ? 'success' : 'error';
    };

    return (
      <Card className={styles.resultCard}>
        <CardContent>
          <Typography variant="h5" gutterBottom>Analysis Results</Typography>
          
          <div className={styles.metricsGrid}>
            <div className={styles.metric}>
              <Typography variant="body2" gutterBottom>Alignment</Typography>
              <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                <CircularProgress
                  variant="determinate"
                  value={Math.round(result.metrics.alignment * 100)}
                  size={80}
                  color={getProgressColor(result.metrics.alignment)}
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
                  <Typography variant="caption">
                    {Math.round(result.metrics.alignment * 100)}%
                  </Typography>
                </Box>
              </Box>
            </div>
            <div className={styles.metric}>
              <Typography variant="body2" gutterBottom>Stability</Typography>
              <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                <CircularProgress
                  variant="determinate"
                  value={Math.round(result.metrics.stability * 100)}
                  size={80}
                  color={getProgressColor(result.metrics.stability)}
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
                  <Typography variant="caption">
                    {Math.round(result.metrics.stability * 100)}%
                  </Typography>
                </Box>
              </Box>
            </div>
            <div className={styles.metric}>
              <Typography variant="body2" gutterBottom>Symmetry</Typography>
              <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                <CircularProgress
                  variant="determinate"
                  value={Math.round(result.metrics.symmetry * 100)}
                  size={80}
                  color={getProgressColor(result.metrics.symmetry)}
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
                  <Typography variant="caption">
                    {Math.round(result.metrics.symmetry * 100)}%
                  </Typography>
                </Box>
              </Box>
            </div>
            <div className={styles.metric}>
              <Typography variant="body2" gutterBottom>Consistency</Typography>
              <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                <CircularProgress
                  variant="determinate"
                  value={Math.round(result.metrics.consistency * 100)}
                  size={80}
                  color={getProgressColor(result.metrics.consistency)}
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
                  <Typography variant="caption">
                    {Math.round(result.metrics.consistency * 100)}%
                  </Typography>
                </Box>
              </Box>
            </div>
          </div>

          <div className={styles.feedback}>
            <Typography variant="h6" gutterBottom>Feedback</Typography>
            <ul>
              {result.feedback.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>

          <div className={styles.suggestions}>
            <Typography variant="h6" gutterBottom>Suggestions</Typography>
            <ul>
              {result.suggestions.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className={styles.container}>
      <Card className={styles.uploadCard}>
        <CardContent>
          <Typography variant="h4" gutterBottom>Form Analysis</Typography>
          <Stack spacing={3} sx={{ width: '100%' }}>
            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}

            <Box>
              <input
                accept="video/*"
                style={{ display: 'none' }}
                id="video-upload-button"
                type="file"
                onChange={handleVideoUpload}
                disabled={analyzing}
              />
              <label htmlFor="video-upload-button">
                <Button
                  variant="contained"
                  component="span"
                  startIcon={<UploadIcon />}
                  disabled={analyzing}
                  size="large"
                  fullWidth
                >
                  {analyzing ? 'Analyzing...' : 'Upload Video'}
                </Button>
              </label>
            </Box>

            <div className={styles.preview}>
              <video
                ref={videoRef}
                className={styles.video}
                controls
                playsInline
                style={{ display: videoRef.current?.src ? 'block' : 'none' }}
              />
            </div>
          </Stack>
        </CardContent>
      </Card>

      {result && renderResult()}
    </div>
  );
}; 
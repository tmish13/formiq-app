import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  Snackbar,
  Alert,
  LinearProgress,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import { useApi } from '../hooks/useApi';
import { FormCheck } from '../types';
import ErrorBoundaryWrapper from '../components/ErrorBoundary';
import LoadingSpinner from '../components/LoadingSpinner';
import { AxiosProgressEvent, AxiosError } from 'axios';

interface ApiErrorResponse {
  detail: string;
}

const MAX_FILE_SIZE = parseInt(process.env.REACT_APP_MAX_FILE_SIZE || '10000000', 10);
const ALLOWED_VIDEO_TYPES = (process.env.REACT_APP_ALLOWED_VIDEO_TYPES || 'video/mp4,video/quicktime').split(',');

const UploadContent = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const { loading, execute: uploadFile } = useApi<FormCheck>('form-checks', 'post');

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setError('Please select a file');
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(`File size must be less than ${MAX_FILE_SIZE / 1000000}MB`);
      return;
    }

    if (!ALLOWED_VIDEO_TYPES.includes(file.type)) {
      setError(`File type must be one of: ${ALLOWED_VIDEO_TYPES.join(', ')}`);
      return;
    }

    setSelectedFile(file);
    setError(null);
    setUploadProgress(0);
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('exercise_type', 'squat'); // Default to squat, you might want to make this selectable

    try {
      const result = await uploadFile({
        data: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(progress);
          }
        },
      });
      
      if (result && result.id) {
        navigate(`/results/${result.id}`);
      } else {
        setError('Failed to process video. Please try again.');
      }
    } catch (err) {
      const axiosError = err as AxiosError<ApiErrorResponse>;
      const errorMessage = axiosError.response?.data?.detail || 
                         axiosError.message || 
                         'Failed to upload file. Please try again.';
      setError(errorMessage);
      setUploadProgress(0);
    }
  }, [selectedFile, uploadFile, navigate]);

  const handleCloseError = useCallback(() => {
    setError(null);
  }, []);

  if (loading && uploadProgress === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner size="large" />
      </Box>
    );
  }

  return (
    <Container maxWidth="md">
      <Paper elevation={3} sx={{ p: 4, my: 4 }}>
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          minHeight="400px"
        >
          <Typography variant="h4" component="h1" gutterBottom>
            Upload Your Exercise Video
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Select a video file to analyze your exercise form
          </Typography>

          <input
            accept={ALLOWED_VIDEO_TYPES.join(',')}
            style={{ display: 'none' }}
            id="video-upload"
            type="file"
            onChange={handleFileSelect}
          />
          <label htmlFor="video-upload">
            <Button
              variant="contained"
              component="span"
              startIcon={<CloudUploadIcon />}
              disabled={loading}
            >
              Select Video
            </Button>
          </label>

          {selectedFile && (
            <Typography variant="body2" sx={{ mt: 2 }}>
              Selected file: {selectedFile.name}
            </Typography>
          )}

          {loading && uploadProgress > 0 && (
            <Box sx={{ width: '100%', mt: 2 }}>
              <LinearProgress 
                variant="determinate" 
                value={uploadProgress} 
                sx={{
                  height: 8,
                  borderRadius: 4,
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 4,
                  },
                }}
              />
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
                Uploading: {uploadProgress}%
              </Typography>
            </Box>
          )}

          <Button
            variant="contained"
            color="primary"
            onClick={handleUpload}
            disabled={!selectedFile || loading}
            sx={{ mt: 4 }}
          >
            {loading ? 'Uploading...' : 'Upload and Analyze'}
          </Button>
        </Box>
      </Paper>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={handleCloseError}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseError} severity="error" variant="filled">
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
};

const Upload = () => {
  const handleError = (error: Error) => {
    console.error('Upload Error:', error);
  };

  return (
    <ErrorBoundaryWrapper onError={handleError}>
      <UploadContent />
    </ErrorBoundaryWrapper>
  );
};

export default Upload; 
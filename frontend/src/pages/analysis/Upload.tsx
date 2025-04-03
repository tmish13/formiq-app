import React, { useState, useRef, useEffect } from 'react';
import { Box, Typography, Button, TextField, FormControl, InputLabel, Select, MenuItem, Paper, LinearProgress, Alert, Snackbar, CircularProgress, Grid } from '@mui/material';
import { styled } from '@mui/system';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';
import { ExerciseType } from '../../types';
import { apiService } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

// Target video settings
const MAX_VIDEO_SIZE_MB = 50; // 50 MB
const MAX_VIDEO_DURATION = 180; // 3 minutes

// Styled components
const UploadBox = styled(Box)(({ theme }) => ({
  border: `2px dashed ${theme.palette.primary.main}`,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(3),
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  '&:hover': {
    backgroundColor: theme.palette.action.hover,
  },
}));

const VideoPreview = styled('video')({
  width: '100%',
  maxHeight: '300px',
  objectFit: 'contain',
  marginTop: '16px',
  borderRadius: '4px',
});

const Upload: React.FC = () => {
  const { submitFormCheck, isLoading, error } = useFormCheck();
  const [video, setVideo] = useState<File | null>(null);
  const [exerciseType, setExerciseType] = useState<ExerciseType>('squat');
  const [notes, setNotes] = useState('');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isCompressing, setIsCompressing] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [videoAnalysis, setVideoAnalysis] = useState<{ duration: number, size: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  // Reset upload progress when video changes
  useEffect(() => {
    if (video) {
      analyzeVideo(video);
    } else {
      setVideoAnalysis(null);
      setVideoUrl(null);
      setUploadProgress(0);
    }
  }, [video]);

  // Cleanup objectURL on unmount
  useEffect(() => {
    return () => {
      if (videoUrl && videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  const analyzeVideo = async (file: File) => {
    // Create preview URL
    const url = URL.createObjectURL(file);
    setVideoUrl(url);

    // Create video element to analyze
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    // Listen for metadata loaded event
    video.onloadedmetadata = () => {
      setVideoAnalysis({
        duration: video.duration,
        size: file.size / (1024 * 1024) // Size in MB
      });
    };
    
    // Set source and load
    video.src = url;
  };

  const validateVideo = (): boolean => {
    setUploadError(null);
    
    if (!video) {
      setUploadError('Please select a video file');
      return false;
    }

    // Validate file type
    const fileType = video.type;
    if (!fileType.startsWith('video/')) {
      setUploadError('Invalid file type. Please upload a video file.');
      return false;
    }

    // Validate file size
    if (videoAnalysis && videoAnalysis.size > MAX_VIDEO_SIZE_MB) {
      setUploadError(`Video size exceeds maximum limit of ${MAX_VIDEO_SIZE_MB}MB`);
      return false;
    }

    // Validate duration
    if (videoAnalysis && videoAnalysis.duration > MAX_VIDEO_DURATION) {
      setUploadError(`Video duration exceeds maximum limit of ${MAX_VIDEO_DURATION} seconds`);
      return false;
    }

    return true;
  };

  const handleVideoChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setVideo(event.target.files[0]);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
    
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setVideo(event.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!validateVideo()) {
      return;
    }
    
    try {
      // Get presigned upload URL
      const presignedData = await apiService.post('/form-checks/presigned-upload', {
        filename: video!.name,
        contentType: video!.type,
        exerciseType
      });
      
      // Prepare form data for direct S3 upload
      const formData = new FormData();
      Object.entries(presignedData.post_data.fields).forEach(([key, value]) => {
        formData.append(key, value as string);
      });
      formData.append('file', video!);
      
      // Upload directly to S3 with progress tracking
      const xhr = new XMLHttpRequest();
      xhr.open('POST', presignedData.post_data.url);
      
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      };
      
      xhr.onload = async () => {
        if (xhr.status === 204 || xhr.status === 200) {
          try {
            // Complete form check submission with already uploaded video
            await submitFormCheck(
              null, // No need to upload the video again
              exerciseType,
              notes,
              presignedData.file_url // Pass the S3 URL
            );
            
            // Redirect to form check results page
            navigate('/analysis/history');
            
            // Reset form
            setVideo(null);
            setNotes('');
            setUploadProgress(0);
          } catch (err) {
            console.error('Failed to complete form check submission:', err);
            setUploadError('Failed to complete submission after upload');
          }
        } else {
          setUploadError(`Upload failed with status: ${xhr.status}`);
        }
      };
      
      xhr.onerror = () => {
        setUploadError('Network error occurred during upload');
      };
      
      xhr.send(formData);
    } catch (err) {
      console.error('Failed to get presigned URL:', err);
      setUploadError('Failed to prepare upload');
    }
  };

  const resetForm = () => {
    setVideo(null);
    setVideoUrl(null);
    setUploadProgress(0);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (isLoading && uploadProgress === 0) {
    return <LoadingSpinner />;
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Upload Form Check
      </Typography>
      <Paper sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
        <form onSubmit={handleSubmit}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}
          
          {uploadError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {uploadError}
            </Alert>
          )}
          
          <Box sx={{ mb: 3 }}>
            <input
              accept="video/*"
              style={{ display: 'none' }}
              id="video-upload"
              ref={fileInputRef}
              type="file"
              onChange={handleVideoChange}
            />
            
            <UploadBox 
              sx={{ 
                mb: 2,
                border: isDragging ? '2px solid' : '2px dashed',
                borderColor: isDragging ? 'primary.main' : 'grey.400',
                bgcolor: isDragging ? 'action.hover' : 'background.paper',
              }}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {!video ? (
                <>
                  <Typography variant="h6" gutterBottom>
                    Drag and drop your video here
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    or click to browse files
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                    Maximum size: {MAX_VIDEO_SIZE_MB}MB | Maximum duration: {MAX_VIDEO_DURATION} seconds
                  </Typography>
                </>
              ) : (
                <>
                  <Typography variant="body1" gutterBottom>
                    {video.name}
                  </Typography>
                  {videoAnalysis && (
                    <Typography variant="body2" color="text.secondary">
                      Size: {videoAnalysis.size.toFixed(2)}MB | Duration: {videoAnalysis.duration.toFixed(1)} seconds
                    </Typography>
                  )}
                  <Button 
                    variant="outlined" 
                    size="small" 
                    sx={{ mt: 1 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      resetForm();
                    }}
                  >
                    Change Video
                  </Button>
                </>
              )}
            </UploadBox>
            
            {videoUrl && (
              <VideoPreview
                controls
                src={videoUrl}
                preload="metadata"
              />
            )}
          </Box>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Exercise Type</InputLabel>
                <Select
                  value={exerciseType}
                  label="Exercise Type"
                  onChange={(e) => setExerciseType(e.target.value as ExerciseType)}
                >
                  <MenuItem value="squat">Squat</MenuItem>
                  <MenuItem value="deadlift">Deadlift</MenuItem>
                  <MenuItem value="bench_press">Bench Press</MenuItem>
                  <MenuItem value="overhead_press">Overhead Press</MenuItem>
                  <MenuItem value="barbell_row">Barbell Row</MenuItem>
                  <MenuItem value="pullup">Pull-up</MenuItem>
                  <MenuItem value="pushup">Push-up</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                multiline
                rows={2}
                label="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any specific form concerns or questions here..."
              />
            </Grid>
          </Grid>
          
          {uploadProgress > 0 && uploadProgress < 100 && (
            <Box sx={{ my: 3 }}>
              <Typography variant="body2" gutterBottom>
                Uploading: {uploadProgress}%
              </Typography>
              <LinearProgress variant="determinate" value={uploadProgress} />
            </Box>
          )}
          
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between' }}>
            <Button
              variant="outlined"
              onClick={resetForm}
              disabled={!video || uploadProgress > 0 && uploadProgress < 100}
            >
              Cancel
            </Button>
            
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={!video || isLoading || uploadProgress > 0 && uploadProgress < 100}
              startIcon={isLoading && uploadProgress === 0 ? <CircularProgress size={20} color="inherit" /> : null}
            >
              {uploadProgress > 0 && uploadProgress < 100 ? 'Uploading...' : 'Submit for Analysis'}
            </Button>
          </Box>
        </form>
      </Paper>
    </Box>
  );
};

export default Upload; 
import React, { useState, useRef, ChangeEvent, DragEvent } from 'react';
import { Box, Button, CircularProgress, Typography, Alert, Paper, LinearProgress, IconButton } from '@mui/material';
import { styled } from '@mui/material/styles';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { videoService, Video } from '../services/videos';

// Maximum file size in bytes (100MB)
const MAX_FILE_SIZE = 100 * 1024 * 1024;
// Maximum video duration in seconds (5 minutes)
const MAX_DURATION = 5 * 60;
// Allowed video types
const ALLOWED_TYPES = ['video/mp4', 'video/webm', 'video/quicktime'];

const UploadContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  textAlign: 'center',
  border: `2px dashed ${theme.palette.primary.main}`,
  background: theme.palette.background.default,
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  '&:hover': {
    borderColor: theme.palette.primary.dark,
    background: theme.palette.action.hover,
  },
}));

const VideoPreview = styled('video')({
  width: '100%',
  maxHeight: '300px',
  borderRadius: '4px',
  marginTop: '16px',
});

export interface VideoUploadProps {
  onUploadComplete?: (video: Video) => void;
  onUploadError?: (error: Error) => void;
}

interface UploadStatus {
  uploading: boolean;
  progress: number;
  error: string | null;
  success: boolean;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ 
  onUploadComplete = () => {}, 
  onUploadError = () => {} 
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>({
    uploading: false,
    progress: 0,
    error: null,
    success: false,
  });
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [uploadedVideo, setUploadedVideo] = useState<Video | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadAbortController = useRef<AbortController | null>(null);

  // Handle file selection
  const handleFileSelect = (selectedFile: File) => {
    // Reset state
    setStatus({
      uploading: false,
      progress: 0,
      error: null,
      success: false,
    });
    setVideoUrl(null);
    setUploadedVideo(null);

    // Validate file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setStatus(prev => ({
        ...prev,
        error: `File size exceeds the maximum limit of ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
      }));
      return;
    }

    // Validate file type
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      setStatus(prev => ({
        ...prev,
        error: `File type not supported. Allowed types: ${ALLOWED_TYPES.join(', ')}`,
      }));
      return;
    }

    // Create a video element to check duration
    const videoElement = document.createElement('video');
    videoElement.preload = 'metadata';

    // Create an object URL for the file
    const objectUrl = URL.createObjectURL(selectedFile);
    videoElement.src = objectUrl;

    // Set up event listener for metadata loaded
    videoElement.onloadedmetadata = () => {
      URL.revokeObjectURL(objectUrl);
      
      // Validate duration
      if (videoElement.duration > MAX_DURATION) {
        setStatus(prev => ({
          ...prev,
          error: `Video duration exceeds the maximum limit of ${MAX_DURATION / 60} minutes`,
        }));
        return;
      }

      // All validations passed, set the file
      setFile(selectedFile);
      setVideoUrl(objectUrl);
    };

    // Handle error loading video
    videoElement.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      setStatus(prev => ({
        ...prev,
        error: 'Error loading video file. Please try another file.',
      }));
    };
  };

  // Handle file input change
  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  // Handle drag and drop
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  // Trigger file input click
  const handleContainerClick = () => {
    if (!file && !status.uploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // Clear selected file
  const handleClearFile = () => {
    if (videoUrl) {
      URL.revokeObjectURL(videoUrl);
    }
    setFile(null);
    setVideoUrl(null);
    setUploadedVideo(null);
    setStatus({
      uploading: false,
      progress: 0,
      error: null,
      success: false,
    });
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Cancel upload
  const handleCancelUpload = () => {
    if (uploadAbortController.current) {
      uploadAbortController.current.abort();
      uploadAbortController.current = null;
    }
    
    setStatus({
      uploading: false,
      progress: 0,
      error: 'Upload cancelled by user',
      success: false,
    });
  };

  // Upload file to S3
  const handleUpload = async () => {
    if (!file) return;

    try {
      // Reset status
      setStatus({
        uploading: true,
        progress: 0,
        error: null,
        success: false,
      });
      
      // Create abort controller
      uploadAbortController.current = new AbortController();
      
      // Upload the video with progress tracking
      const video = await videoService.uploadVideo(file, (progress) => {
        setStatus(prev => ({
          ...prev,
          progress,
        }));
      });
      
      // Update state with the uploaded video
      setUploadedVideo(video);
      
      // Set success state
      setStatus({
        uploading: false,
        progress: 100,
        error: null,
        success: true,
      });
      
      // Call onUploadComplete callback
      onUploadComplete(video);
      
    } catch (error) {
      console.error('Upload error:', error);
      setStatus({
        uploading: false,
        progress: 0,
        error: error instanceof Error ? error.message : 'An unknown error occurred',
        success: false,
      });
      onUploadError(error instanceof Error ? error : new Error('Upload failed'));
    } finally {
      // Clean up
      if (uploadAbortController.current) {
        uploadAbortController.current = null;
      }
    }
  };

  return (
    <Box>
      <input
        accept="video/*"
        type="file"
        hidden
        ref={fileInputRef}
        onChange={handleFileInputChange}
        disabled={status.uploading}
      />
      
      <UploadContainer
        onClick={handleContainerClick}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        elevation={2}
        sx={{
          opacity: status.uploading || status.success ? 0.7 : 1,
          pointerEvents: status.uploading || status.success ? 'none' : 'auto',
        }}
      >
        <CloudUploadIcon fontSize="large" color="primary" />
        <Typography variant="h6" component="div" gutterBottom>
          {file ? file.name : 'Drag and drop a video file here, or click to select'}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Maximum file size: {MAX_FILE_SIZE / (1024 * 1024)}MB, Max duration: {MAX_DURATION / 60} minutes
          <br />
          Supported formats: MP4, WebM, QuickTime
        </Typography>
      </UploadContainer>
      
      {status.error && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => setStatus(prev => ({ ...prev, error: null }))}>
              Dismiss
            </Button>
          }
        >
          {status.error}
        </Alert>
      )}
      
      {status.success && (
        <Alert 
          severity="success" 
          sx={{ mb: 2 }}
          icon={<CheckCircleIcon fontSize="inherit" />}
        >
          Video uploaded successfully!
        </Alert>
      )}
      
      {file && videoUrl && (
        <Box mt={2}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle1">
              {file.name} ({(file.size / (1024 * 1024)).toFixed(2)}MB)
            </Typography>
            <Box>
              {!status.uploading && !status.success && (
                <IconButton onClick={handleClearFile} color="error" size="small">
                  <DeleteIcon />
                </IconButton>
              )}
            </Box>
          </Box>
          
          <VideoPreview controls src={videoUrl} />
          
          {status.uploading && (
            <Box mt={2}>
              <Box display="flex" alignItems="center" mb={1}>
                <Box width="100%" mr={1}>
                  <LinearProgress variant="determinate" value={status.progress} />
                </Box>
                <Box minWidth={35}>
                  <Typography variant="body2" color="textSecondary">{`${Math.round(status.progress)}%`}</Typography>
                </Box>
              </Box>
              <Button 
                variant="outlined" 
                color="error" 
                onClick={handleCancelUpload}
                startIcon={<DeleteIcon />}
              >
                Cancel
              </Button>
            </Box>
          )}
          
          {!status.uploading && !status.success && (
            <Button
              variant="contained"
              color="primary"
              fullWidth
              onClick={handleUpload}
              sx={{ mt: 2 }}
              startIcon={<CloudUploadIcon />}
            >
              Upload Video
            </Button>
          )}
        </Box>
      )}
    </Box>
  );
};

export default VideoUpload; 
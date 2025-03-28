import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  CircularProgress,
} from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export function FormCheck() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('video', selectedFile);
      
      // TODO: Implement video upload and analysis
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulated upload
      
      // Navigate to results page
      navigate('/results');
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  if (!user) {
    navigate('/login');
    return null;
  }

  return (
    <Box sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Form Check Analysis
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper
            sx={{
              p: 3,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Typography variant="h6" gutterBottom>
              Upload Your Video
            </Typography>
            <input
              accept="video/*"
              style={{ display: 'none' }}
              id="video-upload"
              type="file"
              onChange={handleFileSelect}
            />
            <label htmlFor="video-upload">
              <Button
                variant="contained"
                component="span"
                disabled={isUploading}
              >
                Select Video
              </Button>
            </label>
            {selectedFile && (
              <Typography variant="body2" color="text.secondary">
                Selected: {selectedFile.name}
              </Typography>
            )}
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              sx={{ mt: 2 }}
            >
              {isUploading ? (
                <>
                  <CircularProgress size={24} sx={{ mr: 1 }} />
                  Uploading...
                </>
              ) : (
                'Analyze Form'
              )}
            </Button>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Instructions
            </Typography>
            <Typography variant="body1" paragraph>
              1. Record your exercise from a side view
            </Typography>
            <Typography variant="body1" paragraph>
              2. Ensure good lighting and clear visibility
            </Typography>
            <Typography variant="body1" paragraph>
              3. Include the full range of motion
            </Typography>
            <Typography variant="body1" paragraph>
              4. Upload the video and wait for analysis
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
} 
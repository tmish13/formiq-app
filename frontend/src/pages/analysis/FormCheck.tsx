import React, { useState } from 'react';
import { Box, Typography, Button, TextField } from '@mui/material';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';

const FormCheck: React.FC = () => {
  const { submitFormCheck, isLoading, error } = useFormCheck();
  const [video, setVideo] = useState<File | null>(null);
  const [notes, setNotes] = useState('');

  const handleVideoChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setVideo(event.target.files[0]);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (video) {
      try {
        await submitFormCheck(video, 'squat', undefined);
        setVideo(null);
        setNotes('');
      } catch (err) {
        console.error('Failed to submit form check:', err);
      }
    }
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 600, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Submit Form Check
      </Typography>
      {error && (
        <Typography color="error" gutterBottom>
          {error}
        </Typography>
      )}
      <Box sx={{ mb: 3 }}>
        <input
          accept="video/*"
          style={{ display: 'none' }}
          id="video-upload"
          type="file"
          onChange={handleVideoChange}
        />
        <label htmlFor="video-upload">
          <Button variant="contained" component="span">
            Upload Video
          </Button>
          {video && (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Selected: {video.name}
            </Typography>
          )}
        </label>
      </Box>
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        sx={{ mb: 3 }}
      />
      <Button
        type="submit"
        variant="contained"
        color="primary"
        disabled={!video || isLoading}
      >
        Submit
      </Button>
    </Box>
  );
};

export default FormCheck; 
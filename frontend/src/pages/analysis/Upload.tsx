import React, { useState } from 'react';
import { Box, Typography, Button, TextField, FormControl, InputLabel, Select, MenuItem, Paper } from '@mui/material';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';
import { ExerciseType } from '../../types';

const Upload: React.FC = () => {
  const { submitFormCheck, isLoading, error } = useFormCheck();
  const [video, setVideo] = useState<File | null>(null);
  const [exerciseType, setExerciseType] = useState<ExerciseType>('squat');
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
        await submitFormCheck(video, exerciseType, notes);
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
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Upload Form Check
      </Typography>
      <Paper sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
        <form onSubmit={handleSubmit}>
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
          <FormControl fullWidth sx={{ mb: 3 }}>
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
            </Select>
          </FormControl>
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
        </form>
      </Paper>
    </Box>
  );
};

export default Upload; 
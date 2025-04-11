import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Typography,
  IconButton,
  Grid,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { WorkoutTemplate, WorkoutExercise } from '../../services/workoutPlanningService';
import { Exercise } from '../../services/exerciseLibraryService';

interface TemplateFormProps {
  template?: WorkoutTemplate;
  exercises: Exercise[];
  onSubmit: (template: Omit<WorkoutTemplate, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onCancel: () => void;
}

export const TemplateForm: React.FC<TemplateFormProps> = ({
  template,
  exercises,
  onSubmit,
  onCancel,
}) => {
  const [name, setName] = useState(template?.name || '');
  const [description, setDescription] = useState(template?.description || '');
  const [difficulty, setDifficulty] = useState(template?.difficulty || 'beginner');
  const [estimatedDuration, setEstimatedDuration] = useState(template?.estimatedDuration || 30);
  const [targetMuscleGroups, setTargetMuscleGroups] = useState<string[]>(template?.targetMuscleGroups || []);
  const [workoutExercises, setWorkoutExercises] = useState<WorkoutExercise[]>(template?.exercises || []);

  const handleAddExercise = () => {
    const newExercise: WorkoutExercise = {
      exercise: exercises[0],
      sets: 3,
      reps: 10,
      restTime: 60,
      order: workoutExercises.length,
    };
    setWorkoutExercises([...workoutExercises, newExercise]);
  };

  const handleRemoveExercise = (index: number) => {
    const updatedExercises = workoutExercises.filter((_, i) => i !== index);
    setWorkoutExercises(updatedExercises);
  };

  const handleExerciseChange = (index: number, field: keyof WorkoutExercise, value: any) => {
    const updatedExercises = [...workoutExercises];
    updatedExercises[index] = {
      ...updatedExercises[index],
      [field]: value,
    };
    setWorkoutExercises(updatedExercises);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      description,
      difficulty,
      estimatedDuration,
      targetMuscleGroups,
      exercises: workoutExercises,
    });
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ p: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Template Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            rows={3}
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <FormControl fullWidth>
            <InputLabel>Difficulty</InputLabel>
            <Select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value as 'beginner' | 'intermediate' | 'advanced')}
              label="Difficulty"
            >
              <MenuItem value="beginner">Beginner</MenuItem>
              <MenuItem value="intermediate">Intermediate</MenuItem>
              <MenuItem value="advanced">Advanced</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6}>
          <TextField
            fullWidth
            type="number"
            label="Estimated Duration (minutes)"
            value={estimatedDuration}
            onChange={(e) => setEstimatedDuration(Number(e.target.value))}
            required
          />
        </Grid>

        {/* Exercises Section */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom>
            Exercises
          </Typography>
          {workoutExercises.map((exercise, index) => (
            <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid #ddd', borderRadius: 1 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Exercise</InputLabel>
                    <Select
                      value={exercise.exercise.id}
                      onChange={(e) => {
                        const selectedExercise = exercises.find(ex => ex.id === e.target.value);
                        if (selectedExercise) {
                          handleExerciseChange(index, 'exercise', selectedExercise);
                        }
                      }}
                      label="Exercise"
                    >
                      {exercises.map((ex) => (
                        <MenuItem key={ex.id} value={ex.id}>
                          {ex.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={2}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Sets"
                    value={exercise.sets}
                    onChange={(e) => handleExerciseChange(index, 'sets', Number(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12} sm={2}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Reps"
                    value={exercise.reps}
                    onChange={(e) => handleExerciseChange(index, 'reps', Number(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Rest Time (seconds)"
                    value={exercise.restTime}
                    onChange={(e) => handleExerciseChange(index, 'restTime', Number(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12} sm={1}>
                  <IconButton onClick={() => handleRemoveExercise(index)} color="error">
                    <DeleteIcon />
                  </IconButton>
                </Grid>
              </Grid>
            </Box>
          ))}
          <Button
            startIcon={<AddIcon />}
            onClick={handleAddExercise}
            variant="outlined"
            sx={{ mt: 1 }}
          >
            Add Exercise
          </Button>
        </Grid>

        {/* Form Actions */}
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
            <Button onClick={onCancel} variant="outlined">
              Cancel
            </Button>
            <Button type="submit" variant="contained">
              {template ? 'Update Template' : 'Create Template'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}; 
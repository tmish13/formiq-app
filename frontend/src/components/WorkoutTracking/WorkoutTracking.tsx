import React from 'react';
import { useWorkoutTracking } from '../../hooks/useWorkoutTracking';
import { Box, Button, Typography, CircularProgress, List, ListItem, ListItemText } from '@mui/material';
import { WorkoutPlan, Workout } from '../../types/workout';

export const WorkoutTracking: React.FC = () => {
  const {
    workoutPlans,
    workoutHistory,
    currentWorkout,
    isLoading,
    error,
    startWorkout,
    endWorkout,
    saveWorkoutEntry,
    selectWorkoutPlan,
  } = useWorkoutTracking();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={2}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  const handlePlanSelect = (plan: WorkoutPlan) => {
    selectWorkoutPlan(plan.id);
  };

  const handleCompleteSet = () => {
    if (!currentWorkout) return;

    const currentExercise = currentWorkout.workouts[currentWorkout.currentWorkoutIndex]
      .exercises[currentWorkout.currentExerciseIndex];

    saveWorkoutEntry({
      exerciseId: currentExercise.id,
      setNumber: currentWorkout.currentSetIndex + 1,
      reps: currentExercise.reps,
      weight: currentExercise.weight || 0,
    });
  };

  return (
    <Box p={2}>
      <Typography variant="h4" gutterBottom>
        Workout Tracking
      </Typography>

      {!currentWorkout ? (
        <>
          <Typography variant="h6" gutterBottom>
            Available Workout Plans
          </Typography>
          <List>
            {workoutPlans.map((plan: WorkoutPlan) => (
              <ListItem
                key={plan.id}
                secondaryAction={
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={() => handlePlanSelect(plan)}
                  >
                    Select
                  </Button>
                }
              >
                <ListItemText
                  primary={plan.name}
                  secondary={plan.description}
                />
              </ListItem>
            ))}
          </List>
        </>
      ) : (
        <Box>
          <Typography variant="h6" gutterBottom>
            Current Workout
          </Typography>
          <Box mb={2}>
            <Typography variant="subtitle1">
              {currentWorkout.workouts[currentWorkout.currentWorkoutIndex].name}
            </Typography>
            <Typography>
              Exercise: {currentWorkout.workouts[currentWorkout.currentWorkoutIndex]
                .exercises[currentWorkout.currentExerciseIndex].name}
            </Typography>
            <Typography>
              Set {currentWorkout.currentSetIndex + 1} of {currentWorkout.workouts[currentWorkout.currentWorkoutIndex]
                .exercises[currentWorkout.currentExerciseIndex].sets}
            </Typography>
          </Box>
          <Box display="flex" gap={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleCompleteSet}
            >
              Complete Set
            </Button>
            <Button
              variant="outlined"
              color="secondary"
              onClick={endWorkout}
            >
              End Workout
            </Button>
          </Box>
        </Box>
      )}

      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          Workout History
        </Typography>
        <List>
          {workoutHistory.map((entry: { id: string; workout: Workout; duration: number }) => (
            <ListItem key={entry.id}>
              <ListItemText
                primary={entry.workout.name}
                secondary={`Duration: ${entry.duration} minutes`}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    </Box>
  );
}; 
import React, { useState } from 'react';
import styled from 'styled-components';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';

const WorkoutContainer = styled.div`
  min-height: 100vh;
  padding: ${({ theme }) => theme.spacing.xl};
  background-color: ${({ theme }) => theme.colors.background};
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const Title = styled.h1`
  color: ${({ theme }) => theme.colors.text};
`;

const WorkoutCard = styled.div`
  background-color: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => theme.spacing.xl};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.md};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const ExerciseList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.spacing.md};
`;

const ExerciseItem = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.spacing.md};
  padding: ${({ theme }) => theme.spacing.md};
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: ${({ theme }) => theme.borderRadius.md};
`;

const ExerciseInfo = styled.div`
  flex: 1;
`;

const ExerciseName = styled.h3`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.xs};
`;

const ExerciseDetails = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.spacing.md};
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.spacing.md};
  margin-top: ${({ theme }) => theme.spacing.md};
`;

interface Exercise {
  id: string;
  name: string;
  sets: number;
  reps: number;
  weight: number;
}

export const WorkoutPage: React.FC = () => {
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [currentExercise, setCurrentExercise] = useState<Partial<Exercise>>({});

  const handleAddExercise = (e: React.FormEvent) => {
    e.preventDefault();
    if (currentExercise.name) {
      setExercises([
        ...exercises,
        {
          id: Date.now().toString(),
          name: currentExercise.name,
          sets: currentExercise.sets || 0,
          reps: currentExercise.reps || 0,
          weight: currentExercise.weight || 0,
        },
      ]);
      setCurrentExercise({});
    }
  };

  const handleRemoveExercise = (id: string) => {
    setExercises(exercises.filter((exercise) => exercise.id !== id));
  };

  return (
    <WorkoutContainer>
      <Header>
        <Title>Workout Tracker</Title>
      </Header>

      <WorkoutCard>
        <Form onSubmit={handleAddExercise}>
          <Input
            label="Exercise Name"
            type="text"
            value={currentExercise.name || ''}
            onChange={(e) => setCurrentExercise({ ...currentExercise, name: e.target.value })}
            required
          />
          <div style={{ display: 'flex', gap: '16px' }}>
            <Input
              label="Sets"
              type="number"
              value={currentExercise.sets || ''}
              onChange={(e) => setCurrentExercise({ ...currentExercise, sets: parseInt(e.target.value) })}
              required
            />
            <Input
              label="Reps"
              type="number"
              value={currentExercise.reps || ''}
              onChange={(e) => setCurrentExercise({ ...currentExercise, reps: parseInt(e.target.value) })}
              required
            />
            <Input
              label="Weight (kg)"
              type="number"
              value={currentExercise.weight || ''}
              onChange={(e) => setCurrentExercise({ ...currentExercise, weight: parseInt(e.target.value) })}
              required
            />
          </div>
          <ButtonGroup>
            <Button type="submit" variant="primary">
              Add Exercise
            </Button>
          </ButtonGroup>
        </Form>
      </WorkoutCard>

      <WorkoutCard>
        <Title>Current Workout</Title>
        <ExerciseList>
          {exercises.map((exercise) => (
            <ExerciseItem key={exercise.id}>
              <ExerciseInfo>
                <ExerciseName>{exercise.name}</ExerciseName>
                <ExerciseDetails>
                  {exercise.sets} sets × {exercise.reps} reps @ {exercise.weight}kg
                </ExerciseDetails>
              </ExerciseInfo>
              <Button
                variant="outline"
                onClick={() => handleRemoveExercise(exercise.id)}
              >
                Remove
              </Button>
            </ExerciseItem>
          ))}
          {exercises.length === 0 && (
            <ExerciseItem>
              <ExerciseInfo>
                <ExerciseName>No exercises added yet</ExerciseName>
                <ExerciseDetails>Add exercises to start tracking your workout</ExerciseDetails>
              </ExerciseInfo>
            </ExerciseItem>
          )}
        </ExerciseList>
      </WorkoutCard>
    </WorkoutContainer>
  );
}; 
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { WorkoutTracking } from '@/components/WorkoutTracking/WorkoutTracking';
import { useWorkoutTracking } from '@/hooks/useWorkoutTracking';
import { WorkoutPlan, Workout } from '@/types/workout';
import { renderWithProviders } from '@/utils/test-utils';

// Mock the useWorkoutTracking hook
jest.mock('../../../hooks/useWorkoutTracking');

const mockWorkoutPlan: WorkoutPlan = {
  id: '1',
  userId: '123',
  name: 'Beginner Workout',
  description: 'A simple workout for beginners',
  frequency: '3x per week',
  duration: 4,
  workouts: [
    {
      id: '1',
      userId: '123',
      name: 'Full Body',
      description: 'Complete body workout',
      exercises: [
        {
          id: '1',
          name: 'Push-ups',
          sets: 3,
          reps: 10,
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  ],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const mockWorkoutHistory = [
  {
    id: '1',
    workout: mockWorkoutPlan.workouts[0],
    duration: 30,
  },
];

describe('WorkoutTracking', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useWorkoutTracking as jest.Mock).mockReturnValue({
      workoutPlans: [mockWorkoutPlan],
      workoutHistory: mockWorkoutHistory,
      currentWorkout: null,
      isLoading: false,
      error: null,
      startWorkout: jest.fn(),
      endWorkout: jest.fn(),
      saveWorkoutEntry: jest.fn(),
      selectWorkoutPlan: jest.fn(),
    });
  });

  it('renders workout plans', () => {
    renderWithProviders(<WorkoutTracking />);
    expect(screen.getByText('Beginner Workout')).toBeInTheDocument();
  });

  it('handles workout selection', () => {
    const mockSelectWorkoutPlan = jest.fn();
    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      selectWorkoutPlan: mockSelectWorkoutPlan,
    });

    renderWithProviders(<WorkoutTracking />);
    fireEvent.click(screen.getByText('Beginner Workout'));
    expect(mockSelectWorkoutPlan).toHaveBeenCalledWith('1');
  });

  it('displays current workout', () => {
    const currentWorkout = {
      workouts: mockWorkoutPlan.workouts,
      currentWorkoutIndex: 0,
      currentExerciseIndex: 0,
      currentSetIndex: 0,
    };

    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      currentWorkout,
    });

    renderWithProviders(<WorkoutTracking />);
    expect(screen.getByText('Full Body')).toBeInTheDocument();
    expect(screen.getByText('Push-ups')).toBeInTheDocument();
  });

  it('handles completing sets', () => {
    const mockSaveWorkoutEntry = jest.fn();
    const currentWorkout = {
      workouts: mockWorkoutPlan.workouts,
      currentWorkoutIndex: 0,
      currentExerciseIndex: 0,
      currentSetIndex: 0,
    };

    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      currentWorkout,
      saveWorkoutEntry: mockSaveWorkoutEntry,
    });

    renderWithProviders(<WorkoutTracking />);
    fireEvent.click(screen.getByText('Complete Set'));
    expect(mockSaveWorkoutEntry).toHaveBeenCalledWith({
      exerciseId: '1',
      setNumber: 1,
      reps: 10,
      weight: 0,
    });
  });

  it('saves workout history', async () => {
    const mockEndWorkout = jest.fn();
    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      endWorkout: mockEndWorkout,
    });

    renderWithProviders(<WorkoutTracking />);
    fireEvent.click(screen.getByText('End Workout'));
    expect(mockEndWorkout).toHaveBeenCalled();
  });

  it('handles errors', () => {
    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      error: 'Failed to load workout plans',
    });

    renderWithProviders(<WorkoutTracking />);
    expect(screen.getByText('Failed to load workout plans')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    (useWorkoutTracking as jest.Mock).mockReturnValue({
      ...useWorkoutTracking(),
      isLoading: true,
    });

    renderWithProviders(<WorkoutTracking />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
}); 
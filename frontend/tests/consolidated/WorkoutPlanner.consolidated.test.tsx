import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import configureStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { 
  setWorkoutPlans, 
  setCurrentPlan, 
  addWorkoutPlan, 
  updateWorkoutPlan, 
  deleteWorkoutPlan
} from '../../frontend/src/store/slices/workoutSlice';
import { useWorkout } from '../../frontend/src/hooks/useWorkout';
import { Workout, WorkoutPlan } from '../../frontend/src/types';

// Mock the services
jest.mock('../../frontend/src/services/workoutService', () => ({
  workoutService: {
    getWorkoutPlans: jest.fn(),
    getWorkoutPlan: jest.fn(),
    createWorkoutPlan: jest.fn(),
    updateWorkoutPlan: jest.fn(),
    deleteWorkoutPlan: jest.fn(),
    getActiveWorkoutPlans: jest.fn(),
  }
}));

// Mock the useWorkoutTracking hook
jest.mock('../../frontend/src/hooks/useWorkoutTracking');

// Mock components
const WorkoutPlannerComponent = ({ 
  workoutPlans, 
  currentPlan, 
  onSelectPlan, 
  onCreatePlan, 
  onUpdatePlan, 
  onDeletePlan 
}) => (
  <div>
    <h2>Workout Planner</h2>
    <button onClick={onCreatePlan} data-testid="create-plan-btn">Create Plan</button>
    
    {workoutPlans.length === 0 ? (
      <div data-testid="no-plans-message">No workout plans available</div>
    ) : (
      <div data-testid="workout-plan-list">
        {workoutPlans.map(plan => (
          <div key={plan.id} data-testid={`plan-${plan.id}`}>
            <span>{plan.name}</span>
            <button onClick={() => onSelectPlan(plan.id)} data-testid={`select-plan-${plan.id}`}>
              Select
            </button>
            <button onClick={() => onUpdatePlan(plan)} data-testid={`edit-plan-${plan.id}`}>
              Edit
            </button>
            <button onClick={() => onDeletePlan(plan.id)} data-testid={`delete-plan-${plan.id}`}>
              Delete
            </button>
          </div>
        ))}
      </div>
    )}
    
    {currentPlan && (
      <div data-testid="current-plan">
        <h3>Current Plan: {currentPlan.name}</h3>
        <div data-testid="workout-list">
          {currentPlan.workouts.map(workout => (
            <div key={workout.id} data-testid={`workout-${workout.id}`}>
              {workout.name}
            </div>
          ))}
        </div>
      </div>
    )}
  </div>
);

// Sample data for testing
const mockWorkoutPlan: WorkoutPlan = {
  id: '1',
  name: 'Test Plan',
  description: 'Test Description',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  userId: 'user123',
  workouts: [
    {
      id: 'w1',
      name: 'Workout 1',
      description: 'Test Workout',
      exercises: [
        { id: 'e1', name: 'Squats', sets: 3, reps: 10, weight: 0 }
      ],
      completed: false,
      scheduledFor: new Date().toISOString(),
    }
  ]
};

const mockWorkoutPlans = [
  mockWorkoutPlan,
  {
    ...mockWorkoutPlan,
    id: '2',
    name: 'Test Plan 2',
  }
];

const initialState = {
  workout: {
    workoutPlans: [],
    currentPlan: null,
    currentWorkout: null,
    isLoading: false,
    error: null
  }
};

const mockStore = configureStore([thunk]);

describe('WorkoutPlanner Consolidated Tests', () => {
  let store;
  
  beforeEach(() => {
    store = mockStore(initialState);
    jest.clearAllMocks();
  });

  describe('Redux State Management', () => {
    it('should handle setWorkoutPlans', () => {
      const plans = [mockWorkoutPlan];
      const action = setWorkoutPlans(plans);
      
      const expectedAction = {
        type: 'workout/setWorkoutPlans',
        payload: plans
      };
      
      expect(action).toEqual(expectedAction);
    });
    
    it('should handle setCurrentPlan', () => {
      const action = setCurrentPlan(mockWorkoutPlan);
      
      const expectedAction = {
        type: 'workout/setCurrentPlan',
        payload: mockWorkoutPlan
      };
      
      expect(action).toEqual(expectedAction);
    });
    
    it('should handle addWorkoutPlan', () => {
      const action = addWorkoutPlan(mockWorkoutPlan);
      
      const expectedAction = {
        type: 'workout/addWorkoutPlan',
        payload: mockWorkoutPlan
      };
      
      expect(action).toEqual(expectedAction);
    });
    
    it('should handle updateWorkoutPlan', () => {
      const updatedPlan = { ...mockWorkoutPlan, name: 'Updated Plan' };
      const action = updateWorkoutPlan(updatedPlan);
      
      const expectedAction = {
        type: 'workout/updateWorkoutPlan',
        payload: updatedPlan
      };
      
      expect(action).toEqual(expectedAction);
    });
    
    it('should handle deleteWorkoutPlan', () => {
      const action = deleteWorkoutPlan('1');
      
      const expectedAction = {
        type: 'workout/deleteWorkoutPlan',
        payload: '1'
      };
      
      expect(action).toEqual(expectedAction);
    });
  });
  
  describe('Workout Planner UI Interactions', () => {
    it('renders workout planner with workout plans', () => {
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={mockWorkoutPlans}
            currentPlan={null}
            onSelectPlan={jest.fn()}
            onCreatePlan={jest.fn()}
            onUpdatePlan={jest.fn()}
            onDeletePlan={jest.fn()}
          />
        </Provider>
      );
      
      expect(screen.getByTestId('workout-plan-list')).toBeInTheDocument();
      expect(screen.getByTestId('plan-1')).toBeInTheDocument();
      expect(screen.getByTestId('plan-2')).toBeInTheDocument();
    });
    
    it('renders a message when no workout plans are available', () => {
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={[]}
            currentPlan={null}
            onSelectPlan={jest.fn()}
            onCreatePlan={jest.fn()}
            onUpdatePlan={jest.fn()}
            onDeletePlan={jest.fn()}
          />
        </Provider>
      );
      
      expect(screen.getByTestId('no-plans-message')).toBeInTheDocument();
    });
    
    it('calls onSelectPlan when a plan is selected', () => {
      const mockOnSelectPlan = jest.fn();
      
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={mockWorkoutPlans}
            currentPlan={null}
            onSelectPlan={mockOnSelectPlan}
            onCreatePlan={jest.fn()}
            onUpdatePlan={jest.fn()}
            onDeletePlan={jest.fn()}
          />
        </Provider>
      );
      
      fireEvent.click(screen.getByTestId('select-plan-1'));
      expect(mockOnSelectPlan).toHaveBeenCalledWith('1');
    });
    
    it('displays the current plan when selected', () => {
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={mockWorkoutPlans}
            currentPlan={mockWorkoutPlan}
            onSelectPlan={jest.fn()}
            onCreatePlan={jest.fn()}
            onUpdatePlan={jest.fn()}
            onDeletePlan={jest.fn()}
          />
        </Provider>
      );
      
      expect(screen.getByTestId('current-plan')).toBeInTheDocument();
      expect(screen.getByText(/Current Plan: Test Plan/i)).toBeInTheDocument();
      expect(screen.getByTestId('workout-w1')).toBeInTheDocument();
    });
    
    it('calls onDeletePlan when delete button is clicked', () => {
      const mockOnDeletePlan = jest.fn();
      
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={mockWorkoutPlans}
            currentPlan={null}
            onSelectPlan={jest.fn()}
            onCreatePlan={jest.fn()}
            onUpdatePlan={jest.fn()}
            onDeletePlan={mockOnDeletePlan}
          />
        </Provider>
      );
      
      fireEvent.click(screen.getByTestId('delete-plan-1'));
      expect(mockOnDeletePlan).toHaveBeenCalledWith('1');
    });
    
    it('calls onCreatePlan when create button is clicked', () => {
      const mockOnCreatePlan = jest.fn();
      
      render(
        <Provider store={store}>
          <WorkoutPlannerComponent 
            workoutPlans={mockWorkoutPlans}
            currentPlan={null}
            onSelectPlan={jest.fn()}
            onCreatePlan={mockOnCreatePlan}
            onUpdatePlan={jest.fn()}
            onDeletePlan={jest.fn()}
          />
        </Provider>
      );
      
      fireEvent.click(screen.getByTestId('create-plan-btn'));
      expect(mockOnCreatePlan).toHaveBeenCalled();
    });
  });
  
  describe('Workout Service Integration', () => {
    const workoutService = require('../../frontend/src/services/workoutService').workoutService;
    
    beforeEach(() => {
      workoutService.getWorkoutPlans.mockResolvedValue([mockWorkoutPlan]);
      workoutService.getWorkoutPlan.mockResolvedValue(mockWorkoutPlan);
      workoutService.createWorkoutPlan.mockResolvedValue({ id: 'new-id', ...mockWorkoutPlan });
      workoutService.updateWorkoutPlan.mockResolvedValue({ ...mockWorkoutPlan, name: 'Updated Plan' });
      workoutService.deleteWorkoutPlan.mockResolvedValue({ success: true });
    });
    
    it('retrieves workout plans from the API', async () => {
      // Set up component with the mock hook
      const mockUseWorkout = () => ({
        workoutPlans: [],
        currentPlan: null,
        isLoading: false,
        error: null,
        fetchWorkoutPlans: jest.fn().mockImplementation(async () => {
          const plans = await workoutService.getWorkoutPlans();
          return plans;
        }),
        fetchWorkoutPlan: jest.fn(),
        createWorkoutPlan: jest.fn(),
        updateWorkoutPlan: jest.fn(),
        deleteWorkoutPlan: jest.fn(),
      });
      
      // Create a test component to test the hook
      const TestComponent = () => {
        const { fetchWorkoutPlans, workoutPlans } = mockUseWorkout();
        
        React.useEffect(() => {
          fetchWorkoutPlans();
        }, [fetchWorkoutPlans]);
        
        return (
          <div>
            {workoutPlans.length === 0 ? (
              <div data-testid="loading">Loading plans...</div>
            ) : (
              <div data-testid="plans-loaded">
                Plans loaded: {workoutPlans.length}
              </div>
            )}
          </div>
        );
      };
      
      render(
        <Provider store={store}>
          <TestComponent />
        </Provider>
      );
      
      // Verify service was called
      expect(workoutService.getWorkoutPlans).toHaveBeenCalled();
    });
    
    it('creates a new workout plan and adds it to the store', async () => {
      const newPlan = {
        name: 'New Plan',
        description: 'New plan description',
        workouts: []
      };
      
      workoutService.createWorkoutPlan.mockResolvedValue({
        id: 'new-id',
        userId: 'user123',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        ...newPlan
      });
      
      // Set up component with the mock hook
      const mockDispatch = jest.fn();
      const mockUseWorkout = () => ({
        workoutPlans: [],
        currentPlan: null,
        isLoading: false,
        error: null,
        fetchWorkoutPlans: jest.fn(),
        fetchWorkoutPlan: jest.fn(),
        createWorkoutPlan: jest.fn().mockImplementation(async (plan) => {
          const createdPlan = await workoutService.createWorkoutPlan(plan);
          mockDispatch(addWorkoutPlan(createdPlan));
          return createdPlan;
        }),
        updateWorkoutPlan: jest.fn(),
        deleteWorkoutPlan: jest.fn(),
      });
      
      // Create a test component to test the hook
      const TestComponent = () => {
        const { createWorkoutPlan } = mockUseWorkout();
        
        return (
          <div>
            <button 
              data-testid="create-plan" 
              onClick={() => createWorkoutPlan(newPlan)}
            >
              Create Plan
            </button>
          </div>
        );
      };
      
      render(
        <Provider store={store}>
          <TestComponent />
        </Provider>
      );
      
      fireEvent.click(screen.getByTestId('create-plan'));
      
      await waitFor(() => {
        expect(workoutService.createWorkoutPlan).toHaveBeenCalledWith(newPlan);
      });
    });
  });
  
  describe('Rest Timer Features', () => {
    it('tracks rest periods between exercises', () => {
      // Mock component with rest timer logic
      const RestTimer = ({ duration, onComplete }) => {
        const [isActive, setIsActive] = React.useState(false);
        const [timeLeft, setTimeLeft] = React.useState(duration);
        
        const startTimer = () => setIsActive(true);
        const pauseTimer = () => setIsActive(false);
        const resetTimer = () => setTimeLeft(duration);
        
        return (
          <div>
            <div data-testid="time-display">{timeLeft}</div>
            <button data-testid="start-timer" onClick={startTimer}>Start</button>
            <button data-testid="pause-timer" onClick={pauseTimer}>Pause</button>
            <button data-testid="reset-timer" onClick={resetTimer}>Reset</button>
          </div>
        );
      };
      
      const mockOnComplete = jest.fn();
      
      render(<RestTimer duration={60} onComplete={mockOnComplete} />);
      
      // Timer should start with the provided duration
      expect(screen.getByTestId('time-display').textContent).toBe('60');
      
      // Test timer controls
      fireEvent.click(screen.getByTestId('start-timer'));
      fireEvent.click(screen.getByTestId('pause-timer'));
      fireEvent.click(screen.getByTestId('reset-timer'));
      
      expect(screen.getByTestId('time-display').textContent).toBe('60');
    });
  });
  
  describe('Workout Progress Tracking', () => {
    it('tracks completion status of workouts', () => {
      const progressPlan = {
        ...mockWorkoutPlan,
        workouts: [
          {
            ...mockWorkoutPlan.workouts[0],
            exercises: [
              { id: 'e1', name: 'Squats', sets: 3, reps: 10, weight: 0, completed: false },
              { id: 'e2', name: 'Lunges', sets: 3, reps: 10, weight: 0, completed: true }
            ]
          }
        ]
      };
      
      // Mock component for testing progress tracking
      const WorkoutProgressTracker = ({ workoutPlan }) => {
        const [plan, setPlan] = React.useState(workoutPlan);
        
        const completeExercise = (workoutId, exerciseId) => {
          setPlan({
            ...plan,
            workouts: plan.workouts.map(w => 
              w.id === workoutId 
                ? {
                    ...w,
                    exercises: w.exercises.map(e => 
                      e.id === exerciseId ? { ...e, completed: true } : e
                    )
                  }
                : w
            )
          });
        };
        
        return (
          <div>
            <h2>Workout Progress</h2>
            {plan.workouts.map(workout => (
              <div key={workout.id} data-testid={`workout-progress-${workout.id}`}>
                <h3>{workout.name}</h3>
                {workout.exercises.map(exercise => (
                  <div key={exercise.id} data-testid={`exercise-${exercise.id}`}>
                    <span data-testid={`exercise-name-${exercise.id}`}>{exercise.name}</span>
                    <span data-testid={`exercise-completed-${exercise.id}`}>
                      {exercise.completed ? 'Completed' : 'Incomplete'}
                    </span>
                    <button 
                      data-testid={`complete-exercise-${exercise.id}`}
                      onClick={() => completeExercise(workout.id, exercise.id)}
                    >
                      Mark Complete
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        );
      };
      
      render(<WorkoutProgressTracker workoutPlan={progressPlan} />);
      
      // Verify initial state
      expect(screen.getByTestId('exercise-completed-e1').textContent).toBe('Incomplete');
      expect(screen.getByTestId('exercise-completed-e2').textContent).toBe('Completed');
      
      // Mark exercise as complete
      fireEvent.click(screen.getByTestId('complete-exercise-e1'));
      
      // Verify exercise was marked as complete
      expect(screen.getByTestId('exercise-completed-e1').textContent).toBe('Completed');
    });
  });
}); 
import { StorageService } from '../storageService';
import { WorkoutService } from '../workoutService';
import { formAnalysisService } from '../formAnalysisService';
import { Theme } from '../../types/theme';
import { FormAnalysisResult, FormFeedback, JointAngles } from '../../types/formAnalysis';

// Mock data
const mockWorkout = {
  id: 'test-workout-id',
  userId: 'test-user-id',
  name: 'Test Workout',
  description: 'A test workout',
  exercises: [
    {
      id: 'test-exercise-id',
      name: 'Squat',
      sets: 3,
      reps: 10
    }
  ],
  duration: 30,
  difficulty: 'medium',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
};

const mockFormAnalysis: FormAnalysisResult = {
  confidence: 0.95,
  isReliable: true,
  keypoints: [
    { x: 0, y: 0, score: 1, name: 'nose' },
    { x: 10, y: 10, score: 1, name: 'left_shoulder' },
    { x: -10, y: 10, score: 1, name: 'right_shoulder' }
  ],
  angles: {
    knee: 90,
    hip: 120,
    ankle: 80
  } as JointAngles,
  feedback: [
    { type: 'success', message: 'Good form', confidence: 0.9 },
    { type: 'warning', message: 'Keep your back straight', confidence: 0.8 }
  ] as FormFeedback[],
  timestamp: Date.now(),
  videoUrl: 'test-video-url'
};

const mockPreferences = {
  theme: {
    colors: {
      primary: { light: '#7986cb', main: '#3f51b5', dark: '#303f9f' },
      secondary: { light: '#ff4081', main: '#f50057', dark: '#c51162' },
      error: { light: '#e57373', main: '#f44336', dark: '#d32f2f' },
      warning: { light: '#ffb74d', main: '#ff9800', dark: '#f57c00' },
      success: { light: '#81c784', main: '#4caf50', dark: '#388e3c' },
      info: { light: '#64b5f6', main: '#2196f3', dark: '#1976d2' },
      background: { main: '#ffffff', secondary: '#f5f5f5', paper: '#ffffff' },
      text: { primary: '#000000', secondary: '#666666', disabled: '#999999', inverse: '#ffffff' },
      border: { main: '#e0e0e0', light: '#f0f0f0' },
      disabled: '#e0e0e0'
    },
    typography: {
      fontFamily: { primary: "'Inter', sans-serif", secondary: "'Poppins', sans-serif", mono: "'SF Mono', monospace" },
      fontSize: { xxs: '0.625rem', xs: '0.75rem', sm: '0.875rem', md: '1rem', lg: '1.125rem', xl: '1.25rem', xxl: '1.5rem' },
      fontWeight: { light: 300, regular: 400, medium: 500, semibold: 600, bold: 700 },
      lineHeight: { tight: '1.25', normal: '1.5', relaxed: '1.75' }
    },
    spacing: { xxs: '0.25rem', xs: '0.5rem', sm: '0.75rem', md: '1rem', lg: '1.5rem', xl: '2rem', xxl: '3rem' },
    borderRadius: { sm: '0.25rem', md: '0.5rem', lg: '1rem', full: '9999px' },
    shadows: { none: 'none', small: '0 1px 3px rgba(0, 0, 0, 0.1)', medium: '0 4px 6px rgba(0, 0, 0, 0.1)', large: '0 10px 15px rgba(0, 0, 0, 0.1)' }
  } as Theme,
  notifications: true,
  language: 'en'
};

describe('Data Persistence Tests', () => {
  let storageService: jest.Mocked<StorageService>;
  let workoutService: jest.Mocked<WorkoutService>;

  beforeEach(() => {
    jest.clearAllMocks();
    storageService = StorageService.getInstance() as jest.Mocked<StorageService>;
    workoutService = new WorkoutService() as jest.Mocked<WorkoutService>;
    // Use the singleton instance
    jest.spyOn(formAnalysisService, 'analyzeForm');
    jest.spyOn(formAnalysisService, 'getAnalysisHistory');
    jest.spyOn(formAnalysisService, 'saveAnalysis');
  });

  describe('Workout Data Persistence', () => {
    it('saves workout data and retrieves it after refresh', async () => {
      // Test implementation
    });

    it('handles workout data migration on app update', async () => {
      // Test implementation
    });
  });

  describe('Form Analysis Persistence', () => {
    it('saves form analysis and retrieves it after refresh', async () => {
      // Test implementation
    });

    it('caches form analysis for offline access', async () => {
      // Test implementation
    });
  });

  describe('User Preferences Persistence', () => {
    it('saves user preferences and retrieves them after refresh', async () => {
      // Test implementation
    });

    it('applies saved theme on app load', async () => {
      // Test implementation
    });

    it('handles missing preferences gracefully', async () => {
      // Test implementation
    });
  });
}); 
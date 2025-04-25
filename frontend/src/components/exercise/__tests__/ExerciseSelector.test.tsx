import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from 'styled-components';
import { ExerciseSelector } from '../ExerciseSelector';
import { ExerciseType, exerciseConfigs } from '../../../services/poseAnalysis/exerciseTypes';
import { mockThemeWithFallbacks as mockTheme } from '../../../../tests/__mocks__/mockTheme';
import { theme } from '../../../theme';

// Mock styled-components
jest.mock('styled-components', () => {
  const actual = jest.requireActual('styled-components');
  return {
    ...actual,
    styled: {
      div: () => (props: any) => <div data-testid="container" {...props} />,
      h3: () => (props: any) => <h3 data-testid="title" {...props}>{props.children}</h3>,
      select: () => (props: any) => (
        <select 
          data-testid="exercise-select" 
          {...props}
        >
          {props.children}
        </select>
      ),
      ul: () => (props: any) => <ul data-testid="guidelines-list" {...props}>{props.children}</ul>,
      li: () => (props: any) => <li data-testid="guideline-item" {...props}>{props.children}</li>
    },
    ThemeProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="theme-provider">{children}</div>
  };
});

// Mock exercise types and configurations
jest.mock('../../../services/poseAnalysis/exerciseTypes', () => {
  const ExerciseType = {
    SQUAT: 'squat',
    PUSHUP: 'pushup',
    PLANK: 'plank',
  };

  const exerciseConfigs = {
    [ExerciseType.SQUAT]: {
      name: 'Squat',
      formChecks: [
        { name: 'Knee Position', description: 'Keep knees over toes' },
        { name: 'Back Position', description: 'Keep back straight' }
      ]
    },
    [ExerciseType.PUSHUP]: {
      name: 'Push-up',
      formChecks: [
        { name: 'Elbow Position', description: 'Keep elbows at 45-degree angle' },
        { name: 'Core Engagement', description: 'Keep core tight' }
      ]
    },
    [ExerciseType.PLANK]: {
      name: 'Plank',
      formChecks: [
        { name: 'Spine Alignment', description: 'Keep spine neutral' },
        { name: 'Shoulder Position', description: 'Shoulders over elbows' }
      ]
    }
  };

  return {
    ExerciseType,
    exerciseConfigs
  };
});

const renderWithTheme = (ui: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {ui}
    </ThemeProvider>
  );
};

describe('ExerciseSelector Component', () => {
  const mockOnExerciseChange = jest.fn();
  const defaultProps = {
    selectedExercise: ExerciseType.SQUAT,
    onExerciseChange: mockOnExerciseChange,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with default exercise selected', () => {
    renderWithTheme(<ExerciseSelector {...defaultProps} />);
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    expect(select.value).toBe(ExerciseType.SQUAT);
  });

  it('displays all exercise options', () => {
    renderWithTheme(<ExerciseSelector {...defaultProps} />);
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    const options = Array.from(select.options).map(option => option.value);
    expect(options).toEqual(Object.values(ExerciseType));
  });

  it('calls onExerciseChange when selection changes', () => {
    renderWithTheme(<ExerciseSelector {...defaultProps} />);
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    
    fireEvent.change(select, { target: { value: ExerciseType.PUSHUP } });
    expect(mockOnExerciseChange).toHaveBeenCalledWith(ExerciseType.PUSHUP);
  });

  it('formats exercise name by adding spaces before capital letters', () => {
    renderWithTheme(<ExerciseSelector {...defaultProps} />);
    const select = screen.getByRole('combobox') as HTMLSelectElement;
    const options = Array.from(select.options);
    
    options.forEach(option => {
      const formattedName = option.textContent?.trim();
      expect(formattedName).toMatch(/^[A-Z][a-z]+(\s[A-Z][a-z]+)*$/);
    });
  });

  it('displays exercise guidelines for selected exercise', () => {
    renderWithTheme(<ExerciseSelector {...defaultProps} />);
    expect(screen.getByText('Exercise Form Guidelines')).toBeInTheDocument();
    expect(screen.getByText(/Keep back straight/i)).toBeInTheDocument();
  });
}); 
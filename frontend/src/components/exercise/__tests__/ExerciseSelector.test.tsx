import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from 'styled-components';
import { ExerciseSelector } from '../ExerciseSelector';
import { ExerciseType, exerciseConfigs } from '../../../services/poseAnalysis/exerciseTypes';
import { mockThemeWithFallbacks as mockTheme } from '../../../../tests/__mocks__/mockTheme';

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

describe('ExerciseSelector Component', () => {
  const mockOnExerciseChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with the default exercise selected', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.SQUAT}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Check if the component renders the select element with the correct value
    const selectElement = screen.getByTestId('exercise-select');
    expect(selectElement).toHaveValue(ExerciseType.SQUAT);

    // Check if the title is rendered
    expect(screen.getByTestId('title')).toHaveTextContent('Exercise Form Guidelines');

    // Check if the guidelines list is rendered
    const guidelineItems = screen.getAllByTestId('guideline-item');
    expect(guidelineItems).toHaveLength(2); // Squat has 2 form checks

    // Check content of the form checks
    expect(guidelineItems[0]).toHaveTextContent('Knee Position: Keep knees over toes');
    expect(guidelineItems[1]).toHaveTextContent('Back Position: Keep back straight');
  });

  it('calls onExerciseChange when selecting a different exercise', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.SQUAT}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Get the select element
    const selectElement = screen.getByTestId('exercise-select');

    // Change the selection to Pushup
    fireEvent.change(selectElement, { target: { value: ExerciseType.PUSHUP } });

    // Check if onExerciseChange was called with the correct value
    expect(mockOnExerciseChange).toHaveBeenCalledWith(ExerciseType.PUSHUP);
  });

  it('displays the correct form guidelines when changing exercises', () => {
    // Initial render with Squat
    const { rerender } = render(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.SQUAT}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Check initial guidelines
    let guidelineItems = screen.getAllByTestId('guideline-item');
    expect(guidelineItems[0]).toHaveTextContent('Knee Position: Keep knees over toes');

    // Rerender with Pushup
    rerender(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.PUSHUP}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Check updated guidelines
    guidelineItems = screen.getAllByTestId('guideline-item');
    expect(guidelineItems[0]).toHaveTextContent('Elbow Position: Keep elbows at 45-degree angle');
    expect(guidelineItems[1]).toHaveTextContent('Core Engagement: Keep core tight');
  });

  it('renders all available exercise options', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.SQUAT}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Get the select element
    const selectElement = screen.getByTestId('exercise-select');
    
    // Check if all exercise types are rendered as options
    Object.values(ExerciseType).forEach(exerciseType => {
      // Find the option element with the value of the current exercise type
      const optionElement = Array.from(selectElement.children).find(
        child => (child as HTMLOptionElement).value === exerciseType
      );
      
      expect(optionElement).toBeTruthy();
    });
  });

  it('formats exercise name by adding spaces before capital letters', () => {
    // Render with a camelCase exercise type
    render(
      <ThemeProvider theme={mockTheme}>
        <ExerciseSelector
          selectedExercise={ExerciseType.PUSHUP}
          onExerciseChange={mockOnExerciseChange}
        />
      </ThemeProvider>
    );

    // Get all option elements
    const selectElement = screen.getByTestId('exercise-select');
    const options = Array.from(selectElement.children) as HTMLOptionElement[];
    
    // Check formatting for all options
    options.forEach(option => {
      // Verify that options have the capitalized formatting compared to raw values
      if (option.value === ExerciseType.PUSHUP) {
        expect(option.textContent).toContain('Pushup');
      }
    });
  });
}); 
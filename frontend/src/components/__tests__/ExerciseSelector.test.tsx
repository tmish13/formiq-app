import React from 'react';
import { render, fireEvent } from '@testing-library/react';
import { ExerciseSelector } from '../ExerciseSelector';
import { ExerciseType } from '../../services/poseAnalysis/exerciseTypes';

describe('ExerciseSelector', () => {
  const mockProps = {
    selectedExercise: ExerciseType.SQUAT,
    onExerciseChange: jest.fn(),
  };

  it('renders correctly with default props', () => {
    const { getByTestId } = render(<ExerciseSelector {...mockProps} />);
    expect(getByTestId('exercise-selector')).toBeInTheDocument();
  });

  it('displays all exercise options', () => {
    const { getByTestId } = render(<ExerciseSelector {...mockProps} />);
    const select = getByTestId('exercise-select') as HTMLSelectElement;
    
    expect(select.value).toBe(ExerciseType.SQUAT);
    
    // Check if all exercise types are present as options
    const options = Array.from(select.options);
    expect(options.length).toBe(Object.values(ExerciseType).length);
    
    Object.values(ExerciseType).forEach(type => {
      const option = options.find(opt => opt.value === type);
      expect(option).toBeTruthy();
      expect(option?.textContent).toBe(type.replace(/([A-Z])/g, ' $1').trim());
    });
  });

  it('calls onExerciseChange when a different exercise is selected', () => {
    const { getByTestId } = render(<ExerciseSelector {...mockProps} />);
    const select = getByTestId('exercise-select') as HTMLSelectElement;
    
    fireEvent.change(select, { target: { value: ExerciseType.PUSHUP } });
    expect(mockProps.onExerciseChange).toHaveBeenCalledWith(ExerciseType.PUSHUP);
  });

  it('displays exercise guidelines', () => {
    const { getByTestId } = render(<ExerciseSelector {...mockProps} />);
    const guidelines = getByTestId('exercise-guidelines');
    expect(guidelines).toBeInTheDocument();
  });
}); 
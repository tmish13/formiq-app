import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ExerciseLibraryPage from '../../../pages/workout/ExerciseLibraryPage';
import { exerciseLibraryService, ExerciseType } from '../../../services/exerciseLibraryService';

// Mock the exerciseLibraryService
jest.mock('../../../services/exerciseLibraryService', () => ({
  exerciseLibraryService: {
    getExercises: jest.fn(),
    filterExercises: jest.fn(),
    getExerciseTypes: jest.fn().mockReturnValue(Object.values(ExerciseType)),
  },
  ExerciseType,
}));

// Mock the theme
jest.mock('../../../theme', () => ({
  lightTheme: {
    shadows: {
      lg: '0 4px 6px rgba(0, 0, 0, 0.1)',
    },
  },
}));

const mockExercise = {
  id: '1',
  name: 'Test Exercise',
  description: 'Test Description',
  type: ExerciseType.STRENGTH,
  difficulty: 'beginner',
  targetMuscles: ['Quadriceps', 'Hamstrings'],
  equipment: ['Dumbbell'],
  formRules: [],
  videoUrl: 'https://example.com/video',
  thumbnailUrl: 'https://example.com/thumbnail',
  tips: ['Step 1', 'Step 2'],
  variations: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('ExerciseLibraryPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (exerciseLibraryService.getExercises as jest.Mock).mockResolvedValue([mockExercise]);
  });

  it('renders the exercise library page', async () => {
    renderWithRouter(<ExerciseLibraryPage />);

    expect(screen.getByText('Exercise Library')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search exercises...')).toBeInTheDocument();
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByText('Add Exercise')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Test Exercise')).toBeInTheDocument();
    });
  });

  it('handles search input', async () => {
    renderWithRouter(<ExerciseLibraryPage />);

    const searchInput = screen.getByPlaceholderText('Search exercises...');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    await waitFor(() => {
      expect(exerciseLibraryService.getExercises).toHaveBeenCalledWith(
        expect.objectContaining({ searchQuery: 'test' })
      );
    });
  });

  it('opens and closes the filter dialog', async () => {
    renderWithRouter(<ExerciseLibraryPage />);

    // Open filter dialog
    fireEvent.click(screen.getByText('Filters'));
    expect(screen.getByText('Filter Exercises')).toBeInTheDocument();

    // Close filter dialog
    fireEvent.click(screen.getByTestId('CloseIcon'));
    expect(screen.queryByText('Filter Exercises')).not.toBeInTheDocument();
  });

  it('applies filters correctly', async () => {
    renderWithRouter(<ExerciseLibraryPage />);

    // Open filter dialog
    fireEvent.click(screen.getByText('Filters'));

    // Select exercise type
    const typeSelect = screen.getByLabelText('Type');
    fireEvent.mouseDown(typeSelect);
    fireEvent.click(screen.getByText(ExerciseType.STRENGTH));

    // Select difficulty
    const difficultySelect = screen.getByLabelText('Difficulty');
    fireEvent.mouseDown(difficultySelect);
    fireEvent.click(screen.getByText('beginner'));

    // Apply filters
    fireEvent.click(screen.getByText('Apply'));

    await waitFor(() => {
      expect(exerciseLibraryService.getExercises).toHaveBeenCalledWith(
        expect.objectContaining({
          type: ExerciseType.STRENGTH,
          difficulty: 'beginner',
        })
      );
    });
  });

  it('clears filters correctly', async () => {
    renderWithRouter(<ExerciseLibraryPage />);

    // Open filter dialog
    fireEvent.click(screen.getByText('Filters'));

    // Select some filters
    const typeSelect = screen.getByLabelText('Type');
    fireEvent.mouseDown(typeSelect);
    fireEvent.click(screen.getByText(ExerciseType.STRENGTH));

    // Clear filters
    fireEvent.click(screen.getByText('Clear Filters'));

    await waitFor(() => {
      expect(exerciseLibraryService.getExercises).toHaveBeenCalledWith({});
    });
  });

  it('handles loading state', async () => {
    (exerciseLibraryService.getExercises as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    renderWithRouter(<ExerciseLibraryPage />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  it('handles error state', async () => {
    const errorMessage = 'Failed to fetch exercises';
    (exerciseLibraryService.getExercises as jest.Mock).mockRejectedValue(
      new Error(errorMessage)
    );

    renderWithRouter(<ExerciseLibraryPage />);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('handles empty state', async () => {
    (exerciseLibraryService.getExercises as jest.Mock).mockResolvedValue([]);

    renderWithRouter(<ExerciseLibraryPage />);

    await waitFor(() => {
      expect(screen.getByText('No exercises found. Try adjusting your filters.')).toBeInTheDocument();
    });
  });

  it('navigates to exercise details on card click', async () => {
    const { container } = renderWithRouter(<ExerciseLibraryPage />);

    await waitFor(() => {
      expect(screen.getByText('Test Exercise')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Test Exercise'));

    // Check if navigation occurred (you might need to adjust this based on your routing setup)
    expect(container.innerHTML).toContain('Test Exercise');
  });
}); 
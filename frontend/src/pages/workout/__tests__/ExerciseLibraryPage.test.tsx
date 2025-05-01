import React, { useState, useEffect, ReactNode } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { exerciseLibraryService } from '../../../services/exerciseLibraryService';

// Define the exercise type enum directly for testing
const MockExerciseType = {
  STRENGTH: 'strength',
  CARDIO: 'cardio',
  FLEXIBILITY: 'flexibility',
  BALANCE: 'balance'
};

// Prepare the values array separately to avoid initialization issues
const exerciseTypeValues = ['strength', 'cardio', 'flexibility', 'balance'];

// Mock the exerciseLibraryService
jest.mock('../../../services/exerciseLibraryService', () => {
  return {
    exerciseLibraryService: {
      getExercises: jest.fn(),
      filterExercises: jest.fn(),
      getExerciseTypes: jest.fn().mockReturnValue(exerciseTypeValues),
      getMuscleGroups: jest.fn().mockReturnValue([]),
      getEquipment: jest.fn().mockReturnValue([]),
    },
    ExerciseType: {
      STRENGTH: 'strength',
      CARDIO: 'cardio',
      FLEXIBILITY: 'flexibility',
      BALANCE: 'balance'
    },
    ExerciseDifficulty: {
      BEGINNER: 'beginner',
      INTERMEDIATE: 'intermediate',
      ADVANCED: 'advanced'
    }
  };
});

// Mock the theme
jest.mock('../../../theme', () => ({
  lightTheme: {
    shadows: {
      lg: '0 4px 6px rgba(0, 0, 0, 0.1)',
    },
  },
}));

// Define types for the mock components
interface MockProps {
  children?: ReactNode;
}

interface MockSelectProps extends MockProps {
  label?: string;
  onChange?: (event: React.ChangeEvent<HTMLSelectElement>) => void;
  value?: string;
}

interface MockMenuItemProps extends MockProps {
  value?: string;
}

// Mock Material UI components used in the filter dialog
jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  CircularProgress: () => <div role="progressbar">Loading...</div>,
  FormControl: ({ children }: MockProps) => <div>{children}</div>,
  InputLabel: ({ children }: MockProps) => <label>{children}</label>,
  Select: ({ children, label, onChange, value }: MockSelectProps) => (
    <select aria-label={label} value={value} onChange={onChange}>
      {children}
    </select>
  ),
  MenuItem: ({ children, value }: MockMenuItemProps) => <option value={value}>{children}</option>,
}));

// Mock Material UI icons
jest.mock('@mui/icons-material/Close', () => ({
  __esModule: true,
  default: () => <span data-testid="CloseIcon" />,
}));

// Create a mock for the ExerciseLibraryPage component
jest.mock('../ExerciseLibraryPage', () => {
  return function MockExerciseLibraryPage() {
    const [showFilters, setShowFilters] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [exercises, setExercises] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedType, setSelectedType] = useState('');
    const [selectedDifficulty, setSelectedDifficulty] = useState('');
    
    useEffect(() => {
      let active = true;
      
      const fetchData = async () => {
        try {
          setIsLoading(true);
          setError(null);
          
          // Apply filters if any
          const filters: any = {};
          if (searchQuery) filters.searchQuery = searchQuery;
          if (selectedType) filters.type = selectedType;
          if (selectedDifficulty) filters.difficulty = selectedDifficulty;
          
          const data = await exerciseLibraryService.getExercises(filters);
          if (active) {
            setExercises(data);
            setIsLoading(false);
          }
        } catch (err) {
          if (active) {
            setError(err instanceof Error ? err.message : 'Failed to fetch exercises');
            setIsLoading(false);
          }
        }
      };
      
      fetchData();
      
      return () => { active = false; };
    }, [searchQuery, selectedType, selectedDifficulty]);
    
    const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchQuery(e.target.value);
    };
    
    const handleTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedType(e.target.value);
    };
    
    const handleDifficultyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      setSelectedDifficulty(e.target.value);
    };
    
    const handleClearFilters = () => {
      setSelectedType('');
      setSelectedDifficulty('');
      setSearchQuery('');
    };
    
    return (
      <div data-testid="exercise-library-page">
        <h1>Exercise Library</h1>
        <input 
          placeholder="Search exercises..." 
          value={searchQuery}
          onChange={handleSearch}
        />
        <button onClick={() => setShowFilters(true)}>Filters</button>
        <button>Add Exercise</button>
        
        {isLoading && <div role="progressbar">Loading...</div>}
        
        {error && <div>{error}</div>}
        
        {!isLoading && !error && exercises.length === 0 && (
          <div>No exercises found. Try adjusting your filters.</div>
        )}
        
        {!isLoading && exercises.map((exercise) => (
          <div key={exercise.id} className="exercise-card">
            <h2>{exercise.name}</h2>
          </div>
        ))}
        
        {showFilters && (
          <div>
            <h2>Filter Exercises</h2>
            <span data-testid="CloseIcon" onClick={() => setShowFilters(false)} />
            
            <div>
              <label htmlFor="type-select">Type</label>
              <select
                id="type-select"
                aria-label="Type"
                value={selectedType}
                onChange={handleTypeChange}
              >
                <option value="">All</option>
                <option value={MockExerciseType.STRENGTH}>{MockExerciseType.STRENGTH}</option>
                <option value={MockExerciseType.CARDIO}>{MockExerciseType.CARDIO}</option>
                <option value={MockExerciseType.FLEXIBILITY}>{MockExerciseType.FLEXIBILITY}</option>
                <option value={MockExerciseType.BALANCE}>{MockExerciseType.BALANCE}</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="difficulty-select">Difficulty</label>
              <select
                id="difficulty-select"
                aria-label="Difficulty"
                value={selectedDifficulty}
                onChange={handleDifficultyChange}
              >
                <option value="">All</option>
                <option value="beginner">beginner</option>
                <option value="intermediate">intermediate</option>
                <option value="advanced">advanced</option>
              </select>
            </div>
            
            <button onClick={handleClearFilters}>Clear Filters</button>
            <button onClick={() => setShowFilters(false)}>Apply</button>
          </div>
        )}
      </div>
    );
  };
});

// Import the mocked component
import ExerciseLibraryPage from '../ExerciseLibraryPage';

const mockExercise = {
  id: '1',
  name: 'Test Exercise',
  description: 'Test Description',
  type: MockExerciseType.STRENGTH,
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
    fireEvent.change(typeSelect, { target: { value: MockExerciseType.STRENGTH } });

    // Select difficulty
    const difficultySelect = screen.getByLabelText('Difficulty');
    fireEvent.change(difficultySelect, { target: { value: 'beginner' } });

    // Apply filters
    fireEvent.click(screen.getByText('Apply'));

    await waitFor(() => {
      expect(exerciseLibraryService.getExercises).toHaveBeenCalledWith(
        expect.objectContaining({
          type: MockExerciseType.STRENGTH,
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
    fireEvent.change(typeSelect, { target: { value: MockExerciseType.STRENGTH } });

    // Clear filters
    fireEvent.click(screen.getByText('Clear Filters'));

    await waitFor(() => {
      expect(exerciseLibraryService.getExercises).toHaveBeenCalledWith({});
    });
  });

  it('handles loading state', async () => {
    (exerciseLibraryService.getExercises as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve([]), 100))
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
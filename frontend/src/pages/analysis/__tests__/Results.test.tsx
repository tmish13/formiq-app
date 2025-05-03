import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Results } from '../Results';

// Mock useParams
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: jest.fn().mockReturnValue({ id: 'test-id-123' })
}));

// Mock components
jest.mock('../../../components/FormCheckFeedback', () => ({
  __esModule: true,
  default: ({ feedback, score }: { feedback: string; score: number }) => (
    <div data-testid="form-check-feedback">
      <div data-testid="feedback-text">{feedback}</div>
      <div data-testid="feedback-score">{score}</div>
    </div>
  )
}));

jest.mock('../../../components/common', () => ({
  VideoPlayer: ({ videoUrl }: { videoUrl: string }) => (
    <div data-testid="video-player">
      <div data-testid="video-url">{videoUrl}</div>
    </div>
  ),
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading...</div>
}));

describe('Results Component', () => {
  const mockFormCheck = {
    id: 'test-id-123',
    exercise_type: 'squat',
    score: 85,
    video_url: 'https://example.com/test-video.mp4',
    overall_feedback: 'Great form overall. Keep your back straighter.',
    issues: ['Back slightly rounded', 'Knees slightly over toes'],
    suggestions: ['Focus on maintaining a neutral spine', 'Keep knees aligned with toes']
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock fetch globally before each test
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockFormCheck)
      })
    );
  });

  afterEach(() => {
    // Clean up after each test
    jest.restoreAllMocks();
  });

  const renderResultsComponent = () => {
    return render(
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<Results />} />
        </Routes>
      </BrowserRouter>
    );
  };

  it('shows loading state initially', async () => {
    // Mock fetch to delay response
    global.fetch = jest.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({
        ok: true,
        json: () => Promise.resolve(mockFormCheck)
      }), 100))
    );

    renderResultsComponent();
    
    // Check loading state
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('displays error message when API request fails', async () => {
    // Mock fetch to return error
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: false,
        status: 500
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      const errorElement = screen.getByText(/An error occurred while fetching the form check/i);
      expect(errorElement).toBeInTheDocument();
    });
  });

  it('displays 404 error when form check not found', async () => {
    // Mock fetch to return 404
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: false,
        status: 404
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      const errorElement = screen.getByText(/Form check not found/i);
      expect(errorElement).toBeInTheDocument();
    });
  });

  it('displays form check results when API returns data', async () => {
    renderResultsComponent();

    await waitFor(() => {
      // Check title and content container
      expect(screen.getByTestId('results-container')).toBeInTheDocument();
      expect(screen.getByTestId('results-title')).toBeInTheDocument();
      expect(screen.getByTestId('results-content')).toBeInTheDocument();
      
      // Check exercise type and score
      expect(screen.getByTestId('exercise-type')).toHaveTextContent('Exercise Type: squat');
      expect(screen.getByTestId('score')).toHaveTextContent(`Score: ${mockFormCheck.score}%`);
      
      // Check video player
      expect(screen.getByTestId('video-player')).toBeInTheDocument();
      expect(screen.getByTestId('video-url')).toHaveTextContent('https://example.com/test-video.mp4');
      
      // Check feedback
      expect(screen.getByTestId('form-check-feedback')).toBeInTheDocument();
      expect(screen.getByTestId('feedback-text')).toHaveTextContent('Great form overall. Keep your back straighter.');
    });
  });

  it('applies green color class for high score', async () => {
    // Test with high score
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({...mockFormCheck, score: 85})
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      const scoreElement = screen.getByTestId('score');
      expect(scoreElement.className).toContain('text-green-500');
    });
  });

  it('applies yellow color class for medium score', async () => {
    // Test with medium score
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({...mockFormCheck, score: 65})
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      const scoreElement = screen.getByTestId('score');
      expect(scoreElement.className).toContain('text-yellow-500');
    });
  });

  it('applies red color class for low score', async () => {
    // Test with low score
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({...mockFormCheck, score: 40})
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      const scoreElement = screen.getByTestId('score');
      expect(scoreElement.className).toContain('text-red-500');
    });
  });

  it('handles missing video URL gracefully', async () => {
    // Mock form check without video_url
    const formCheckWithoutVideo = {...mockFormCheck, video_url: undefined};
    
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(formCheckWithoutVideo)
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      expect(screen.getByTestId('no-video-message')).toBeInTheDocument();
      expect(screen.getByText(/No video available for this form check/i)).toBeInTheDocument();
    });
  });

  it('handles form check with empty feedback gracefully', async () => {
    // Mock form check with empty feedback
    const formCheckWithEmptyFeedback = {...mockFormCheck, overall_feedback: undefined};
    
    global.fetch = jest.fn().mockImplementation(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(formCheckWithEmptyFeedback)
      })
    );

    renderResultsComponent();

    await waitFor(() => {
      expect(screen.getByTestId('feedback-text')).toHaveTextContent('');
    });
  });

  it('fetches form check with correct ID from URL param', async () => {
    renderResultsComponent();

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/form-checks/test-id-123');
    });
  });
}); 
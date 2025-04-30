import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useParams } from 'react-router-dom';
import { Results } from '../../pages/analysis/Results';
import '@testing-library/jest-dom';

// Mock react-router-dom's useParams
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: jest.fn(),
}));

// Mock the VideoPlayer and LoadingSpinner component
jest.mock('../../components/common', () => ({
  VideoPlayer: ({ videoUrl, ...props }: { videoUrl: string }) => <div data-testid="video-player" {...props}>Mock Video Player {videoUrl}</div>,
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading...</div>
}));

// Mock FormCheckFeedback component
jest.mock('../../components/FormCheckFeedback', () => {
  return {
    __esModule: true,
    default: (props: { score: number; feedback: string; 'data-testid'?: string }) => (
      <div data-testid={props['data-testid'] || "form-check-feedback"}>
        <div>Form Check Score: {props.score}%</div>
        <div>{props.feedback}</div>
      </div>
    )
  };
});

// Mock data
const mockFormCheck = {
  id: '123',
  exercise_type: 'squat',
  score: 85,
  video_url: 'http://example.com/video.mp4',
  overall_feedback: 'Good form overall',
  issues: ['Knees caving in'],
  suggestions: ['Keep chest up']
};

// Helper function to render the component
const renderResults = (id: string = '123') => {
  (useParams as jest.Mock).mockReturnValue({ id });
  return render(<Results />);
};

describe('Results Component', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = jest.fn();
    (useParams as jest.Mock).mockClear();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('shows loading spinner initially', async () => {
    // Create a promise that never resolves to keep the loading state
    const neverResolve = new Promise<Response>(() => {});
    jest.spyOn(global, 'fetch').mockImplementationOnce(() => neverResolve);
    
    renderResults();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows error when API call fails', async () => {
    // Mock a rejected fetch
    jest.spyOn(global, 'fetch').mockImplementationOnce(() => {
      throw new Error('Network error');
    });
    
    renderResults();
    
    // Allow time for the component to update
    await waitFor(() => {
      const errorElement = screen.queryByText(/error occurred/i);
      expect(errorElement).toBeInTheDocument();
    });
  });

  it('displays error when no ID is provided', async () => {
    renderResults('');
    
    await waitFor(() => {
      const errorElement = screen.queryByText(/no form check id provided/i);
      expect(errorElement).toBeInTheDocument();
    });
  });

  it('displays form check data correctly', async () => {
    jest.spyOn(global, 'fetch').mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockFormCheck)
      } as Response)
    );

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('results-title')).toHaveTextContent('Form Analysis Results');
      expect(screen.getByTestId('exercise-type')).toHaveTextContent(`Exercise Type: ${mockFormCheck.exercise_type}`);
      
      // Check for the score value
      const scoreElement = screen.getByTestId('score');
      expect(scoreElement.textContent).toContain('85');
      expect(scoreElement.textContent).toContain('%');
    });
  });

  it('displays not found message when form check is not found', async () => {
    jest.spyOn(global, 'fetch').mockImplementationOnce(() => 
      Promise.resolve({
        ok: false,
        status: 404
      } as Response)
    );

    renderResults();
    
    await waitFor(() => {
      const notFoundElement = screen.queryByText(/form check not found/i);
      expect(notFoundElement).toBeInTheDocument();
    });
  });

  it('handles missing video URL', async () => {
    const formCheckWithoutVideo = { ...mockFormCheck, video_url: undefined };
    jest.spyOn(global, 'fetch').mockImplementationOnce(() => 
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(formCheckWithoutVideo)
      } as Response)
    );

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('no-video-message')).toBeInTheDocument();
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });
  });
}); 
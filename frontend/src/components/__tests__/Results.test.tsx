import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useParams } from 'react-router-dom';
import { Results } from '../../pages/analysis/Results';
import { VideoPlayer } from '../../components/common';
import { LoadingSpinner } from '../../components/common';
import '@testing-library/jest-dom';

// Mock react-router-dom's useParams
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: jest.fn(),
}));

// Mock the VideoPlayer component
jest.mock('../../components/common', () => ({
  VideoPlayer: () => <div data-testid="video-player">Mock Video Player</div>,
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading...</div>
}));

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock data
const mockFormCheck = {
  id: '123',
  exercise_type: 'benchPress',
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
  beforeEach(() => {
    mockFetch.mockClear();
    (useParams as jest.Mock).mockClear();
  });

  it('shows loading spinner initially', async () => {
    // Create a promise that never resolves to keep the loading state
    const neverResolve = new Promise(() => {});
    mockFetch.mockImplementationOnce(() => neverResolve);
    
    renderResults();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows error when API call fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'));
    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('An error occurred while fetching the form check');
    });
  });

  it('displays error when no ID is provided', async () => {
    renderResults('');
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('No form check ID provided');
    });
  });

  it('displays form check data correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockFormCheck)
    });

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('results-title')).toHaveTextContent('Form Analysis Results');
      expect(screen.getByTestId('exercise-type')).toHaveTextContent(`Exercise Type: ${mockFormCheck.exercise_type}`);
      expect(screen.getByTestId('score')).toHaveTextContent(`Score: ${mockFormCheck.score}%`);
      expect(screen.getByTestId('video-player')).toBeInTheDocument();
    });
  });

  it('displays not found message when form check is not found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404
    });

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toHaveTextContent('Form check not found');
    });
  });

  it('handles missing video URL', async () => {
    const formCheckWithoutVideo = { ...mockFormCheck, video_url: undefined };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(formCheckWithoutVideo)
    });

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByTestId('no-video-message')).toHaveTextContent('No video available for this form check');
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });
  });
}); 
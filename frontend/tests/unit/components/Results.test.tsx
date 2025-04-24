import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Results } from '../../../src/pages/analysis/Results';
import { VideoPlayer, LoadingSpinner } from '../../../src/components/common';

// Mock the VideoPlayer component
jest.mock('../../../src/components/common/VideoPlayer', () => ({
  VideoPlayer: ({ videoUrl }: { videoUrl: string }) => (
    <div data-testid="video-player">Mock Video Player: {videoUrl}</div>
  )
}));

// Mock the LoadingSpinner component
jest.mock('../../../src/components/common/LoadingSpinner', () => ({
  LoadingSpinner: () => <div data-testid="loading-spinner">Loading...</div>
}));

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock data that matches the FormCheck interface
const mockFormCheck = {
  id: '123',
  exercise_type: 'squat',
  score: 85,
  video_url: 'http://example.com/video.mp4',
  overall_feedback: 'Good form overall',
  issues: ['Knees caving in'],
  suggestions: ['Keep chest up']
};

// Helper function to render the component with the correct route
const renderResults = (id: string = '123') => {
  return render(
    <MemoryRouter initialEntries={[`/results/${id}`]}>
      <Routes>
        <Route path="/results/:id" element={<Results />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('Results Component', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('displays loading state initially', async () => {
    renderResults();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('displays error message when API call fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'));
    renderResults();
    
    await waitFor(() => {
      expect(screen.getByText('An error occurred while fetching the form check')).toBeInTheDocument();
    });
  });

  it('displays error when no ID is provided', async () => {
    renderResults('');
    
    await waitFor(() => {
      expect(screen.getByText('No form check ID provided')).toBeInTheDocument();
    });
  });

  it('displays form check data correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockFormCheck)
    });

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByText('Form Analysis Results')).toBeInTheDocument();
      expect(screen.getByText('Exercise Type: squat')).toBeInTheDocument();
      expect(screen.getByText('Score: 85%')).toBeInTheDocument();
      expect(screen.getByTestId('video-player')).toBeInTheDocument();
      expect(screen.getByText('Good form overall')).toBeInTheDocument();
      expect(screen.getByText('Knees caving in')).toBeInTheDocument();
    });
  });

  it('displays not found message when form check is not found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404
    });

    renderResults();
    
    await waitFor(() => {
      expect(screen.getByText('Form check not found')).toBeInTheDocument();
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
      expect(screen.getByText('No video available for this form check')).toBeInTheDocument();
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
    });
  });
}); 
import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import Results from '../../../src/pages/analysis/Results';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { renderWithProviders } from '../../utils/test-utils';

// Mock data
const mockFormCheck = {
  id: '1',
  exercise_type: 'squat',
  score: 95,
  created_at: '2024-01-15T10:00:00Z',
  video_url: 'https://example.com/videos/squat1.mp4',
  feedback: {
    overall: 'Great form overall',
    issues: ['Slight knee valgus at bottom position'],
    suggestions: ['Focus on pushing knees outward during descent']
  }
};

// Setup MSW server
const server = setupServer(
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    if (id === '1') {
      return res(ctx.json(mockFormCheck));
    } else if (id === '999') {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found' }));
    } else {
      return res(ctx.status(500), ctx.json({ message: 'Server error' }));
    }
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

const renderResults = (route: string) => {
  return renderWithProviders(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/results/:id" element={<Results />} />
        <Route path="*" element={<div>Not Found</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('Results', () => {
  it('displays loading state initially', () => {
    renderResults('/results/1');
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('displays error message when API call fails', async () => {
    server.use(
      rest.get('/api/form-checks/:id', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ message: 'Error loading form check' }));
      })
    );
    
    renderResults('/results/1');

    await waitFor(() => {
      expect(screen.getByText(/error loading form check/i)).toBeInTheDocument();
    });
  });

  it('displays form check data correctly', async () => {
    renderResults('/results/1');

    await waitFor(() => {
      expect(screen.getByText('squat')).toBeInTheDocument();
      expect(screen.getByText('Great form overall')).toBeInTheDocument();
      expect(screen.getByText('Slight knee valgus at bottom position')).toBeInTheDocument();
      expect(screen.getByText('Focus on pushing knees outward during descent')).toBeInTheDocument();
    });
  });

  it('displays video player when video URL is available', async () => {
    renderResults('/results/1');

    await waitFor(() => {
      const videoElement = screen.getByTestId('video-player');
      expect(videoElement).toBeInTheDocument();
      expect(videoElement).toHaveAttribute('src', mockFormCheck.video_url);
    });
  });

  it('displays error message when form check is not found', async () => {
    renderResults('/results/999');

    await waitFor(() => {
      expect(screen.getByText(/form check not found/i)).toBeInTheDocument();
    });
  });

  it('displays score with appropriate color coding', async () => {
    renderResults('/results/1');

    await waitFor(() => {
      const scoreChip = screen.getByTestId('score-chip');
      expect(scoreChip).toBeInTheDocument();
      expect(scoreChip).toHaveTextContent('95');
      expect(scoreChip).toHaveClass('good-score');
    });
  });

  it('handles missing video URL gracefully', async () => {
    server.use(
      rest.get('/api/form-checks/:id', (req, res, ctx) => {
        return res(ctx.json({ ...mockFormCheck, video_url: null }));
      })
    );

    renderResults('/results/1');

    await waitFor(() => {
      expect(screen.queryByTestId('video-player')).not.toBeInTheDocument();
      expect(screen.getByText(/video not available/i)).toBeInTheDocument();
    });
  });
}); 
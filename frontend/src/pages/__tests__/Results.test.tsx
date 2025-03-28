import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import Results from '../Results';
import type { FormCheck } from '../../types';

const mockFormCheck: FormCheck = {
  id: 1,
  user_id: 1,
  exercise_type: 'squat',
  video_url: 'https://example.com/video1.mp4',
  score: 85,
  overall_feedback: 'Good form overall',
  issues: ['Slight knee valgus', 'Heels lifting'],
  created_at: '2024-01-01T12:00:00Z',
};

const server = setupServer(
  http.get('/api/form-checks/:id', () => {
    return HttpResponse.json(mockFormCheck);
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Results', () => {
  it('displays loading state initially', () => {
    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error message when API call fails', async () => {
    server.use(
      http.get('/api/form-checks/:id', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error loading form check/i)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();
  });

  it('displays form check data correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('squat')).toBeInTheDocument();
    });

    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('Good form overall')).toBeInTheDocument();
    expect(screen.getByText('Slight knee valgus')).toBeInTheDocument();
    expect(screen.getByText('Heels lifting')).toBeInTheDocument();
  });

  it('displays video player when video URL is available', async () => {
    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const videoElement = screen.getByTestId('video-player');
      expect(videoElement).toBeInTheDocument();
      expect(videoElement).toHaveAttribute('src', mockFormCheck.video_url);
    });
  });

  it('displays error message when form check is not found', async () => {
    server.use(
      http.get('/api/form-checks/:id', () => {
        return new HttpResponse(null, { status: 404 });
      })
    );

    render(
      <MemoryRouter initialEntries={['/results/999']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/form check not found/i)).toBeInTheDocument();
    });

    const backButton = screen.getByRole('button', { name: /back to history/i });
    expect(backButton).toBeInTheDocument();
  });

  it('displays score with appropriate color coding', async () => {
    const highScoreFormCheck = {
      ...mockFormCheck,
      score: 95,
    };

    server.use(
      http.get('/api/form-checks/:id', () => {
        return HttpResponse.json(highScoreFormCheck);
      })
    );

    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const scoreChip = screen.getByText('95');
      expect(scoreChip).toBeInTheDocument();
      expect(scoreChip.closest('[class*="MuiChip-root"]')).toHaveStyle({
        backgroundColor: expect.stringMatching(/green/i),
      });
    });
  });

  it('displays formatted date', async () => {
    render(
      <MemoryRouter initialEntries={['/results/1']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      const dateText = screen.getByText(/january 1, 2024/i);
      expect(dateText).toBeInTheDocument();
    });
  });
}); 
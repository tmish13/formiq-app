import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import History from '../History';
import type { FormCheck } from '../../types';

const mockFormChecks: FormCheck[] = [
  {
    id: 1,
    user_id: 1,
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    score: 85,
    overall_feedback: 'Good form overall',
    issues: ['Slight knee valgus'],
    created_at: '2024-01-01T12:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    exercise_type: 'deadlift',
    video_url: 'https://example.com/video2.mp4',
    score: 92,
    overall_feedback: 'Excellent form',
    issues: [],
    created_at: '2024-01-02T12:00:00Z',
  },
];

const server = setupServer(
  http.get('/api/form-checks', () => {
    return HttpResponse.json(mockFormChecks);
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('History', () => {
  it('displays loading state initially', () => {
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error message when API call fails', async () => {
    server.use(
      http.get('/api/form-checks', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/error loading form checks/i)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();
  });

  it('displays empty state when no form checks exist', async () => {
    server.use(
      http.get('/api/form-checks', () => {
        return HttpResponse.json([]);
      })
    );

    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/no form checks available/i)).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole('button', { name: /upload a video/i });
    expect(uploadButton).toBeInTheDocument();
  });

  it('displays form checks data correctly', async () => {
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('squat')).toBeInTheDocument();
      expect(screen.getByText('deadlift')).toBeInTheDocument();
    });

    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('92')).toBeInTheDocument();
    expect(screen.getByText('Good form overall')).toBeInTheDocument();
    expect(screen.getByText('Excellent form')).toBeInTheDocument();
  });

  it('handles pagination correctly', async () => {
    const manyFormChecks: FormCheck[] = Array.from({ length: 15 }, (_, i) => ({
      id: i + 1,
      user_id: 1,
      exercise_type: 'squat',
      video_url: `https://example.com/video${i + 1}.mp4`,
      score: 85,
      overall_feedback: `Feedback ${i + 1}`,
      issues: [],
      created_at: new Date().toISOString(),
    }));

    server.use(
      http.get('/api/form-checks', () => {
        return HttpResponse.json(manyFormChecks);
      })
    );

    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Feedback 1')).toBeInTheDocument();
    });

    const nextPageButton = screen.getByRole('button', { name: /next page/i });
    fireEvent.click(nextPageButton);

    await waitFor(() => {
      expect(screen.getByText('Feedback 11')).toBeInTheDocument();
    });
  });

  it('allows sorting by date and score', async () => {
    render(
      <MemoryRouter>
        <History />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('squat')).toBeInTheDocument();
    });

    const dateHeader = screen.getByRole('columnheader', { name: /date/i });
    fireEvent.click(dateHeader);

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      expect(rows[1]).toHaveTextContent('deadlift');
    });

    const scoreHeader = screen.getByRole('columnheader', { name: /score/i });
    fireEvent.click(scoreHeader);

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      expect(rows[1]).toHaveTextContent('squat');
    });
  });
}); 
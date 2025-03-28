import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import Upload from '../Upload';
import type { FormCheck } from '../../types';

const mockFormCheck: FormCheck = {
  id: 1,
  user_id: 1,
  exercise_type: 'squat',
  video_url: 'https://example.com/video1.mp4',
  score: 85,
  overall_feedback: 'Good form overall',
  issues: ['Slight knee valgus'],
  created_at: new Date().toISOString(),
};

const server = setupServer(
  http.post('/api/form-checks', () => {
    return HttpResponse.json(mockFormCheck);
  }),
  http.post('/api/upload', () => {
    return HttpResponse.json({ url: 'https://example.com/video1.mp4' });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Upload', () => {
  it('displays initial upload form', () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    expect(screen.getByText(/upload your video/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/exercise type/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /select video/i })).toBeInTheDocument();
  });

  it('handles file selection', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);

    expect(screen.getByText(/test.mp4/i)).toBeInTheDocument();
  });

  it('displays error for invalid file type', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test image'], 'test.jpg', { type: 'image/jpeg' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);

    expect(screen.getByText(/please select a valid video file/i)).toBeInTheDocument();
  });

  it('handles upload error', async () => {
    server.use(
      http.post('/api/upload', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);
    fireEvent.change(screen.getByLabelText(/exercise type/i), { target: { value: 'squat' } });
    
    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/error uploading video/i)).toBeInTheDocument();
    });
  });

  it('handles form check creation error', async () => {
    server.use(
      http.post('/api/form-checks', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);
    fireEvent.change(screen.getByLabelText(/exercise type/i), { target: { value: 'squat' } });
    
    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/error creating form check/i)).toBeInTheDocument();
    });
  });

  it('displays upload progress', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);
    fireEvent.change(screen.getByLabelText(/exercise type/i), { target: { value: 'squat' } });
    
    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText(/uploading video/i)).toBeInTheDocument();
    });
  });

  it('redirects to results page on successful upload', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);
    fireEvent.change(screen.getByLabelText(/exercise type/i), { target: { value: 'squat' } });
    
    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(window.location.pathname).toBe(`/results/${mockFormCheck.id}`);
    });
  });

  it('validates required fields before submission', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    );

    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    expect(screen.getByText(/please select a video/i)).toBeInTheDocument();
    expect(screen.getByText(/please select an exercise type/i)).toBeInTheDocument();
  });
}); 
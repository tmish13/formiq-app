import React from 'react';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { rest } from 'msw';
import { server } from '../../mocks/server';
import { renderWithProviders } from '../../test-utils';
import Upload from '../../pages/analysis/Upload';

// Mock styled function from @mui/system before importing Upload
jest.mock('@mui/system', () => {
  const originalModule = jest.requireActual('@mui/system');
  return {
    ...originalModule,
    styled: () => (Component: React.ComponentType<any>) => (props: any) => <Component {...props} />
  };
});

// Mock form check type with necessary fields
interface FormCheck {
  id: number;
  user_id: number;
  exercise_type: string;
  video_url: string;
  score: number;
  overall_feedback: string;
  issues: string[];
  created_at: string;
  status: string;
  updated_at: string;
}

const mockFormCheck: FormCheck = {
  id: 1,
  user_id: 1,
  exercise_type: 'squat',
  video_url: 'https://example.com/video1.mp4',
  score: 85,
  overall_feedback: 'Good form overall',
  issues: ['Slight knee valgus'],
  created_at: new Date().toISOString(),
  status: 'completed',
  updated_at: new Date().toISOString(),
};

// Add specific handlers for this test file
beforeEach(() => {
  server.use(
    rest.post('/api/form-checks', (req, res, ctx) => {
      return res(ctx.json(mockFormCheck));
    }),
    rest.post('/api/upload', (req, res, ctx) => {
      return res(ctx.json({ url: 'https://example.com/video1.mp4' }));
    })
  );
});

describe('Upload', () => {
  it('displays initial upload form', () => {
    renderWithProviders(<Upload />);

    expect(screen.getByText(/upload your video/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/exercise type/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /select video/i })).toBeInTheDocument();
  });

  it('handles file selection', async () => {
    renderWithProviders(<Upload />);

    const file = new File(['test video'], 'test.mp4', { type: 'video/mp4' });
    const input = screen.getByTestId('video-input');
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });

    fireEvent.change(input);

    expect(screen.getByText(/test.mp4/i)).toBeInTheDocument();
  });

  it('displays error for invalid file type', async () => {
    renderWithProviders(<Upload />);

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
      rest.post('/api/upload', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    renderWithProviders(<Upload />);

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
      rest.post('/api/form-checks', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    renderWithProviders(<Upload />);

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
    renderWithProviders(<Upload />);

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
    renderWithProviders(<Upload />);

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
    renderWithProviders(<Upload />);

    const submitButton = screen.getByRole('button', { name: /upload/i });
    fireEvent.click(submitButton);

    expect(screen.getByText(/please select a video/i)).toBeInTheDocument();
    expect(screen.getByText(/please select an exercise type/i)).toBeInTheDocument();
  });
}); 
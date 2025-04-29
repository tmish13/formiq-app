import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Upload } from '../camera/Upload';
import { Results } from '../form/Results';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Mock the CameraService
jest.mock('../../services/CameraService', () => ({
  startRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' }),
  stopRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' })
}));

// Create test server
const server = setupServer(
  // Mock upload endpoint
  rest.post('/api/form-analysis/upload', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'test-analysis-id',
        status: 'processing'
      })
    );
  }),
  
  // Mock analysis results endpoint
  rest.get('/api/form-analysis/:id', (req, res, ctx) => {
    return res(ctx.json(generateTestFormAnalysis()));
  })
);

describe('Upload and Results Integration', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('should navigate from upload to results page after successful upload', async () => {
    render(
      <MemoryRouter initialEntries={['/upload']}>
        <Routes>
          <Route path="/upload" element={<Upload />} />
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    // Start recording
    const startButton = screen.getByText('Start Recording');
    fireEvent.click(startButton);

    // Wait for recording to start
    await waitFor(() => {
      expect(screen.getByText('Stop Recording')).toBeInTheDocument();
    });

    // Stop recording
    const stopButton = screen.getByText('Stop Recording');
    fireEvent.click(stopButton);

    // Wait for navigation to results page
    await waitFor(() => {
      expect(screen.getByText('Form Analysis Results')).toBeInTheDocument();
    });

    // Verify results are displayed
    expect(screen.getByText(/Confidence Score:/)).toBeInTheDocument();
    expect(screen.getByTestId('form-feedback')).toBeInTheDocument();
  });

  it('should handle upload errors gracefully', async () => {
    // Override the upload endpoint to simulate an error
    server.use(
      rest.post('/api/form-analysis/upload', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(
      <MemoryRouter initialEntries={['/upload']}>
        <Routes>
          <Route path="/upload" element={<Upload />} />
        </Routes>
      </MemoryRouter>
    );

    // Start recording
    const startButton = screen.getByText('Start Recording');
    fireEvent.click(startButton);

    // Wait for recording to start
    await waitFor(() => {
      expect(screen.getByText('Stop Recording')).toBeInTheDocument();
    });

    // Stop recording
    const stopButton = screen.getByText('Stop Recording');
    fireEvent.click(stopButton);

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/Failed to upload video/i)).toBeInTheDocument();
    });
  });

  it('should handle analysis errors gracefully', async () => {
    // Override the analysis endpoint to simulate an error
    server.use(
      rest.get('/api/form-analysis/:id', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    render(
      <MemoryRouter initialEntries={['/results/test-analysis-id']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/Failed to load analysis results/i)).toBeInTheDocument();
    });
  });
}); 
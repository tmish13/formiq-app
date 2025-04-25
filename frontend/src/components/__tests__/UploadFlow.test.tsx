import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { testRender } from '../../test-utils';
import { Upload } from '../Upload';
import { FormFeedback } from '../FormFeedback';
import { Results } from '../Results';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Mock the video recording API
jest.mock('../../services/CameraService', () => ({
  startRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' }),
  stopRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' })
}));

// Create test server
const server = setupServer(
  http.post('/api/form-analysis/upload', () => {
    return HttpResponse.json({
      id: 'analysis-123',
      status: 'processing',
      message: 'Your video is being processed'
    });
  }),
  http.get('/api/form-analysis/status/:id', () => {
    return HttpResponse.json({
      id: 'analysis-123',
      status: 'completed',
      progress: 100
    });
  }),
  http.get('/api/form-analysis/:id', () => {
    return HttpResponse.json(generateTestFormAnalysis());
  })
);

describe('Upload Flow Integration', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  it('completes the full upload and analysis flow', async () => {
    const { getByTestId, findByText } = testRender(
      <MemoryRouter initialEntries={['/upload']}>
        <Routes>
          <Route path="/upload" element={<Upload />} />
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    // Start recording
    const startButton = getByTestId('start-recording');
    startButton.click();

    // Wait for recording to start
    await findByText(/Recording started/i);

    // Stop recording
    const stopButton = getByTestId('stop-recording');
    stopButton.click();

    // Wait for upload to complete
    await findByText(/Processing your video/i);

    // Wait for analysis to complete
    await findByText(/Analysis complete/i);

    // Verify we're on the results page
    expect(window.location.pathname).toBe('/results/analysis-123');

    // Verify results are displayed
    const results = await findByText(/Form Analysis Results/i);
    expect(results).toBeInTheDocument();
  });

  it('handles upload errors gracefully', async () => {
    // Override the upload endpoint to simulate an error
    server.use(
      http.post('/api/form-analysis/upload', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    const { getByTestId, findByText } = testRender(
      <MemoryRouter initialEntries={['/upload']}>
        <Routes>
          <Route path="/upload" element={<Upload />} />
        </Routes>
      </MemoryRouter>
    );

    // Start and stop recording
    getByTestId('start-recording').click();
    await findByText(/Recording started/i);
    getByTestId('stop-recording').click();

    // Verify error message is displayed
    const errorMessage = await findByText(/Failed to upload video/i);
    expect(errorMessage).toBeInTheDocument();
  });

  it('handles analysis errors gracefully', async () => {
    // Override the analysis endpoint to simulate an error
    server.use(
      http.get('/api/form-analysis/:id', () => {
        return new HttpResponse(null, { status: 500 });
      })
    );

    const { getByTestId, findByText } = testRender(
      <MemoryRouter initialEntries={['/results/analysis-123']}>
        <Routes>
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    // Verify error message is displayed
    const errorMessage = await findByText(/Failed to load analysis results/i);
    expect(errorMessage).toBeInTheDocument();
  });
}); 
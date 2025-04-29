import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { testRender } from '../../test-utils';
import Upload from '../../pages/analysis/Upload';
import { FormFeedback } from '../FormFeedback';
import { Results } from '../../pages/analysis/Results';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Mock the video recording API
jest.mock('../../services/CameraService', () => ({
  startRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' }),
  stopRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' })
}));

// Create test server
const server = setupServer(
  rest.post('/api/form-analysis/upload', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'analysis-123',
        status: 'processing',
        message: 'Your video is being processed'
      })
    );
  }),
  rest.get('/api/form-analysis/status/:id', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'analysis-123',
        status: 'completed',
        progress: 100
      })
    );
  }),
  rest.get('/api/form-analysis/:id', (req, res, ctx) => {
    return res(ctx.json(generateTestFormAnalysis()));
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
      rest.post('/api/form-analysis/upload', (req, res, ctx) => {
        return res(ctx.status(500));
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
      rest.get('/api/form-analysis/:id', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    const { getByTestId, findByText } = testRender(
      <MemoryRouter initialEntries={['/upload']}>
        <Routes>
          <Route path="/upload" element={<Upload />} />
          <Route path="/results/:id" element={<Results />} />
        </Routes>
      </MemoryRouter>
    );

    // Start and stop recording
    getByTestId('start-recording').click();
    await findByText(/Recording started/i);
    getByTestId('stop-recording').click();

    // Wait for upload to complete
    await findByText(/Processing your video/i);

    // Verify error message is displayed
    const errorMessage = await findByText(/Failed to analyze video/i);
    expect(errorMessage).toBeInTheDocument();
  });
}); 
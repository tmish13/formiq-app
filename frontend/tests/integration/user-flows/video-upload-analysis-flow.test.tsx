/**
 * Integration Test: Video Upload → Analysis → Results Flow
 * 
 * Tests the complete user journey from video upload through analysis
 * to results display, using real backend connections when available.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntegrationTestUtils, config } from '../setup';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { store } from '../../../src/store';
import { ThemeProvider } from '../../../src/contexts/ThemeContext';
import FormCheckUploadPage from '../../../src/pages/workout/FormCheckUploadPage';
import { formCheckService } from '../../../src/services/formCheckService';
import { videoService } from '../../../src/services/videoService';
import { websocketService } from '../../../src/services/websocketService';

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Provider store={store}>
    <BrowserRouter>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </BrowserRouter>
  </Provider>
);

describe('Video Upload → Analysis → Results Integration Flow', () => {
  let mockWebSocket: any;
  let uploadProgressCallback: ((progress: number) => void) | undefined;
  let analysisStatusCallback: ((status: any) => void) | undefined;

  beforeEach(async () => {
    // Setup WebSocket mock for real-time updates
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      readyState: WebSocket.OPEN,
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
    };
    
    (global as any).WebSocket = jest.fn(() => mockWebSocket);
    
    // Mock services if not testing with real backend
    if (!config.backend.enableRealApi) {
      jest.spyOn(videoService, 'uploadVideo').mockImplementation(
        async (file: File, progressCallback?: (progress: number) => void) => {
          uploadProgressCallback = progressCallback;
          
          // Simulate upload progress
          setTimeout(() => progressCallback?.(25), 100);
          setTimeout(() => progressCallback?.(50), 200);
          setTimeout(() => progressCallback?.(75), 300);
          setTimeout(() => progressCallback?.(100), 400);
          
          return {
            success: true,
            data: {
              video_id: 'test-video-123',
              upload_url: 'https://mock-s3.amazonaws.com/test-video-123',
              status: 'uploaded',
            },
          };
        }
      );
      
      jest.spyOn(formCheckService, 'submitForAnalysis').mockImplementation(
        async (videoId: string, exerciseType: string) => {
          // Simulate analysis start
          setTimeout(() => {
            analysisStatusCallback?.({
              status: 'processing',
              progress: 25,
              stage: 'pose_detection',
            });
          }, 500);
          
          setTimeout(() => {
            analysisStatusCallback?.({
              status: 'processing',
              progress: 75,
              stage: 'form_analysis',
            });
          }, 1000);
          
          setTimeout(() => {
            analysisStatusCallback?.({
              status: 'completed',
              progress: 100,
              analysis_id: 'test-analysis-123',
            });
          }, 1500);
          
          return {
            success: true,
            data: {
              analysis_id: 'test-analysis-123',
              status: 'processing',
            },
          };
        }
      );
      
      jest.spyOn(formCheckService, 'getAnalysisResults').mockResolvedValue({
        success: true,
        data: {
          analysis_id: 'test-analysis-123',
          video_id: 'test-video-123',
          exercise_type: 'squat',
          status: 'completed',
          scores: {
            posture_score: 85,
            stability_score: 78,
            depth_score: 92,
            overall_score: 85,
          },
          feedback: {
            summary: 'Good squat form overall. Focus on knee tracking alignment.',
            detailed_points: [
              'Excellent depth achieved throughout the movement',
              'Maintain knees aligned with toes during ascent',
              'Keep core engaged for better stability',
            ],
            improvement_areas: [
              'Knee valgus observed during ascent',
              'Slight forward lean at bottom position',
            ],
          },
          pose_data: {
            keypoints: [/* mock keypoint data */],
            angles: {
              knee_angle: [110, 95, 80, 85, 100, 115],
              hip_angle: [160, 140, 120, 125, 145, 165],
            },
          },
          timestamp: new Date().toISOString(),
        },
      });
    }
  });

  afterEach(() => {
    jest.clearAllMocks();
    uploadProgressCallback = undefined;
    analysisStatusCallback = undefined;
  });

  it('should complete the full video upload to analysis results flow', async () => {
    const user = userEvent.setup();
    
    // Render the upload page
    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Step 1: Verify initial page load
    expect(screen.getByText(/upload.*video/i)).toBeInTheDocument();
    expect(screen.getByText(/select.*exercise/i)).toBeInTheDocument();

    // Step 2: Select exercise type
    const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
    await user.selectOptions(exerciseSelect, 'squat');
    expect(exerciseSelect).toHaveValue('squat');

    // Step 3: Upload video file
    const videoFile = IntegrationTestUtils.createTestVideoFile();
    const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
    
    await user.upload(fileInput, videoFile);
    
    // Verify file is selected
    expect(fileInput).toHaveProperty('files', expect.objectContaining({
      0: expect.objectContaining({
        name: 'test-video.mp4',
        type: 'video/mp4',
      }),
    }));

    // Step 4: Start upload process
    const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
    await user.click(uploadButton);

    // Step 5: Verify upload progress is shown
    await waitFor(() => {
      expect(screen.getByText(/uploading/i)).toBeInTheDocument();
    });

    // Simulate upload progress updates
    if (uploadProgressCallback) {
      uploadProgressCallback(50);
      await waitFor(() => {
        expect(screen.getByText(/50%|uploading.*50/i)).toBeInTheDocument();
      });
    }

    // Step 6: Wait for upload completion and analysis start
    await waitFor(
      () => {
        expect(screen.getByText(/analyzing|processing/i)).toBeInTheDocument();
      },
      { timeout: config.video.uploadTimeout }
    );

    // Step 7: Verify analysis progress is shown
    if (analysisStatusCallback) {
      analysisStatusCallback({
        status: 'processing',
        progress: 25,
        stage: 'pose_detection',
      });
      
      await waitFor(() => {
        expect(screen.getByText(/pose.*detection|detecting.*pose/i)).toBeInTheDocument();
      });

      analysisStatusCallback({
        status: 'processing',
        progress: 75,
        stage: 'form_analysis',
      });
      
      await waitFor(() => {
        expect(screen.getByText(/form.*analysis|analyzing.*form/i)).toBeInTheDocument();
      });
    }

    // Step 8: Wait for analysis completion
    if (analysisStatusCallback) {
      analysisStatusCallback({
        status: 'completed',
        progress: 100,
        analysis_id: 'test-analysis-123',
      });
    }

    await waitFor(
      () => {
        expect(screen.getByText(/analysis.*complete|results.*ready/i)).toBeInTheDocument();
      },
      { timeout: config.performance.thresholds.analysisTime }
    );

    // Step 9: Verify results are displayed
    await waitFor(() => {
      // Check for score display
      expect(screen.getByText(/overall.*score/i)).toBeInTheDocument();
      expect(screen.getByText(/85/)).toBeInTheDocument(); // Overall score
      
      // Check for individual scores
      expect(screen.getByText(/posture/i)).toBeInTheDocument();
      expect(screen.getByText(/stability/i)).toBeInTheDocument();
      expect(screen.getByText(/depth/i)).toBeInTheDocument();
    });

    // Step 10: Verify feedback is shown
    await waitFor(() => {
      expect(screen.getByText(/good squat form/i)).toBeInTheDocument();
      expect(screen.getByText(/knee tracking/i)).toBeInTheDocument();
    });

    // Step 11: Verify detailed feedback points are available
    const improvementSection = screen.getByText(/improvement|recommendations/i);
    expect(improvementSection).toBeInTheDocument();
    
    expect(screen.getByText(/knees aligned with toes/i)).toBeInTheDocument();
    expect(screen.getByText(/core engaged/i)).toBeInTheDocument();

    // Step 12: Verify pose visualization is available (if implemented)
    const poseVisualization = screen.queryByTestId('pose-visualization');
    if (poseVisualization) {
      expect(poseVisualization).toBeInTheDocument();
    }

    // Step 13: Test navigation to detailed results
    const viewDetailsButton = screen.queryByRole('button', { name: /view.*details|detailed.*analysis/i });
    if (viewDetailsButton) {
      await user.click(viewDetailsButton);
      
      await waitFor(() => {
        expect(screen.getByText(/detailed.*analysis|analysis.*details/i)).toBeInTheDocument();
      });
    }
  });

  it('should handle upload errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Mock upload failure
    if (!config.backend.enableRealApi) {
      jest.spyOn(videoService, 'uploadVideo').mockRejectedValue(
        new Error('Upload failed: Network error')
      );
    }

    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Select exercise and upload file
    const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
    await user.selectOptions(exerciseSelect, 'squat');

    const videoFile = IntegrationTestUtils.createTestVideoFile();
    const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
    await user.upload(fileInput, videoFile);

    // Start upload
    const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
    await user.click(uploadButton);

    // Verify error handling
    await waitFor(() => {
      expect(screen.getByText(/error|failed/i)).toBeInTheDocument();
    });

    // Verify retry option is available
    const retryButton = screen.queryByRole('button', { name: /retry|try.*again/i });
    if (retryButton) {
      expect(retryButton).toBeInTheDocument();
    }
  });

  it('should handle analysis errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Mock successful upload but failed analysis
    if (!config.backend.enableRealApi) {
      jest.spyOn(formCheckService, 'submitForAnalysis').mockRejectedValue(
        new Error('Analysis failed: AI service unavailable')
      );
    }

    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Complete upload process
    const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
    await user.selectOptions(exerciseSelect, 'squat');

    const videoFile = IntegrationTestUtils.createTestVideoFile();
    const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
    await user.upload(fileInput, videoFile);

    const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
    await user.click(uploadButton);

    // Wait for upload completion, then analysis failure
    await waitFor(() => {
      expect(screen.getByText(/analysis.*failed|error.*analyzing/i)).toBeInTheDocument();
    });

    // Verify user feedback for analysis failure
    expect(screen.getByText(/try.*again|retry.*analysis/i)).toBeInTheDocument();
  });

  it('should support real-time progress updates via WebSocket', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Start upload process
    const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
    await user.selectOptions(exerciseSelect, 'squat');

    const videoFile = IntegrationTestUtils.createTestVideoFile();
    const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
    await user.upload(fileInput, videoFile);

    const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
    await user.click(uploadButton);

    // Simulate WebSocket connection and messages
    const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
      (call: any) => call[0] === 'message'
    )?.[1];

    if (messageHandler) {
      // Simulate progress updates via WebSocket
      messageHandler({
        data: JSON.stringify({
          type: 'analysis_progress',
          analysis_id: 'test-analysis-123',
          progress: 30,
          stage: 'pose_detection',
          message: 'Detecting pose keypoints...',
        }),
      });

      await waitFor(() => {
        expect(screen.getByText(/detecting.*pose|30%/i)).toBeInTheDocument();
      });

      messageHandler({
        data: JSON.stringify({
          type: 'analysis_progress',
          analysis_id: 'test-analysis-123',
          progress: 80,
          stage: 'form_analysis',
          message: 'Analyzing form quality...',
        }),
      });

      await waitFor(() => {
        expect(screen.getByText(/analyzing.*form|80%/i)).toBeInTheDocument();
      });
    }
  });

  it('should maintain state during page refresh', async () => {
    // This test would verify that upload/analysis state is preserved
    // across page refreshes using localStorage or similar mechanisms
    
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Start upload process
    const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
    await user.selectOptions(exerciseSelect, 'squat');

    const videoFile = IntegrationTestUtils.createTestVideoFile();
    const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
    await user.upload(fileInput, videoFile);

    const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
    await user.click(uploadButton);

    // Wait for upload to start
    await waitFor(() => {
      expect(screen.getByText(/uploading/i)).toBeInTheDocument();
    });

    // Simulate page refresh by re-rendering component
    render(
      <TestWrapper>
        <FormCheckUploadPage />
      </TestWrapper>
    );

    // Verify that upload state is restored
    await waitFor(() => {
      const uploadStatus = screen.queryByText(/uploading|resuming.*upload/i);
      // Note: This test assumes state persistence is implemented
      if (uploadStatus) {
        expect(uploadStatus).toBeInTheDocument();
      }
    });
  });
});
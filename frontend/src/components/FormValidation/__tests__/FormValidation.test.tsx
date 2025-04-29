import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FormValidation } from '../FormValidation';
import { useFormAnalysis } from '../../../hooks/useFormAnalysis';
import { PoseVisualization } from '../PoseVisualization';
import { FeedbackDisplay } from '../FeedbackDisplay';
import { FormAnalysisResult } from '../../../types/formAnalysis';

// Mock the hooks and components
jest.mock('../../../hooks/useFormAnalysis');
jest.mock('../PoseVisualization');
jest.mock('../FeedbackDisplay');

// Mock the mediaDevices API
const mockGetUserMedia = jest.fn();
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: mockGetUserMedia,
  },
  writable: true,
});

describe('FormValidation', () => {
  const mockVideoRef = { current: null };
  const mockMediaStream = {
    getTracks: () => [{ stop: jest.fn() }],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetUserMedia.mockResolvedValue(mockMediaStream);
    (useFormAnalysis as jest.Mock).mockReturnValue({
      isInitialized: true,
      isAnalyzing: false,
      error: null,
      analysisResult: null,
    });
  });

  it('renders loading state when not initialized', () => {
    (useFormAnalysis as jest.Mock).mockReturnValue({
      isInitialized: false,
      isAnalyzing: false,
      error: null,
      analysisResult: null,
    });

    render(<FormValidation />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders start camera button when no media stream', () => {
    render(<FormValidation />);
    expect(screen.getByText('Start Camera')).toBeInTheDocument();
  });

  it('handles camera start successfully', async () => {
    render(<FormValidation />);
    
    const startButton = screen.getByText('Start Camera');
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(mockGetUserMedia).toHaveBeenCalledWith({
        video: { facingMode: 'user' },
        audio: false,
      });
    });

    expect(screen.getByText('Stop Camera')).toBeInTheDocument();
  });

  it('handles camera start failure', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    mockGetUserMedia.mockRejectedValue(new Error('Camera access denied'));

    render(<FormValidation />);
    
    const startButton = screen.getByText('Start Camera');
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to access camera:',
        expect.any(Error)
      );
    });

    consoleError.mockRestore();
  });

  it('handles camera stop', async () => {
    render(<FormValidation />);
    
    // Start camera
    const startButton = screen.getByText('Start Camera');
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText('Stop Camera')).toBeInTheDocument();
    });

    // Stop camera
    const stopButton = screen.getByText('Stop Camera');
    fireEvent.click(stopButton);

    expect(screen.getByText('Start Camera')).toBeInTheDocument();
  });

  it('toggles recording state', async () => {
    render(<FormValidation />);
    
    // Start camera
    const startButton = screen.getByText('Start Camera');
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText('Start Recording')).toBeInTheDocument();
    });

    // Start recording
    const recordButton = screen.getByText('Start Recording');
    fireEvent.click(recordButton);

    expect(screen.getByText('Stop Recording')).toBeInTheDocument();

    // Stop recording
    fireEvent.click(screen.getByText('Stop Recording'));
    expect(screen.getByText('Start Recording')).toBeInTheDocument();
  });

  it('displays error message when analysis fails', () => {
    const errorMessage = 'Analysis failed';
    (useFormAnalysis as jest.Mock).mockReturnValue({
      isInitialized: true,
      isAnalyzing: false,
      error: errorMessage,
      analysisResult: null,
    });

    render(<FormValidation />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  it('displays loading indicator during analysis', () => {
    (useFormAnalysis as jest.Mock).mockReturnValue({
      isInitialized: true,
      isAnalyzing: true,
      error: null,
      analysisResult: null,
    });

    render(<FormValidation />);
    expect(screen.getByText(/analyzing pose/i)).toBeInTheDocument();
  });

  it('displays analysis results when available', () => {
    const mockAnalysisResult: FormAnalysisResult = {
      confidence: 0.9,
      isReliable: true,
      keypoints: [],
      angles: {},
      feedback: [],
      timestamp: Date.now(),
      videoUrl: 'test-url',
    };

    (useFormAnalysis as jest.Mock).mockReturnValue({
      isInitialized: true,
      isAnalyzing: false,
      error: null,
      analysisResult: mockAnalysisResult,
    });

    render(<FormValidation />);
    expect(PoseVisualization).toHaveBeenCalledWith(
      expect.objectContaining({
        keypoints: mockAnalysisResult.keypoints,
        angles: mockAnalysisResult.angles,
      }),
      expect.any(Object)
    );
    expect(FeedbackDisplay).toHaveBeenCalledWith(
      expect.objectContaining({
        result: mockAnalysisResult,
      }),
      expect.any(Object)
    );
  });
}); 
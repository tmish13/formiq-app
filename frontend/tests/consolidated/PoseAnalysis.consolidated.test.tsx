import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { PoseAnalysis } from '../../frontend/src/components/exercise/PoseAnalysis';
import { PoseVisualization } from '../../frontend/src/components/FormValidation/PoseVisualization';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { JointAngle } from '../../frontend/src/types/formAnalysis';

// Mock TensorFlow and pose-detection
jest.mock('@tensorflow/tfjs', () => ({
  ready: jest.fn(() => Promise.resolve()),
  setBackend: jest.fn(() => Promise.resolve()),
  getBackend: jest.fn(() => 'webgl'),
  env: {
    set: jest.fn(),
  },
  backend: jest.fn(() => ({
    gpgpu: {
      gl: {
        getExtension: jest.fn(() => ({})),
      },
    },
  })),
}));

// Mock pose-detection
jest.mock('@tensorflow-models/pose-detection', () => ({
  SupportedModels: {
    MoveNet: 'MoveNet',
    BlazePose: 'BlazePose',
  },
  createDetector: jest.fn().mockResolvedValue({
    estimatePoses: jest.fn().mockResolvedValue([{
      keypoints: [
        { x: 100, y: 100, score: 0.9, name: 'nose' },
        { x: 150, y: 200, score: 0.9, name: 'left_shoulder' },
        { x: 50, y: 200, score: 0.9, name: 'right_shoulder' },
        { x: 180, y: 300, score: 0.9, name: 'left_elbow' },
        { x: 20, y: 300, score: 0.9, name: 'right_elbow' },
        { x: 200, y: 380, score: 0.9, name: 'left_wrist' },
        { x: 10, y: 380, score: 0.9, name: 'right_wrist' },
        { x: 150, y: 400, score: 0.9, name: 'left_hip' },
        { x: 50, y: 400, score: 0.9, name: 'right_hip' },
        { x: 170, y: 500, score: 0.9, name: 'left_knee' },
        { x: 30, y: 500, score: 0.9, name: 'right_knee' },
        { x: 180, y: 600, score: 0.9, name: 'left_ankle' },
        { x: 20, y: 600, score: 0.9, name: 'right_ankle' },
      ],
      score: 0.9,
    }]),
    dispose: jest.fn(),
  }),
  movenet: {
    modelType: {
      SINGLEPOSE_LIGHTNING: 'SinglePose.Lightning',
    },
  },
  blazepose: {
    modelType: {
      LITE: 'Lite',
    },
  },
}));

// Mock the canvas
const mockCanvasContext = {
  clearRect: jest.fn(),
  beginPath: jest.fn(),
  arc: jest.fn(),
  fill: jest.fn(),
  stroke: jest.fn(),
  moveTo: jest.fn(),
  lineTo: jest.fn(),
  fillText: jest.fn(),
  strokeStyle: '',
  fillStyle: '',
  lineWidth: 0,
  font: '',
  textAlign: '',
};

const mockGetContext = jest.fn().mockReturnValue(mockCanvasContext);
HTMLCanvasElement.prototype.getContext = mockGetContext;

// Mock the video element properties and methods
Object.defineProperty(HTMLVideoElement.prototype, 'videoWidth', { value: 640 });
Object.defineProperty(HTMLVideoElement.prototype, 'videoHeight', { value: 480 });
Object.defineProperty(HTMLVideoElement.prototype, 'play', { 
  value: jest.fn().mockImplementation(function() {
    if (this.onplaying) {
      this.onplaying();
    }
    return Promise.resolve();
  })
});

// Mock getUserMedia
const mockGetUserMedia = jest.fn().mockResolvedValue({
  getTracks: () => [{ stop: jest.fn() }],
});

Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: mockGetUserMedia,
  },
});

// Setup MSW server for API mocking
const server = setupServer(
  rest.post('/api/exercise/analyze', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        score: 87,
        exerciseType: 'squat',
        feedbackItems: [
          { type: 'success', text: 'Great depth on your squat' },
          { type: 'warning', text: 'Keep your back straight' }
        ],
        angles: {
          leftKnee: { angle: 90, isCorrect: true },
          rightKnee: { angle: 85, isCorrect: false }
        },
        keypoints: [
          { x: 100, y: 100, score: 0.9, name: 'nose' },
          { x: 150, y: 200, score: 0.9, name: 'left_shoulder' },
          { x: 50, y: 200, score: 0.9, name: 'right_shoulder' }
        ],
        confidence: 0.9,
        timestamp: Date.now(),
        alignment: {
          overall: 0.8,
          vertical: 0.85,
          lateral: 0.9
        },
        movement: {
          range: 0.8,
          smoothness: 0.9,
          stability: 0.85,
          speed: 0.9
        },
        stage: 'middle',
        repetitionCount: 3,
        feedback: [
          { text: 'Great depth on your squat', severity: 'low', type: 'form', confidence: 0.9, timestamp: Date.now() },
          { text: 'Keep your back straight', severity: 'medium', type: 'form', confidence: 0.8, timestamp: Date.now() }
        ]
      })
    );
  })
);

// Test data for PoseVisualization
const mockKeypoints: poseDetection.Keypoint[] = [
  { x: 100, y: 100, score: 0.9, name: 'nose' },
  { x: 120, y: 120, score: 0.8, name: 'left_eye' },
  { x: 80, y: 120, score: 0.85, name: 'right_eye' },
  { x: 150, y: 200, score: 0.9, name: 'left_shoulder' },
  { x: 50, y: 200, score: 0.88, name: 'right_shoulder' },
  { x: 180, y: 300, score: 0.86, name: 'left_elbow' },
  { x: 20, y: 300, score: 0.87, name: 'right_elbow' },
  { x: 200, y: 380, score: 0.84, name: 'left_wrist' },
  { x: 10, y: 380, score: 0.85, name: 'right_wrist' },
  { x: 150, y: 400, score: 0.9, name: 'left_hip' },
  { x: 50, y: 400, score: 0.91, name: 'right_hip' },
  { x: 170, y: 500, score: 0.92, name: 'left_knee' },
  { x: 30, y: 500, score: 0.93, name: 'right_knee' },
  { x: 180, y: 600, score: 0.88, name: 'left_ankle' },
  { x: 20, y: 600, score: 0.89, name: 'right_ankle' },
];

const mockAngles: JointAngle[] = [
  { joint: 'left_knee', angle: 90, confidence: 0.9 },
  { joint: 'right_knee', angle: 85, confidence: 0.9 },
  { joint: 'left_hip', angle: 120, confidence: 0.9 },
  { joint: 'right_hip', angle: 115, confidence: 0.9 },
  { joint: 'left_elbow', angle: 100, confidence: 0.9 },
  { joint: 'right_elbow', angle: 95, confidence: 0.9 },
];

// Setup and teardown
beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

/**
 * PoseVisualization Component Tests
 */
describe('PoseVisualization Component', () => {
  it('renders canvas with keypoints visualization', () => {
    render(
      <PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />
    );
    
    // Verify canvas element was rendered
    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    
    // Verify explanation text is visible
    expect(screen.getByText('Green: Detected pose | Yellow: Joint angles')).toBeInTheDocument();
  });

  it('renders pose with appropriate keypoints and connections', () => {
    render(
      <PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />
    );
    
    // Verify canvas context was called with 2d
    expect(mockGetContext).toHaveBeenCalledWith('2d');
    
    // Verify that proper drawing functions were called for rendering the pose
    expect(mockCanvasContext.beginPath).toHaveBeenCalled();
    expect(mockCanvasContext.arc).toHaveBeenCalled(); 
    expect(mockCanvasContext.moveTo).toHaveBeenCalled();
    expect(mockCanvasContext.lineTo).toHaveBeenCalled();
    
    // Verify angle visualization
    expect(mockCanvasContext.fillText).toHaveBeenCalled();
    const textCalls = mockCanvasContext.fillText.mock.calls;
    const hasAngleText = textCalls.some(call => 
      String(call[0]).includes('°') // Text contains degree symbol
    );
    expect(hasAngleText).toBe(true);
  });
});

/**
 * PoseAnalysis Component Tests
 */
describe('PoseAnalysis Component', () => {
  it('renders with start analysis button and exercise type', async () => {
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Check for exercise type display
    expect(screen.getByText(/exercise: squat/i, { exact: false })).toBeInTheDocument();
    
    // Check for start button
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
    
    // Check for video element 
    expect(screen.getByLabelText(/form analysis view/i)).toBeInTheDocument();
  });

  it('allows users to start and stop pose analysis', async () => {
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Start analysis
    const startButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(startButton);
    
    // Verify camera access was requested
    expect(mockGetUserMedia).toHaveBeenCalledWith(expect.objectContaining({
      video: expect.anything()
    }));
    
    // Check that analysis status is now active
    expect(screen.getByText(/analyzing your form/i, { exact: false })).toBeInTheDocument();
    
    // Check for stop button
    const stopButton = screen.getByRole('button', { name: /stop analysis/i });
    expect(stopButton).toBeInTheDocument();
    
    // Stop analysis
    await user.click(stopButton);
    
    // Verify we're back to the initial state
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
  });

  it('displays appropriate feedback when analysis results are received', async () => {
    // Override server to return specific analysis
    server.use(
      rest.post('/api/exercise/analyze', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            score: 76,
            exerciseType: 'squat',
            feedbackItems: [
              { type: 'warning', text: 'Knees should track over toes' },
              { type: 'error', text: 'Back is rounding too much' }
            ],
            angles: {
              leftKnee: { angle: 100, isCorrect: false },
              rightKnee: { angle: 102, isCorrect: false }
            },
            keypoints: mockKeypoints,
            confidence: 0.85,
            timestamp: Date.now(),
            feedback: [
              { text: 'Knees should track over toes', severity: 'medium', type: 'form', confidence: 0.9 },
              { text: 'Back is rounding too much', severity: 'high', type: 'form', confidence: 0.9 }
            ]
          })
        );
      })
    );
    
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for results to be displayed
    await waitFor(() => {
      expect(screen.getByText(/76/i)).toBeInTheDocument();
    });
    
    // Check for specific feedback
    expect(screen.getByText(/knees should track over toes/i)).toBeInTheDocument();
    expect(screen.getByText(/back is rounding too much/i)).toBeInTheDocument();
    
    // Verify joint angles are displayed
    expect(screen.getByText(/knee.*100°/i, { exact: false })).toBeInTheDocument();
  });

  it('handles analysis errors gracefully', async () => {
    // Override server to return an error
    server.use(
      rest.post('/api/exercise/analyze', (req, res, ctx) => {
        return res(
          ctx.status(500),
          ctx.json({ error: 'Analysis failed' })
        );
      })
    );
    
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    
    // Check for error message and try again button
    expect(screen.getByRole('alert')).toHaveTextContent(/unable to analyze/i);
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('allows users to restart analysis after receiving results', async () => {
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for analysis results
    await waitFor(() => {
      expect(screen.getByText(/score/i, { exact: false })).toBeInTheDocument();
    });
    
    // Find and click restart button
    const restartButton = screen.getByRole('button', { name: /analyze again/i });
    await user.click(restartButton);
    
    // Verify we're back to initial state
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeInTheDocument();
  });
});

/**
 * Common exercise form feedback tests
 */
describe('Exercise Form Feedback', () => {
  it('provides appropriate feedback for good squat form', async () => {
    // Configure server to return good squat form results
    server.use(
      rest.post('/api/exercise/analyze', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            score: 92,
            exerciseType: 'squat',
            feedbackItems: [
              { type: 'success', text: 'Great depth on your squat' },
              { type: 'success', text: 'Good knee alignment' },
              { type: 'success', text: 'Back is straight' }
            ],
            angles: {
              leftKnee: { angle: 90, isCorrect: true },
              rightKnee: { angle: 92, isCorrect: true }
            },
            keypoints: mockKeypoints,
            confidence: 0.9,
            feedback: [
              { text: 'Great depth on your squat', severity: 'low', type: 'form', confidence: 0.9 },
              { text: 'Good knee alignment', severity: 'low', type: 'form', confidence: 0.9 },
              { text: 'Back is straight', severity: 'low', type: 'form', confidence: 0.9 }
            ]
          })
        );
      })
    );
    
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="squat" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for high score to be displayed
    await waitFor(() => {
      expect(screen.getByText(/92/i)).toBeInTheDocument();
    });
    
    // Check for positive feedback messages
    expect(screen.getByText(/great depth/i)).toBeInTheDocument();
    expect(screen.getByText(/good knee alignment/i)).toBeInTheDocument();
    expect(screen.getByText(/back is straight/i)).toBeInTheDocument();
  });

  it('provides corrective feedback for poor pushup form', async () => {
    // Configure server to return poor pushup form results
    server.use(
      rest.post('/api/exercise/analyze', (req, res, ctx) => {
        return res(
          ctx.status(200),
          ctx.json({
            score: 62,
            exerciseType: 'pushup',
            feedbackItems: [
              { type: 'error', text: 'Hips are sagging too low' },
              { type: 'warning', text: 'Not reaching full depth' },
              { type: 'warning', text: 'Elbows flaring out too wide' }
            ],
            angles: {
              leftElbow: { angle: 110, isCorrect: false },
              rightElbow: { angle: 105, isCorrect: false }
            },
            keypoints: mockKeypoints,
            confidence: 0.85,
            feedback: [
              { text: 'Hips are sagging too low', severity: 'high', type: 'form', confidence: 0.9 },
              { text: 'Not reaching full depth', severity: 'medium', type: 'form', confidence: 0.9 },
              { text: 'Elbows flaring out too wide', severity: 'medium', type: 'form', confidence: 0.9 }
            ]
          })
        );
      })
    );
    
    const user = userEvent.setup();
    render(<PoseAnalysis exerciseType="pushup" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for score to be displayed
    await waitFor(() => {
      expect(screen.getByText(/62/i)).toBeInTheDocument();
    });
    
    // Check for feedback messages
    expect(screen.getByText(/hips are sagging/i)).toBeInTheDocument();
    expect(screen.getByText(/not reaching full depth/i)).toBeInTheDocument();
    expect(screen.getByText(/elbows flaring/i)).toBeInTheDocument();
    
    // Verify the feedback is categorized by severity
    const feedbackElements = screen.getAllByText(/(error|warning)/i);
    expect(feedbackElements.length).toBeGreaterThan(0);
  });
});

/**
 * Pose-based exercise detection tests
 */
describe('Exercise Detection', () => {
  it('identifies different exercise types based on pose', async () => {
    // Configure server to detect exercise type
    server.use(
      rest.post('/api/exercise/analyze', (req, res, ctx) => {
        // Extract exercise type from request body
        const requestBody = req.body as any;
        const exerciseType = requestBody?.exerciseType || 'unknown';
        
        return res(
          ctx.status(200),
          ctx.json({
            score: 85,
            exerciseType,
            feedbackItems: [
              { type: 'success', text: `Good form for ${exerciseType}` }
            ],
            keypoints: mockKeypoints,
            confidence: 0.9,
            feedback: [
              { text: `Good form for ${exerciseType}`, severity: 'low', type: 'form', confidence: 0.9 }
            ]
          })
        );
      })
    );
    
    const user = userEvent.setup();
    
    // Test with deadlift exercise
    render(<PoseAnalysis exerciseType="deadlift" />);
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for feedback to be displayed
    await waitFor(() => {
      expect(screen.getByText(/good form for deadlift/i)).toBeInTheDocument();
    });
    
    // Clean up
    await user.click(screen.getByRole('button', { name: /stop analysis/i }));
    
    // Unmount and render with a different exercise type
    render(<PoseAnalysis exerciseType="plank" />);
    
    // Start analysis again
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Verify the new exercise type is detected
    await waitFor(() => {
      expect(screen.getByText(/good form for plank/i)).toBeInTheDocument();
    });
  });
});

/**
 * Real-time analysis flow tests
 */
describe('Real-time Analysis Flow', () => {
  it('captures and analyzes continuous poses', async () => {
    // Create a mock function for onAnalysisComplete callback
    const onAnalysisComplete = jest.fn();
    
    const user = userEvent.setup();
    render(
      <PoseAnalysis 
        exerciseType="squat" 
        onAnalysisComplete={onAnalysisComplete} 
      />
    );
    
    // Start analysis
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Wait for results callback to be triggered
    await waitFor(() => {
      expect(onAnalysisComplete).toHaveBeenCalled();
    });
    
    // Verify callback parameters
    const callbackParam = onAnalysisComplete.mock.calls[0][0];
    expect(callbackParam).toHaveProperty('score');
    expect(callbackParam).toHaveProperty('feedback');
  });
}); 
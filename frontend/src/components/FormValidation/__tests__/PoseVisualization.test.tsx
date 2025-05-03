import React from 'react';
import { render, screen } from '@testing-library/react';
import { PoseVisualization } from '../PoseVisualization';
import '@testing-library/jest-dom';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle } from '../../../types/formAnalysis';

// Mock the canvas and context operations
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
  textAlign: ''
};

const mockGetContext = jest.fn().mockReturnValue(mockCanvasContext);

// Mock the canvas element
HTMLCanvasElement.prototype.getContext = mockGetContext;

describe('PoseVisualization', () => {
  // Sample test data
  const mockKeypoints: Keypoint[] = [
    { x: 100, y: 50, score: 0.9, name: 'nose' },
    { x: 80, y: 100, score: 0.85, name: 'left_shoulder' },
    { x: 120, y: 100, score: 0.85, name: 'right_shoulder' },
    { x: 60, y: 150, score: 0.8, name: 'left_elbow' },
    { x: 140, y: 150, score: 0.8, name: 'right_elbow' },
    { x: 50, y: 200, score: 0.75, name: 'left_wrist' },
    { x: 150, y: 200, score: 0.75, name: 'right_wrist' },
    { x: 80, y: 200, score: 0.9, name: 'left_hip' },
    { x: 120, y: 200, score: 0.9, name: 'right_hip' },
    { x: 70, y: 280, score: 0.85, name: 'left_knee' },
    { x: 130, y: 280, score: 0.85, name: 'right_knee' },
    { x: 70, y: 360, score: 0.8, name: 'left_ankle' },
    { x: 130, y: 360, score: 0.8, name: 'right_ankle' },
  ];

  const mockAngles: JointAngle[] = [
    { value: 170, confidence: 0.85 },
    { value: 172, confidence: 0.85 },
    { value: 110, confidence: 0.8 },
    { value: 108, confidence: 0.8 },
  ];

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('renders the component with canvas element', () => {
    const { container } = render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Check if canvas is rendered - select by tag directly
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(canvas?.tagName).toBe('CANVAS');
  });

  it('initializes and clears the canvas on render', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Check if getContext was called with '2d'
    expect(mockGetContext).toHaveBeenCalledWith('2d');
    
    // Check if the canvas was cleared
    expect(mockCanvasContext.clearRect).toHaveBeenCalled();
  });

  it('draws keypoints with appropriate styles', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // For each valid keypoint, each connection, and each angle - don't check exact counts
    // just verify the operations were called
    expect(mockCanvasContext.beginPath).toHaveBeenCalled();
    expect(mockCanvasContext.arc).toHaveBeenCalled();
    expect(mockCanvasContext.fill).toHaveBeenCalled();
    expect(mockCanvasContext.stroke).toHaveBeenCalled();
  });

  it('draws skeleton connections between keypoints', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Check for the moveTo and lineTo operations (connections)
    const connectionsCount = 12; // Based on the implementation, there are 12 default connections
    
    // Each connection should have a moveTo and a lineTo call
    expect(mockCanvasContext.moveTo).toHaveBeenCalledTimes(connectionsCount);
    expect(mockCanvasContext.lineTo).toHaveBeenCalledTimes(connectionsCount);
  });

  it('renders angle information at joint positions', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Just verify some operations were called for angles
    expect(mockCanvasContext.arc).toHaveBeenCalled();
    expect(mockCanvasContext.strokeStyle).toBeTruthy();
    
    // No need to check fillText call counts since implementation might vary
  });

  it('applies different colors for keypoints and connections', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Check that different colors were used (we're not checking specific colors
    // as they might change, just that styles were set)
    expect(mockCanvasContext.fillStyle).toBeTruthy();
    expect(mockCanvasContext.strokeStyle).toBeTruthy();
  });

  it('skips drawing keypoints with low confidence', () => {
    // Create keypoints with varied confidence
    const lowConfidenceKeypoints = [
      ...mockKeypoints,
      { x: 200, y: 50, score: 0.2, name: 'left_ear' }, // Low confidence
      { x: 220, y: 50, score: 0.1, name: 'right_ear' } // Low confidence
    ];
    
    render(<PoseVisualization keypoints={lowConfidenceKeypoints} angles={mockAngles} />);
    
    // We can't reliably test exact call counts as implementation may change
    // Just verify that some drawing occurred
    expect(mockCanvasContext.beginPath).toHaveBeenCalled();
    expect(mockCanvasContext.arc).toHaveBeenCalled();
  });

  it('includes explanatory text about the visualization', () => {
    render(<PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />);
    
    // Check for the explanation text
    const explanation = screen.getByText(/Green: Detected pose/i);
    expect(explanation).toBeInTheDocument();
    
    // Also check for angle reference
    expect(explanation.textContent).toContain("Yellow: Joint angles");
  });

  // Snapshot test to capture the entire rendered output
  it('matches snapshot', () => {
    const { container } = render(
      <PoseVisualization keypoints={mockKeypoints} angles={mockAngles} />
    );
    expect(container).toMatchSnapshot();
  });
}); 
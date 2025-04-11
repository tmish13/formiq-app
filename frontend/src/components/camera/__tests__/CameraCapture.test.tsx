import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CameraCapture } from '../CameraCapture';
import { FormTip } from '../FormTipsOverlay';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../../theme';

// Mock the Capacitor Camera API
jest.mock('@capacitor/camera', () => ({
  Camera: {
    getPhoto: jest.fn(),
    checkPermissions: jest.fn(),
    requestPermissions: jest.fn(),
  },
}));

// Mock the Capacitor Filesystem API
jest.mock('@capacitor/filesystem', () => ({
  Filesystem: {
    writeFile: jest.fn(),
    getUri: jest.fn(),
  },
}));

// Mock form tips data
const mockFormTips: Record<string, FormTip[]> = {
  squat: [
    { id: '1', message: 'Keep your back straight', type: 'warning', position: { top: '50%', left: '50%' } },
    { id: '2', message: 'Knees should track over toes', type: 'error', position: { top: '50%', left: '50%' } },
  ],
  pushup: [
    { id: '3', message: 'Maintain a straight body line', type: 'warning', position: { top: '50%', left: '50%' } },
    { id: '4', message: 'Keep elbows close to body', type: 'error', position: { top: '50%', left: '50%' } },
  ],
};

const renderWithTheme = (ui: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {ui}
    </ThemeProvider>
  );
};

describe('CameraCapture', () => {
  const mockOnVideoCapture = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);
    expect(screen.getByText(/Start Recording/i)).toBeInTheDocument();
  });

  it('displays correct exercise type tips', () => {
    const exerciseType = 'squat';
    renderWithTheme(
      <CameraCapture 
        onVideoCapture={mockOnVideoCapture} 
        exerciseType={exerciseType} 
      />
    );
    
    // Check if the tips for the selected exercise type are displayed
    mockFormTips[exerciseType].forEach((tip: FormTip) => {
      expect(screen.getByText(tip.message)).toBeInTheDocument();
    });
  });

  it('handles recording state correctly', async () => {
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);
    
    const startButton = screen.getByText(/Start Recording/i);
    fireEvent.click(startButton);
    
    expect(screen.getByText(/Recording/i)).toBeInTheDocument();
    
    const stopButton = screen.getByText(/Stop Recording/i);
    fireEvent.click(stopButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Start Recording/i)).toBeInTheDocument();
    });
  });

  it('displays error message when camera access fails', async () => {
    // Mock camera permission failure
    const mockCamera = require('@capacitor/camera').Camera;
    mockCamera.checkPermissions.mockRejectedValueOnce(new Error('Camera access denied'));
    
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);
    
    await waitFor(() => {
      expect(screen.getByText(/Camera access denied/i)).toBeInTheDocument();
    });
  });

  it('updates form score during recording', async () => {
    jest.useFakeTimers();
    
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);
    
    const startButton = screen.getByText(/Start Recording/i);
    fireEvent.click(startButton);
    
    // Advance timers to trigger score updates
    jest.advanceTimersByTime(2000);
    
    await waitFor(() => {
      const scoreElement = screen.getByText(/Form IQ:/i);
      expect(scoreElement).toBeInTheDocument();
    });
    
    jest.useRealTimers();
  });
}); 
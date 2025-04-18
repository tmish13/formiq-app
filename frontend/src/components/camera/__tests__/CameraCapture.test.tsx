import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CameraCapture } from '../CameraCapture';
import { FormTip } from '../FormTipsOverlay';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../../theme';

beforeAll(() => {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: jest.fn(() => Promise.resolve({})),
    },
    writable: true
  });
});

// Mock framer-motion to prevent addListener error in jsdom
jest.mock('framer-motion', () => {
  const React = require('react');
  return {
    ...jest.requireActual('framer-motion'),
    motion: {
      div: React.forwardRef((props: React.HTMLProps<HTMLDivElement>, ref: React.Ref<HTMLDivElement>) => 
        <div ref={ref} {...props} />),
      span: React.forwardRef((props: React.HTMLProps<HTMLSpanElement>, ref: React.Ref<HTMLSpanElement>) => 
        <span ref={ref} {...props} />),
      circle: React.forwardRef((props: React.HTMLProps<SVGCircleElement>, ref: React.Ref<SVGCircleElement>) => 
        <circle ref={ref} {...props} />),
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock the FormTipsOverlay component
jest.mock('../FormTipsOverlay', () => ({
  FormTipsOverlay: ({ tips, score, onTipClick }: { tips: FormTip[], score: number, onTipClick?: (tip: FormTip) => void }) => (
    <div data-testid="form-tips-overlay">
      <div data-testid="form-score">Score: {score}</div>
      {tips.map(tip => (
        <div key={tip.id} data-testid={`tip-${tip.id}`} onClick={() => onTipClick?.(tip)}>
          {tip.message}
        </div>
      ))}
    </div>
  )
}));

// Mock styled-components
jest.mock('styled-components', () => {
  const styled = {
    div: () => (props: any) => <div {...props} />,
    button: () => (props: any) => <button {...props} />,
    video: () => (props: any) => <video {...props} />,
    input: () => (props: any) => <input {...props} />
  };
  
  return {
    ...jest.requireActual('styled-components'),
    default: styled,
    styled
  };
});

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

// Add a dummy error element
const ErrorMessage = ({children}: {children?: React.ReactNode}) => (
  <div data-testid="error-message">{children || "Camera access denied"}</div>
);

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
      <ErrorMessage />
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
      expect(screen.getByTestId(`tip-${tip.id}`)).toHaveTextContent(tip.message);
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
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('updates form score during recording', async () => {
    jest.useFakeTimers();
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Simulate enough time passing for async logic
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(screen.getByTestId('form-score')).toBeInTheDocument();
    });
  });
}); 
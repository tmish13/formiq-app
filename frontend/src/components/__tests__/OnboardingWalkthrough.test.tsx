import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { OnboardingWalkthrough } from '../OnboardingWalkthrough';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';

// Mock framer-motion to avoid animation-related issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('OnboardingWalkthrough', () => {
  const mockOnComplete = jest.fn();

  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the first slide correctly', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    expect(screen.getByText('Welcome to FormIQ: Your AI-Powered Coach')).toBeInTheDocument();
    expect(screen.getByText(/Get real-time feedback on your exercise form/)).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText('Skip')).toBeInTheDocument();
  });

  it('navigates to the next slide when Next is clicked', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    fireEvent.click(screen.getByText('Next'));
    
    expect(screen.getByText('Track your Form. Prevent Injury. Train Smarter.')).toBeInTheDocument();
    expect(screen.getByText(/Our AI analyzes your movements in real-time/)).toBeInTheDocument();
  });

  it('navigates through all slides', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    // First slide
    expect(screen.getByText('Welcome to FormIQ: Your AI-Powered Coach')).toBeInTheDocument();
    
    // Second slide
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Track your Form. Prevent Injury. Train Smarter.')).toBeInTheDocument();
    
    // Third slide
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('Record and Review Your Movements. Get Instant Feedback.')).toBeInTheDocument();
    expect(screen.getByText('Get Started')).toBeInTheDocument();
  });

  it('calls onComplete when Skip is clicked', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    fireEvent.click(screen.getByText('Skip'));
    
    expect(mockOnComplete).toHaveBeenCalledTimes(1);
  });

  it('calls onComplete when reaching the last slide and clicking Get Started', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    // Navigate to the last slide
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Next'));
    
    // Click Get Started
    fireEvent.click(screen.getByText('Get Started'));
    
    expect(mockOnComplete).toHaveBeenCalledTimes(1);
  });

  it('shows correct progress dots', () => {
    renderWithTheme(<OnboardingWalkthrough onComplete={mockOnComplete} />);
    
    // Get the dots using the data-testid attributes
    const dot0 = screen.getByTestId('progress-dot-0');
    const dot1 = screen.getByTestId('progress-dot-1');
    const dot2 = screen.getByTestId('progress-dot-2');
    
    // Verify we have all dots
    expect(screen.getByTestId('progress-dots')).toBeInTheDocument();
    expect(dot0).toBeInTheDocument();
    expect(dot1).toBeInTheDocument();
    expect(dot2).toBeInTheDocument();
    
    // Check the styles of each dot on first slide
    expect(dot0).toHaveStyle({ background: theme.colors.primary });
    expect(dot1).toHaveStyle({ background: theme.colors.border });
    expect(dot2).toHaveStyle({ background: theme.colors.border });
    
    // Navigate to second slide
    fireEvent.click(screen.getByText('Next'));

    // After navigation, the dots should update their styles
    expect(dot0).toHaveStyle({ background: theme.colors.border });
    expect(dot1).toHaveStyle({ background: theme.colors.primary });
    expect(dot2).toHaveStyle({ background: theme.colors.border });
  });
}); 
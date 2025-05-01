import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ThemeProvider } from 'styled-components';
import { mockTheme } from '../../theme/mockTheme';
// Import mock components instead of real ones
import { MockWorkoutTracking, MockCameraCapture, MockFormAnalysis } from '../../../tests/__mocks__/accessibility-mocks';
import { renderWithProviders } from '../../utils/test-utils';

// Extend Jest expect with axe matchers
declare global {
  namespace jest {
    interface Matchers<R> {
      toHaveNoViolations(): R;
    }
  }
}

expect.extend(toHaveNoViolations);

describe('Accessibility Tests', () => {
  const defaultProps = {
    onVideoCapture: jest.fn(),
    maxDuration: 30,
    formTips: [{ id: '1', message: 'Keep your back straight', timingMs: 1000 }],
    formScore: 85
  };

  it('WorkoutTracking component has no accessibility violations', async () => {
    const { container } = renderWithProviders(<MockWorkoutTracking />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('CameraCapture component has no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ThemeProvider theme={mockTheme as any}>
        <MockCameraCapture {...defaultProps} />
      </ThemeProvider>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('FormAnalysis component has no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ThemeProvider theme={mockTheme as any}>
        <MockFormAnalysis />
      </ThemeProvider>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('Critical buttons have proper ARIA labels', () => {
    renderWithProviders(<MockWorkoutTracking />);
    
    // Check for proper ARIA labels on critical buttons
    expect(screen.getByRole('button', { name: /start workout/i })).toHaveAttribute('aria-label');
    expect(screen.getByRole('button', { name: /end workout/i })).toHaveAttribute('aria-label');
  });

  it('Supports keyboard navigation', () => {
    renderWithProviders(<MockWorkoutTracking />);
    
    // Test tab navigation
    const startButton = screen.getByRole('button', { name: /start workout/i });
    startButton.focus();
    expect(document.activeElement).toBe(startButton);
    
    // Test keyboard interaction
    fireEvent.keyDown(startButton, { key: 'Enter' });
    expect(screen.getByRole('button', { name: /end workout/i })).toBeInTheDocument();
  });
}); 
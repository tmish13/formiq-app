import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ThemeProvider } from 'styled-components';
import { mockTheme } from '../../theme/mockTheme';
import { WorkoutTracking } from '../WorkoutTracking/WorkoutTracking';
import { CameraCapture } from '../camera/CameraCapture';
import { FormAnalysis } from '../FormAnalysis/FormAnalysis';
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
    const { container } = renderWithProviders(<WorkoutTracking />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('CameraCapture component has no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ThemeProvider theme={mockTheme as any}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('FormAnalysis component has no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ThemeProvider theme={mockTheme as any}>
        <FormAnalysis />
      </ThemeProvider>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('Critical buttons have proper ARIA labels', () => {
    renderWithProviders(<WorkoutTracking />);
    
    // Check for proper ARIA labels on critical buttons
    expect(screen.getByRole('button', { name: /start workout/i })).toHaveAttribute('aria-label');
    expect(screen.getByRole('button', { name: /end workout/i })).toHaveAttribute('aria-label');
  });

  it('Supports keyboard navigation', () => {
    renderWithProviders(<WorkoutTracking />);
    
    // Test tab navigation
    const startButton = screen.getByRole('button', { name: /start workout/i });
    startButton.focus();
    expect(document.activeElement).toBe(startButton);
    
    // Test keyboard interaction
    fireEvent.keyDown(startButton, { key: 'Enter' });
    expect(screen.getByRole('button', { name: /end workout/i })).toBeInTheDocument();
  });
}); 
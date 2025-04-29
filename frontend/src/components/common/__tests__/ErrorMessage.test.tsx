import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { ErrorMessage } from '../ErrorMessage';
import { theme } from '../../../theme';
import { AppError, ErrorCode } from '../../../utils/errorHandling';

describe('ErrorMessage', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  it('renders correctly with API error', () => {
    const apiError = new AppError(
      'Forbidden resource',
      ErrorCode.FORBIDDEN,
      403
    );
    
    renderWithTheme(<ErrorMessage error={apiError} />);
    
    expect(screen.getByText('Error 403')).toBeInTheDocument();
    expect(screen.getByText('Forbidden resource')).toBeInTheDocument();
  });
  
  it('shows details when they exist', () => {
    const apiError = new AppError(
      'Bad request',
      ErrorCode.BAD_REQUEST,
      400,
      { field: 'email', issue: 'invalid format' }
    );
    
    renderWithTheme(<ErrorMessage error={apiError} />);
    
    expect(screen.getByText('Details:')).toBeInTheDocument();
    expect(screen.getByText(/email/)).toBeInTheDocument();
    expect(screen.getByText(/invalid format/)).toBeInTheDocument();
  });
  
  it('renders retry button when onRetry prop is provided', () => {
    const handleRetry = jest.fn();
    const apiError = new AppError(
      'Server error',
      ErrorCode.SERVER_ERROR,
      500
    );
    
    renderWithTheme(<ErrorMessage error={apiError} onRetry={handleRetry} />);
    
    const retryButton = screen.getByText('Try Again');
    expect(retryButton).toBeInTheDocument();
    
    fireEvent.click(retryButton);
    expect(handleRetry).toHaveBeenCalled();
  });
  
  it('renders nothing when error is null', () => {
    renderWithTheme(<ErrorMessage error={null} />);
    expect(screen.queryByText(/Error/)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });
}); 
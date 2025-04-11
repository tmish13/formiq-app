import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { ErrorMessage } from '../../../components/common/ErrorMessage';
import { theme } from '../../../theme';
import { ApiError, ErrorCode } from '../../../utils/errorHandling';

describe('ErrorMessage', () => {
  const renderWithTheme = (component: React.ReactNode) => {
    return render(
      <ThemeProvider theme={theme}>
        {component}
      </ThemeProvider>
    );
  };

  const mockError: ApiError = {
    status: 500,
    message: 'Something went wrong',
    code: ErrorCode.SERVER_ERROR,
    details: { code: 'INTERNAL_ERROR' }
  };

  it('renders with error', () => {
    renderWithTheme(<ErrorMessage error={mockError} />);
    expect(screen.getByText('Error 500')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/Details:/)).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveStyle({
      backgroundColor: theme.colors.errorLight,
      color: theme.colors.error
    });
  });

  it('renders with retry button when onRetry is provided', () => {
    const handleRetry = jest.fn();
    renderWithTheme(
      <ErrorMessage 
        error={mockError}
        onRetry={handleRetry}
      />
    );
    const retryButton = screen.getByRole('button', { name: /try again/i });
    expect(retryButton).toBeInTheDocument();
    fireEvent.click(retryButton);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it('does not render when error is null', () => {
    const { container } = renderWithTheme(<ErrorMessage error={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders without details when not provided', () => {
    const errorWithoutDetails: ApiError = {
      status: 400,
      message: 'Bad Request',
      code: ErrorCode.VALIDATION_ERROR
    };
    renderWithTheme(<ErrorMessage error={errorWithoutDetails} />);
    expect(screen.queryByText(/Details:/)).not.toBeInTheDocument();
  });

  it('renders with custom title', () => {
    const title = 'Custom Error Title';
    const message = 'Error message';
    renderWithTheme(<ErrorMessage title={title} message={message} />);
    expect(screen.getByText(title)).toBeInTheDocument();
    expect(screen.getByText(message)).toBeInTheDocument();
  });

  it('renders with custom retry text', () => {
    const retryText = 'Try Again';
    renderWithTheme(
      <ErrorMessage 
        message="Error message" 
        onRetry={() => {}}
        retryText={retryText}
      />
    );
    expect(screen.getByRole('button', { name: retryText })).toBeInTheDocument();
  });

  it('renders with custom styles', () => {
    const customStyle = { backgroundColor: '#ff0000' };
    renderWithTheme(
      <ErrorMessage 
        message="Error message" 
        style={customStyle}
      />
    );
    const alert = screen.getByRole('alert');
    expect(alert).toHaveStyle(customStyle);
  });

  it('renders with icon', () => {
    renderWithTheme(
      <ErrorMessage 
        message="Error message" 
        icon={<span data-testid="error-icon">⚠️</span>}
      />
    );
    expect(screen.getByTestId('error-icon')).toBeInTheDocument();
  });

  it('renders with custom className', () => {
    const className = 'custom-error-class';
    renderWithTheme(
      <ErrorMessage 
        message="Error message" 
        className={className}
      />
    );
    expect(screen.getByRole('alert')).toHaveClass(className);
  });

  it('renders with full width', () => {
    renderWithTheme(
      <ErrorMessage 
        message="Error message" 
        fullWidth
      />
    );
    expect(screen.getByRole('alert')).toHaveStyle({ width: '100%' });
  });
}); 
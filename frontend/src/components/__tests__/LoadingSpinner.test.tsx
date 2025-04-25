import React from 'react';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders without crashing', () => {
    render(<LoadingSpinner />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('has the correct role', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('applies custom size', () => {
    const customSize = '60px';
    render(<LoadingSpinner size={customSize} />);
    const spinner = screen.getByTestId('loading-spinner');
    expect(spinner).toHaveAttribute('data-testid', 'loading-spinner');
  });

  it('applies default size', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByTestId('loading-spinner');
    expect(spinner).toHaveAttribute('data-testid', 'loading-spinner');
  });
}); 
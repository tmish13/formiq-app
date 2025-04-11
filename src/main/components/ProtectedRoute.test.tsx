import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../context/AuthContext';
import ProtectedRoute from './ProtectedRoute';

// Mock the child component
const MockChildComponent = () => <div>Protected Content</div>;

describe('ProtectedRoute', () => {
  const renderProtectedRoute = (isAuthenticated = false) => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <ProtectedRoute isAuthenticated={isAuthenticated}>
            <MockChildComponent />
          </ProtectedRoute>
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('renders child component when authenticated', () => {
    renderProtectedRoute(true);
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    renderProtectedRoute(false);
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
}); 
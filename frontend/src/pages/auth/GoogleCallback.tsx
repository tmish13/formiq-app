import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { LoadingSpinner } from '../../components/atoms/LoadingSpinner';

export default function GoogleCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { socialLogin } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleGoogleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const error = searchParams.get('error');

        if (error) {
          setError(`Google authentication failed: ${error}`);
          setTimeout(() => navigate('/auth'), 3000);
          return;
        }

        if (!code) {
          setError('No authorization code received from Google');
          setTimeout(() => navigate('/auth'), 3000);
          return;
        }

        // In development mode with mock service, simulate successful OAuth
        if (process.env.NODE_ENV === 'development' && code === 'mock_google_code') {
          try {
            await socialLogin('google', 'mock_token_google');
            return;
          } catch (err) {
            console.error('Mock Google login failed:', err);
            setError('Google authentication failed. Please try again.');
            setTimeout(() => navigate('/auth'), 3000);
            return;
          }
        }

        // For production or real OAuth flow
        setError('Google OAuth flow not fully implemented. Please use email/password authentication.');
        setTimeout(() => navigate('/auth'), 3000);

      } catch (err) {
        console.error('Google callback error:', err);
        setError('Google authentication failed. Please try again.');
        setTimeout(() => navigate('/auth'), 3000);
      }
    };

    handleGoogleCallback();
  }, [searchParams, navigate, socialLogin]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-500 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentication Failed</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <p className="text-sm text-gray-500">Redirecting back to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <LoadingSpinner size="lg" />
        <h2 className="text-xl font-semibold text-gray-900 mt-4 mb-2">Completing Google Sign In</h2>
        <p className="text-gray-600">Please wait while we complete your authentication...</p>
      </div>
    </div>
  );
}
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { LoadingSpinner } from '../atoms/LoadingSpinner';
import apiService from '../../services/apiService';

export const ConfirmEmailVerification: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [isVerified, setIsVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(3);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  // Verify token on mount
  useEffect(() => {
    if (!token) {
      setError('Invalid verification link. Please request a new one.');
      setIsLoading(false);
      return;
    }

    apiService.verifyEmail(token)
      .then(() => {
        setIsVerified(true);
      })
      .catch((err: any) => {
        const detail = err?.response?.data?.detail || err?.message;
        if (detail?.toLowerCase().includes('expired')) {
          setError('This verification link has expired. Please request a new one.');
        } else if (detail?.toLowerCase().includes('already')) {
          setIsVerified(true); // already verified — treat as success
        } else {
          setError(detail || 'Verification failed. The link may be invalid or expired.');
        }
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [token]);

  // Auto-redirect countdown after successful verification
  useEffect(() => {
    if (!isVerified) return;
    if (countdown <= 0) {
      navigate('/auth', { replace: true });
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [isVerified, countdown, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <LoadingSpinner size="lg" />
              <p className="text-gray-600 dark:text-gray-400">Verifying your email…</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Verification Failed</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button onClick={() => navigate('/request-verification')} className="w-full">
              Resend Verification Email
            </Button>
            <Button variant="outline" onClick={() => navigate('/auth')} className="w-full">
              Back to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isVerified) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Email Verified!</CardTitle>
            <CardDescription>
              Your account is confirmed. Redirecting you to login in {countdown}…
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate('/auth', { replace: true })} className="w-full">
              Continue to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};

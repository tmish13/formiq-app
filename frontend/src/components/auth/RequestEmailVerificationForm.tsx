import React, { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import apiService from '../../services/apiService';

export const RequestEmailVerificationForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await apiService.requestEmailVerification(email);
      setIsSubmitted(true);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message;
      // Always show the success screen regardless — don't reveal whether the email exists
      if (detail?.toLowerCase().includes('rate') || detail?.toLowerCase().includes('too many')) {
        setError('Too many requests. Please wait a few minutes before trying again.');
      } else {
        setIsSubmitted(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Check Your Inbox</CardTitle>
            <CardDescription>
              If an account with <strong>{email}</strong> exists and needs verification, we've sent a link. Check your inbox (and spam folder).
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Resend Verification Email</CardTitle>
          <CardDescription>
            Enter your email address and we'll send you a new verification link.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Input
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>
            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={isLoading || !email.trim()}>
              {isLoading ? 'Sending...' : 'Send Verification Email'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

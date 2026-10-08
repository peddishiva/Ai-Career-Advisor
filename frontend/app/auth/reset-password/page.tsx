'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/auth-context';

export default function ResetPasswordPage() {
  const router = useRouter();
  const { configured, loading, user, isPasswordRecovery, updatePassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  // Inspect URL for recovery error parameters on client mount
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const searchParams = new URLSearchParams(window.location.search);
    const hash = window.location.hash.startsWith('#')
      ? window.location.hash.substring(1)
      : window.location.hash;
    const hashParams = new URLSearchParams(hash);

    const errorParam = searchParams.get('error') || hashParams.get('error');
    const errorCode = searchParams.get('error_code') || hashParams.get('error_code');
    const errorDesc = searchParams.get('error_description') || hashParams.get('error_description');

    if (errorParam || errorCode) {
      if (/expired/i.test(errorCode || '') || /expired/i.test(errorDesc || '')) {
        setUrlError('This password reset link has expired. Please request a new one.');
      } else {
        setUrlError('This password reset link is invalid or has expired. Please request a new one.');
      }
    }
  }, []);

  // State E: Recovery / session initialization still loading
  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-16 dark:bg-gray-950">
        <div className="flex flex-col items-center space-y-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Verifying recovery link...</p>
        </div>
      </main>
    );
  }

  // States B, C, D: Missing, expired, or invalid recovery link
  const hasValidRecoverySession = Boolean(user || isPasswordRecovery);
  const isInvalid = Boolean(urlError) || !hasValidRecoverySession;

  if (isInvalid && !success) {
    return (
      <main className="min-h-screen bg-gray-50 px-4 py-16 dark:bg-gray-950">
        <Card className="mx-auto max-w-md">
          <CardHeader>
            <CardTitle>Invalid or expired link</CardTitle>
            <CardDescription>
              {urlError || 'This password reset link is invalid or has expired.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              For your security, password reset links are time-limited and single-use. Please request a new recovery link.
            </p>
            <Button asChild className="w-full">
              <Link href="/auth/forgot-password">Request new reset link</Link>
            </Button>
            <p className="text-center text-sm text-gray-600 dark:text-gray-400">
              <Link className="text-blue-600 underline dark:text-blue-400" href="/auth/login">
                Back to Sign in
              </Link>
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  // State Success: Password reset successful
  if (success) {
    return (
      <main className="min-h-screen bg-gray-50 px-4 py-16 dark:bg-gray-950">
        <Card className="mx-auto max-w-md">
          <CardHeader>
            <CardTitle>Password updated successfully</CardTitle>
            <CardDescription>
              Your account password has been updated. You can now continue using AI Career Advisor.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className="rounded-md bg-green-50 p-4 text-sm text-green-800 dark:bg-green-950/40 dark:text-green-300"
              role="status"
            >
              Your new password is now active.
            </div>
            <div className="flex flex-col gap-2 pt-2">
              <Button onClick={() => router.push('/profile')} className="w-full">
                Continue to Profile
              </Button>
              <Button asChild variant="outline" className="w-full">
                <Link href="/dashboard">Go to Dashboard</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    );
  }

  // State A: Valid recovery session — render password form
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    if (!password) {
      setError('Please enter a new password.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    if (!confirmPassword) {
      setError('Please confirm your new password.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify and try again.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await updatePassword(password);
      if (result.error) {
        setError(result.error);
        setSubmitting(false);
      } else {
        setSuccess(true);
        setSubmitting(false);
      }
    } catch {
      setError('An unexpected error occurred while resetting your password. Please try again.');
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-16 dark:bg-gray-950">
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle>Set new password</CardTitle>
          <CardDescription>Create a new password for your account.</CardDescription>
        </CardHeader>
        <CardContent>
          {!configured && (
            <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              Authentication is not configured in this environment.
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium" htmlFor="reset-password">
                  New password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              <input
                id="reset-password"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'reset-error' : 'reset-password-hint'}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="At least 6 characters"
                minLength={6}
                required
              />
              <p id="reset-password-hint" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Minimum 6 characters.
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium" htmlFor="reset-confirm-password">
                  Confirm new password
                </label>
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                  aria-label={showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'}
                >
                  {showConfirmPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              <input
                id="reset-confirm-password"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirmPassword}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error || (confirmPassword && password !== confirmPassword))}
                aria-describedby={error ? 'reset-error' : undefined}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="Repeat your new password"
                minLength={6}
                required
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                  Passwords do not match yet.
                </p>
              )}
            </div>
            {error && (
              <p id="reset-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                {error}
              </p>
            )}
            <Button className="w-full" type="submit" disabled={!configured || submitting}>
              {submitting ? 'Updating password...' : 'Update password'}
            </Button>
            <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
              <Link className="text-blue-600 underline dark:text-blue-400" href="/auth/login">
                Back to Sign in
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

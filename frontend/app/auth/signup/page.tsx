'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/auth-context';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function SignupPage() {
  const router = useRouter();
  const { configured, loading, user, isPasswordRecovery, signUp } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) {
      if (isPasswordRecovery) {
        router.replace('/auth/reset-password');
      } else {
        router.replace('/dashboard');
      }
    }
  }, [isPasswordRecovery, loading, router, user]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-16 dark:bg-gray-950">
        <div className="flex flex-col items-center space-y-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading session...</p>
        </div>
      </main>
    );
  }

  if (user) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const trimmedName = displayName.trim();
    if (trimmedName.length > 200) {
      setError('Display name cannot exceed 200 characters.');
      return;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError('Please enter your email address.');
      return;
    }
    if (!EMAIL_REGEX.test(trimmedEmail)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setError('Please enter a password.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    if (!confirmPassword) {
      setError('Please confirm your password.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify and try again.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setMessage(null);

    try {
      const result = await signUp(trimmedEmail, password, trimmedName || undefined);
      if (result.error) {
        setError(result.error);
        setSubmitting(false);
      } else if (result.requiresEmailConfirmation) {
        setMessage('Account created! Please check your email to confirm your account, then sign in.');
        setSubmitting(false);
      } else {
        router.push('/dashboard');
      }
    } catch {
      setError('An unexpected error occurred while creating your account. Please try again.');
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-16 dark:bg-gray-950">
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle>Create an account</CardTitle>
          <CardDescription>Your authentication identity is managed securely by Supabase Auth.</CardDescription>
        </CardHeader>
        <CardContent>
          {!configured && (
            <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              Authentication is not configured in this environment.
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div>
              <label className="block text-sm font-medium" htmlFor="signup-name">
                Display name (optional)
              </label>
              <input
                id="signup-name"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type="text"
                autoComplete="name"
                value={displayName}
                maxLength={200}
                disabled={!configured || submitting}
                onChange={(event) => {
                  setDisplayName(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="How you'd like to be called"
              />
            </div>
            <div>
              <label className="block text-sm font-medium" htmlFor="signup-email">
                Email
              </label>
              <input
                id="signup-email"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type="email"
                autoComplete="email"
                value={email}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'signup-error' : undefined}
                onChange={(event) => {
                  setEmail(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="name@example.com"
                required
              />
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium" htmlFor="signup-password">
                  Password
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
                id="signup-password"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'signup-error' : 'password-hint'}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="At least 6 characters"
                required
                minLength={6}
              />
              <p id="password-hint" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Minimum 6 characters.
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium" htmlFor="signup-confirm-password">
                  Confirm password
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
                id="signup-confirm-password"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={confirmPassword}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error || (confirmPassword && password !== confirmPassword))}
                aria-describedby={error ? 'signup-error' : undefined}
                onChange={(event) => {
                  setConfirmPassword(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="Repeat your password"
                required
                minLength={6}
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                  Passwords do not match yet.
                </p>
              )}
            </div>
            {error && (
              <p id="signup-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                {error}
              </p>
            )}
            {message && (
              <p className="rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-950/40 dark:text-green-300" role="status">
                {message}
              </p>
            )}
            <Button className="w-full" type="submit" disabled={!configured || submitting}>
              {submitting ? 'Creating account...' : 'Create account'}
            </Button>
          </form>
          <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
            Already registered?{' '}
            <Link className="text-blue-600 underline dark:text-blue-400" href="/auth/login">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}

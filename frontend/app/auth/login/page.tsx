'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/auth-context';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const router = useRouter();
  const { configured, loading, user, isPasswordRecovery, signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
      setError('Please enter your password.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await signIn(trimmedEmail, password);
      if (result.error) {
        setError(result.error);
        setSubmitting(false);
      } else {
        router.push('/dashboard');
      }
    } catch {
      setError('An unexpected error occurred. Please try again.');
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-16 dark:bg-gray-950">
      <Card className="mx-auto max-w-md">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Access your AI Career Advisor profile.</CardDescription>
        </CardHeader>
        <CardContent>
          {!configured && (
            <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              Authentication is not configured in this environment.
            </p>
          )}
          <form className="space-y-4" onSubmit={handleSubmit} noValidate>
            <div>
              <label className="block text-sm font-medium" htmlFor="login-email">
                Email
              </label>
              <input
                id="login-email"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type="email"
                autoComplete="email"
                value={email}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'login-error' : undefined}
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
                <div className="flex items-center gap-2">
                  <label className="block text-sm font-medium" htmlFor="login-password">
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
                <Link
                  className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                  href="/auth/forgot-password"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="login-password"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                disabled={!configured || submitting}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'login-error' : undefined}
                onChange={(event) => {
                  setPassword(event.target.value);
                  if (error) setError(null);
                }}
                placeholder="Enter your password"
                required
              />
            </div>
            {error && (
              <p id="login-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                {error}
              </p>
            )}
            <Button className="w-full" type="submit" disabled={!configured || submitting}>
              {submitting ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>
          <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
            New here?{' '}
            <Link className="text-blue-600 underline dark:text-blue-400" href="/auth/signup">
              Create an account
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}

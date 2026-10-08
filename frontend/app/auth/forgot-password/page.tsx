'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/auth-context';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { configured, loading, user, isPasswordRecovery, resetPasswordForEmail } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

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

    setSubmitting(true);
    setError(null);

    try {
      const result = await resetPasswordForEmail(trimmedEmail);
      if (result.error) {
        setError(result.error);
        setSubmitting(false);
      } else {
        setSubmitted(true);
        setSubmitting(false);
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
          <CardTitle>Reset your password</CardTitle>
          <CardDescription>
            Enter your email address to receive password recovery instructions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!configured && (
            <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              Authentication is not configured in this environment.
            </p>
          )}

          {submitted ? (
            <div className="space-y-4">
              <div
                className="rounded-md bg-green-50 p-4 text-sm text-green-800 dark:bg-green-950/40 dark:text-green-300"
                role="status"
              >
                <p className="font-medium">Check your email</p>
                <p className="mt-1">
                  If an account exists for that email, we&apos;ve sent a password reset link. Please check your inbox and follow the link to reset your password.
                </p>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Didn&apos;t receive an email? Check your spam folder or{' '}
                <button
                  type="button"
                  onClick={() => {
                    setSubmitted(false);
                    setError(null);
                  }}
                  className="text-blue-600 underline dark:text-blue-400"
                >
                  try another email address
                </button>
                .
              </p>
              <div className="pt-2">
                <Button asChild className="w-full" variant="outline">
                  <Link href="/auth/login">Back to Sign in</Link>
                </Button>
              </div>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleSubmit} noValidate>
              <div>
                <label className="block text-sm font-medium" htmlFor="forgot-email">
                  Email
                </label>
                <input
                  id="forgot-email"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                  type="email"
                  autoComplete="email"
                  value={email}
                  disabled={!configured || submitting}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'forgot-error' : undefined}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="name@example.com"
                  required
                />
              </div>
              {error && (
                <p id="forgot-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                  {error}
                </p>
              )}
              <Button className="w-full" type="submit" disabled={!configured || submitting}>
                {submitting ? 'Sending reset link...' : 'Send reset link'}
              </Button>
              <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
                Remember your password?{' '}
                <Link className="text-blue-600 underline dark:text-blue-400" href="/auth/login">
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

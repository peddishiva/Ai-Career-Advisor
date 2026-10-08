'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiError, authenticatedApiRequest } from '@/lib/api/api-client';
import { useAuth } from '@/lib/auth/auth-context';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

type Profile = {
  user_id: string;
  display_name: string | null;
  created_at: string;
  updated_at: string;
};

function ProfileContent() {
  const router = useRouter();
  const { user, signOut, updatePassword } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [updatingPassword, setUpdatingPassword] = useState(false);

  useEffect(() => {
    if (!user) return;
    let active = true;
    void authenticatedApiRequest<Profile>('/api/v1/profile')
      .then((data) => {
        if (active) {
          setProfile(data);
          setDisplayName(data.display_name ?? ((user.user_metadata?.display_name as string) || ''));
        }
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace('/auth/login');
          return;
        }
        setError(requestError instanceof ApiError ? requestError.message : 'Unable to load your profile.');
      });
    return () => {
      active = false;
    };
  }, [router, user]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await authenticatedApiRequest<Profile>('/api/v1/profile', {
        method: 'PATCH',
        body: JSON.stringify({ display_name: displayName.trim() || null }),
      });
      setProfile(data);
      setDisplayName(data.display_name ?? '');
      setSuccess('Profile saved successfully.');
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        router.replace('/auth/login');
        return;
      }
      setError(requestError instanceof ApiError ? requestError.message : 'Unable to save your profile.');
    } finally {
      setSaving(false);
    }
  }

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (updatingPassword) return;

    if (!newPassword) {
      setPasswordError('Please enter a new password.');
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters long.');
      return;
    }
    if (!confirmPassword) {
      setPasswordError('Please confirm your new password.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match. Please verify and try again.');
      return;
    }

    setUpdatingPassword(true);
    setPasswordError(null);
    setPasswordSuccess(null);

    try {
      const result = await updatePassword(newPassword);
      if (result.error) {
        setPasswordError(result.error);
      } else {
        setPasswordSuccess('Password changed successfully.');
        setNewPassword('');
        setConfirmPassword('');
      }
    } catch {
      setPasswordError('Unable to update password. Please try again.');
    } finally {
      setUpdatingPassword(false);
    }
  }

  async function handleSignOut() {
    await signOut();
    router.replace('/auth/login');
  }

  if (!user) return null;

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-12 dark:bg-gray-950">
      <Card className="mx-auto max-w-xl">
        <CardHeader className="flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Your profile</CardTitle>
            <CardDescription>Profile data is scoped to your verified account identity.</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost" onClick={() => router.push('/')}>
              Home
            </Button>
            <Button type="button" variant="ghost" onClick={() => router.push('/dashboard')}>
              Dashboard
            </Button>
            <Button type="button" variant="outline" onClick={handleSignOut}>
              Sign out
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-6 space-y-3 rounded-lg border bg-gray-50/50 p-4 dark:bg-gray-900/50">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Account</h3>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Email</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{user.email ?? 'No email on record'}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">User ID</p>
              <p className="font-mono text-xs text-gray-600 dark:text-gray-400">{profile?.user_id ?? user.id}</p>
            </div>
          </div>
          <form className="space-y-4" onSubmit={handleSave}>
            <div>
              <label className="block text-sm font-medium" htmlFor="display-name">
                Display name
              </label>
              <input
                id="display-name"
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                value={displayName}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'profile-error' : undefined}
                onChange={(event) => {
                  setDisplayName(event.target.value);
                  if (success) setSuccess(null);
                }}
                maxLength={200}
                placeholder="Enter your display name"
              />
            </div>
            {error && (
              <p id="profile-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                {error}
              </p>
            )}
            {success && (
              <p className="text-sm text-green-600 dark:text-green-400" role="status">
                {success}
              </p>
            )}
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save profile'}
            </Button>
          </form>

          <div className="mt-8 border-t pt-6 dark:border-gray-800">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100">Change password</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Update your account password. Must be at least 6 characters long.
            </p>
            <form className="mt-4 space-y-4" onSubmit={handlePasswordChange}>
              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium" htmlFor="profile-new-password">
                    New password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                    aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                  >
                    {showNewPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
                <input
                  id="profile-new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                  value={newPassword}
                  disabled={updatingPassword}
                  aria-invalid={Boolean(passwordError)}
                  aria-describedby={passwordError ? 'change-password-error' : 'profile-password-hint'}
                  onChange={(event) => {
                    setNewPassword(event.target.value);
                    if (passwordSuccess) setPasswordSuccess(null);
                    if (passwordError) setPasswordError(null);
                  }}
                  placeholder="At least 6 characters"
                  minLength={6}
                  required
                />
                <p id="profile-password-hint" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Minimum 6 characters.
                </p>
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium" htmlFor="profile-confirm-password">
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
                  id="profile-confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="mt-1 w-full rounded-md border px-3 py-2 text-sm bg-white dark:bg-gray-900 dark:border-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-950"
                  value={confirmPassword}
                  disabled={updatingPassword}
                  aria-invalid={Boolean(passwordError || (confirmPassword && newPassword !== confirmPassword))}
                  aria-describedby={passwordError ? 'change-password-error' : undefined}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value);
                    if (passwordSuccess) setPasswordSuccess(null);
                    if (passwordError) setPasswordError(null);
                  }}
                  placeholder="Repeat your new password"
                  minLength={6}
                  required
                />
                {confirmPassword && newPassword !== confirmPassword && (
                  <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                    Passwords do not match yet.
                  </p>
                )}
              </div>
              {passwordError && (
                <p id="change-password-error" className="text-sm text-red-600 dark:text-red-400" role="alert">
                  {passwordError}
                </p>
              )}
              {passwordSuccess && (
                <p className="text-sm text-green-600 dark:text-green-400" role="status">
                  {passwordSuccess}
                </p>
              )}
              <Button type="submit" disabled={updatingPassword}>
                {updatingPassword ? 'Updating password...' : 'Update password'}
              </Button>
            </form>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}

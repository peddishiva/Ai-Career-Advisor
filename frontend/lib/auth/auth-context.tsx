'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { AuthChangeEvent, Session, User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';

export type AuthResult = {
  error: string | null;
  requiresEmailConfirmation?: boolean;
};

export type AuthContextValue = {
  configured: boolean;
  loading: boolean;
  isAuthenticated: boolean;
  session: Session | null;
  user: User | null;
  isPasswordRecovery: boolean;
  signIn: (email: string, password: string) => Promise<AuthResult>;
  login: (email: string, password: string) => Promise<AuthResult>;
  signUp: (email: string, password: string, displayName?: string) => Promise<AuthResult>;
  signup: (email: string, password: string, displayName?: string) => Promise<AuthResult>;
  signOut: () => Promise<AuthResult>;
  logout: () => Promise<AuthResult>;
  resetPasswordForEmail: (email: string) => Promise<AuthResult>;
  updatePassword: (password: string) => Promise<AuthResult>;
  clearPasswordRecovery: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function formatAuthError(error: { message: string } | null): string | null {
  if (!error) return null;
  const msg = error.message;
  if (/invalid login credentials/i.test(msg)) {
    return 'Invalid email or password. Please check your credentials and try again.';
  }
  if (/user already registered/i.test(msg) || /user already exists/i.test(msg)) {
    return 'An account with this email already exists. Please sign in instead.';
  }
  if (/rate limit/i.test(msg) || /over_email_send_rate_limit/i.test(msg)) {
    return 'Too many attempts. Please wait a few moments before trying again.';
  }
  if (/email not confirmed/i.test(msg)) {
    return 'Please verify your email address before signing in.';
  }
  if (/password.*(short|least)/i.test(msg) || /password should be at least/i.test(msg)) {
    return 'Password must be at least 6 characters long.';
  }
  if (/same_password|same as/i.test(msg)) {
    return 'New password should be different from your old password.';
  }
  if (/token.*expired|otp.*expired|invalid.*token|token.*invalid/i.test(msg)) {
    return 'This password reset link is invalid or has expired. Please request a new one.';
  }
  if (/invalid.*email/i.test(msg)) {
    return 'Please enter a valid email address.';
  }
  if (/signup.*disabled/i.test(msg)) {
    return 'Signups are currently disabled. Please contact support.';
  }
  if (/session.*expired|jwt.*expired/i.test(msg)) {
    return 'Your session has expired. Please sign in again.';
  }
  if (/network|failed to fetch/i.test(msg)) {
    return "We couldn't complete the request. Please check your connection and try again.";
  }
  // Sanitize any remaining error containing technical identifiers or database details
  if (/token|jwt|supabase|postgres|database|internal|http|50\d/i.test(msg)) {
    return 'An authentication error occurred. Please try again.';
  }
  return msg;
}

export const ACCOUNT_STORAGE_KEYS = [
  'resumeAnalysis',
  'resumeFileId',
  'savedJobs',
  'jobAlerts',
  'jobSearchQuery',
  'jdxrSessionId',
  'jdxrResult',
] as const;

export function clearUserAccountStorage(): void {
  if (typeof window === 'undefined') return;
  try {
    for (const key of ACCOUNT_STORAGE_KEYS) {
      localStorage.removeItem(key);
    }
  } catch (err) {
    console.error('Failed to clear user account storage:', err);
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPasswordRecovery, setIsPasswordRecovery] = useState(false);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return undefined;
    }

    let mounted = true;

    // Detect recovery in hash if present on initial mount
    if (typeof window !== 'undefined') {
      const hash = window.location.hash;
      if (hash && (hash.includes('type=recovery') || hash.includes('type%3Drecovery'))) {
        setIsPasswordRecovery(true);
      }
    }

    // Retrieve initial session on startup
    void supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (!mounted) return;
        if (error) {
          setSession(null);
        } else {
          setSession(data.session);
        }
        setLoading(false);
      })
      .catch(() => {
        if (mounted) {
          setSession(null);
          setLoading(false);
        }
      });

    // Synchronize auth state changes (INITIAL_SESSION, SIGNED_IN, SIGNED_OUT, TOKEN_REFRESHED, USER_UPDATED, PASSWORD_RECOVERY)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, nextSession: Session | null) => {
      if (!mounted) return;
      switch (event) {
        case 'PASSWORD_RECOVERY':
          setIsPasswordRecovery(true);
          setSession(nextSession);
          setLoading(false);
          break;
        case 'SIGNED_IN':
          if (typeof window !== 'undefined') {
            const nextUserId = nextSession?.user?.id;
            const previousUserId = sessionStorage.getItem('current_auth_user_id');
            if (previousUserId && nextUserId && previousUserId !== nextUserId) {
              // Account switched! Purge cached storage from previous account
              clearUserAccountStorage();
            } else if (!previousUserId && nextUserId) {
              // Transitioned from anonymous to authenticated user!
              // Purge anonymous scratch resume so it does not leak into the authenticated account
              localStorage.removeItem('resumeAnalysis');
              localStorage.removeItem('resumeFileId');
            }
            if (nextUserId) {
              sessionStorage.setItem('current_auth_user_id', nextUserId);
            }
          }
          setSession(nextSession);
          setLoading(false);
          break;
        case 'INITIAL_SESSION':
          if (typeof window !== 'undefined') {
            const nextUserId = nextSession?.user?.id;
            const previousUserId = sessionStorage.getItem('current_auth_user_id');
            if (previousUserId && nextUserId && previousUserId !== nextUserId) {
              // Account switched in another tab/context
              clearUserAccountStorage();
            }
            if (nextUserId) {
              sessionStorage.setItem('current_auth_user_id', nextUserId);
            }
          }
          setSession(nextSession);
          setLoading(false);
          break;
        case 'TOKEN_REFRESHED':
        case 'USER_UPDATED':
          setSession(nextSession);
          setLoading(false);
          break;
        case 'SIGNED_OUT':
          clearUserAccountStorage();
          if (typeof window !== 'undefined') {
            sessionStorage.removeItem('current_auth_user_id');
          }
          setSession(null);
          setIsPasswordRecovery(false);
          setLoading(false);
          break;
        default:
          setSession(nextSession);
          setLoading(false);
          break;
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signIn = async (email: string, password: string): Promise<AuthResult> => {
    if (!supabase) return { error: 'Authentication is not configured for this environment.' };
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      return { error: formatAuthError(error) };
    }
    setSession(data.session);
    return { error: null };
  };

  const signUp = async (email: string, password: string, displayName?: string): Promise<AuthResult> => {
    if (!supabase) return { error: 'Authentication is not configured for this environment.' };
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: displayName ? { data: { display_name: displayName } } : undefined,
    });
    if (error) {
      return { error: formatAuthError(error) };
    }
    if (data.session) {
      setSession(data.session);
    }
    return {
      error: null,
      requiresEmailConfirmation: !data.session,
    };
  };

  const signOut = async (): Promise<AuthResult> => {
    if (!supabase) return { error: 'Authentication is not configured for this environment.' };
    clearUserAccountStorage();
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('current_auth_user_id');
    }
    const { error } = await supabase.auth.signOut();
    setSession(null);
    setIsPasswordRecovery(false);
    return { error: error ? formatAuthError(error) : null };
  };

  const resetPasswordForEmail = async (email: string): Promise<AuthResult> => {
    if (!supabase) return { error: 'Authentication is not configured for this environment.' };
    try {
      const siteUrl =
        process.env.NEXT_PUBLIC_SITE_URL ||
        (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');
      const redirectTo = `${siteUrl.replace(/\/$/, '')}/auth/reset-password`;
      const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
      if (error) {
        // Enforce account enumeration protection by hiding "user not found" errors
        if (/not found/i.test(error.message) || /user.*not/i.test(error.message)) {
          return { error: null };
        }
        return { error: formatAuthError(error) };
      }
      return { error: null };
    } catch {
      return { error: "We couldn't complete the request. Please check your connection and try again." };
    }
  };

  const updatePassword = async (password: string): Promise<AuthResult> => {
    if (!supabase) return { error: 'Authentication is not configured for this environment.' };
    try {
      const { error } = await supabase.auth.updateUser({ password });
      if (error) {
        return { error: formatAuthError(error) };
      }
      setIsPasswordRecovery(false);
      return { error: null };
    } catch {
      return { error: "We couldn't complete the request. Please check your connection and try again." };
    }
  };

  const clearPasswordRecovery = () => {
    setIsPasswordRecovery(false);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      configured: Boolean(supabase),
      loading,
      isAuthenticated: Boolean(session?.user),
      session,
      user: session?.user ?? null,
      isPasswordRecovery,
      signIn,
      login: signIn,
      signUp,
      signup: signUp,
      signOut,
      logout: signOut,
      resetPasswordForEmail,
      updatePassword,
      clearPasswordRecovery,
    }),
    [isPasswordRecovery, loading, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}

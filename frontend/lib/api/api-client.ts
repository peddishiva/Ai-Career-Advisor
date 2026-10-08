import { supabase } from '@/lib/supabase';

const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function authenticatedApiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!supabase) {
    throw new ApiError(503, 'Authentication is not configured for this environment.');
  }

  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw new ApiError(401, 'Unable to retrieve your authentication session.');
  }

  const accessToken = data.session?.access_token;
  if (!accessToken) {
    throw new ApiError(401, 'Please sign in to continue.');
  }

  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${accessToken}`);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${apiUrl}${path}`, { ...init, headers });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError(401, 'Your session has expired. Please sign in again.');
    }
    const message =
      typeof payload.detail === 'string'
        ? payload.detail
        : 'The request could not be completed.';
    throw new ApiError(response.status, message);
  }

  return payload as T;
}

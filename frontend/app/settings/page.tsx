'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SettingsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/profile');
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 text-center text-sm text-gray-500 dark:bg-gray-950 dark:text-gray-400">
      <p>Redirecting to profile...</p>
    </main>
  );
}

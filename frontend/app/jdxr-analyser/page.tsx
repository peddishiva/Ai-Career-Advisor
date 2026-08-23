'use client';

import { useRouter } from 'next/navigation';
import { BookOpen } from 'lucide-react';

import { Button } from '@/components/ui/button';
import JdxrAnalyser from '@/components/jdxr-analyser';

export default function JdxrAnalyserPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950">
      <nav className="border-b border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <button
            type="button"
            className="flex items-center hover:opacity-80"
            onClick={() => router.push('/')}
            aria-label="Go to home"
          >
            <BookOpen className="h-8 w-8 text-blue-600 dark:text-blue-500" />
            <span className="ml-2 text-xl font-semibold text-gray-900 dark:text-white">AI Career Advisor</span>
          </button>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => router.push('/analysis')}>
              Analysis
            </Button>
            <Button variant="ghost" onClick={() => router.push('/job-recommendation')}>
              Job Recommendations
            </Button>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <JdxrAnalyser />
      </main>
    </div>
  );
}

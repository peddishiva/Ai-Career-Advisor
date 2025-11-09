'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestRedirectPage() {
  const router = useRouter();

  const testRedirect = () => {
    console.log('Testing redirect to /analysis...');
    router.push('/analysis');
  };

  const testRedirectWithDelay = () => {
    console.log('Testing redirect with 1 second delay...');
    setTimeout(() => {
      console.log('Redirecting now...');
      router.push('/analysis');
    }, 1000);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Test Redirect Functionality</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Use these buttons to test if the redirect to /analysis page works.
          </p>
          
          <Button 
            onClick={testRedirect}
            className="w-full"
          >
            Test Immediate Redirect
          </Button>

          <Button 
            onClick={testRedirectWithDelay}
            variant="outline"
            className="w-full"
          >
            Test Redirect with 1s Delay
          </Button>

          <Button 
            onClick={() => router.push('/')}
            variant="ghost"
            className="w-full"
          >
            Back to Home
          </Button>

          <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm">
            <p className="font-semibold mb-2">Instructions:</p>
            <ol className="list-decimal list-inside space-y-1 text-gray-700 dark:text-gray-300">
              <li>Open browser console (F12)</li>
              <li>Click one of the buttons above</li>
              <li>Check if you&apos;re redirected to /analysis</li>
              <li>Check console for any errors</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

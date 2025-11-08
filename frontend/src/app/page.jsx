'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { FileText, ArrowRight } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero Section */}
      <div className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <div className="flex items-center justify-center h-16 w-16 rounded-full bg-primary/10">
              <FileText className="h-8 w-8 text-primary" />
            </div>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-foreground">
            AI-Powered Resume Analysis
          </h1>
          <p className="mt-6 text-xl text-muted-foreground">
            Get instant feedback on your resume and improve your chances of landing your dream job.
            Our AI analyzes your resume and provides actionable insights to make it stand out.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" asChild>
              <Link href="/dashboard" className="gap-2">
                Go to Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-muted/50 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground">How It Works</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Get started in minutes with our simple three-step process
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: 'Upload Your Resume',
                description: 'Easily upload your resume in PDF format for analysis.',
                icon: '📄',
              },
              {
                title: 'Get Instant Analysis',
                description: 'Our AI reviews your resume and provides detailed feedback.',
                icon: '🤖',
              },
              {
                title: 'Improve & Succeed',
                description: 'Use our recommendations to enhance your resume and land more interviews.',
                icon: '🚀',
              },
            ].map((feature, index) => (
              <div key={index} className="bg-background p-6 rounded-lg shadow-sm">
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-primary/5 py-16">
        <div className="max-w-3xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-foreground">Ready to improve your resume?</h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Join thousands of job seekers who have improved their resumes with our AI-powered analysis.
          </p>
          <div className="mt-8">
            <Button size="lg" asChild>
              <Link href="/dashboard" className="gap-2">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

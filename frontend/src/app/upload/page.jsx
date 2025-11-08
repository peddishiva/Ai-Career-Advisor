'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { FileUp, UploadCloud, Loader2, ArrowRight } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import Link from 'next/link';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const router = useRouter();
  const { toast } = useToast();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a PDF file.',
        variant: 'destructive',
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      toast({
        title: 'No file selected',
        description: 'Please select a file to upload.',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('resume', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Upload failed');
      }

      // Show success message
      toast({
        title: 'Success!',
        description: 'Your resume has been analyzed successfully!',
      });

      // Redirect to dashboard with the analysis ID
      router.push(`/dashboard?analysisId=${data.analysisId}`);

    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: 'Upload failed',
        description: error.message || 'There was an error uploading your resume. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-12 max-w-3xl">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold mb-2">Upload Your Resume</h1>
        <p className="text-muted-foreground">
          Get instant feedback on your resume from our AI career advisor
        </p>
      </div>

      <div className="bg-card rounded-lg border border-border p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors hover:border-primary/50 ${
              file ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                const selectedFile = e.dataTransfer.files[0];
                if (selectedFile.type === 'application/pdf') {
                  setFile(selectedFile);
                } else {
                  toast({
                    title: 'Invalid file type',
                    description: 'Please upload a PDF file.',
                    variant: 'destructive',
                  });
                }
              }
            }}
            onClick={() => document.getElementById('resume-upload').click()}
          >
            <input
              type="file"
              id="resume-upload"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            {file ? (
              <div className="space-y-2">
                <FileUp className="mx-auto h-12 w-12 text-primary" />
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB • {file.type}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  disabled={isUploading}
                >
                  Change File
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <UploadCloud className="mx-auto h-12 w-12 text-muted-foreground" />
                <p className="font-medium">Drag and drop your resume here</p>
                <p className="text-sm text-muted-foreground">
                  or click to browse files (PDF only, max 5MB)
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-2">
            <p className="text-sm text-muted-foreground text-center sm:text-left">
              Already uploaded?{' '}
              <Link 
                href="/dashboard" 
                className="text-primary hover:underline font-medium"
              >
                View your dashboard <ArrowRight className="inline h-4 w-4" />
              </Link>
            </p>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/dashboard')}
                disabled={isUploading}
                className="flex-1 sm:flex-none"
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={!file || isUploading}
                className="flex-1 sm:flex-none"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze Resume'
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>

      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {[
          {
            title: 'AI-Powered Analysis',
            description: 'Get detailed feedback on your resume from our advanced AI system.',
            icon: '🤖',
          },
          {
            title: 'Instant Results',
            description: 'Receive your analysis in seconds, not days.',
            icon: '⚡',
          },
          {
            title: 'Actionable Insights',
            description: 'Clear recommendations to improve your resume and land more interviews.',
            icon: '🎯',
          },
        ].map((feature, index) => (
          <div key={index} className="bg-muted/50 p-6 rounded-lg">
            <div className="text-3xl mb-3">{feature.icon}</div>
            <h3 className="font-semibold mb-1">{feature.title}</h3>
            <p className="text-sm text-muted-foreground">{feature.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

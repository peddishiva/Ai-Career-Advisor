'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUp, Upload, FileText, BarChart3, Lightbulb, BookOpen, X, Moon, Sun } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { useTheme } from 'next-themes';
import { useAuth } from '@/lib/auth/auth-context';

export default function Home() {
  const router = useRouter();
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();
  const { user, signOut } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const uploadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.location.hash === '#upload') {
      uploadRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      // Check file type (PDF or DOCX) - support MIME types and filename extension fallback
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      const validExtensions = ['.pdf', '.docx'];
      const hasValidExt = validExtensions.some((ext) => selectedFile.name.toLowerCase().endsWith(ext));
      if (!validTypes.includes(selectedFile.type) && !hasValidExt) {
        toast({
          title: 'Invalid file type',
          description: 'Please upload a PDF or DOCX file',
          variant: 'destructive',
        });
        return;
      }
      
      // Check file size (5MB max)
      const maxSize = 5 * 1024 * 1024; // 5MB
      if (selectedFile.size > maxSize) {
        toast({
          title: 'File too large',
          description: 'Maximum file size is 5MB',
          variant: 'destructive',
        });
        return;
      }
      
      setFile(selectedFile);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  const removeFile = () => {
    setFile(null);
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    
    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', file);

      console.log('Uploading file to backend...');
      
      // Upload to Python backend (use environment variable for production)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      const response = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      console.log('Response status:', response.status);
      
      const data = await response.json();

      if (!response.ok) {
        const validationMessage = data.validation?.message || data.message;
        const detailMessage = typeof data.detail === 'string' ? data.detail : data.detail?.message;
        const error = new Error(validationMessage || detailMessage || 'Upload failed');
        (error as Error & { validationError?: boolean }).validationError = data.error === 'resume_validation_failed';
        throw error;
      }
      
      toast({
        title: 'Upload successful!',
        description: 'Your resume has been analyzed successfully.',
      });
      
      // Store analysis data in localStorage for the analysis page
      if (data.analysis) {
        localStorage.setItem('resumeAnalysis', JSON.stringify(sanitizeAnalysisForStorage(data.analysis)));
        if (data.file_id) {
          localStorage.setItem('resumeFileId', data.file_id);
        } else {
          localStorage.removeItem('resumeFileId');
        }
        console.log('Analysis data stored in localStorage');
      }
      
      // Reset file
      setFile(null);
      
      console.log('Redirecting to analysis page...');
      
      // Redirect to analysis page after short delay
      setTimeout(() => {
        router.push('/analysis');
      }, 1000);
      
    } catch (error) {
      console.error('Upload error:', error);
      
      // Check if it's a network error (backend not running)
      if (error instanceof TypeError && error.message.includes('fetch')) {
        toast({
          title: 'Backend not running',
          description: 'Please start the Python backend server first. Run: cd backend && python main.py',
          variant: 'destructive',
        });
      } else if ((error as Error & { validationError?: boolean }).validationError) {
        toast({
          title: "This file doesn't appear to be a resume.",
          description: error instanceof Error ? error.message : 'Please upload a resume containing your education, experience, projects, skills, or certifications.',
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Upload failed',
          description: error instanceof Error ? error.message : 'There was an error uploading your resume. Please try again.',
          variant: 'destructive',
        });
      }
    } finally {
      setIsUploading(false);
    }
  };

  const scrollToUpload = () => {
    uploadRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950">
      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div 
              className="flex items-center cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => router.push('/')}
            >
              <BookOpen className="h-8 w-8 text-blue-600 dark:text-blue-500" />
              <span className="ml-2 text-xl font-semibold text-gray-900 dark:text-white">AI Career Advisor</span>
            </div>
            <div className="flex items-center space-x-2">
              <Button 
                variant="ghost" 
                size="icon" 
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <Sun className="h-5 w-5" />
                ) : (
                  <Moon className="h-5 w-5" />
                )}
              </Button>
              <Button 
                variant="ghost" 
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => router.push('/job-recommendation')}
              >
                Job Recommendations
              </Button>
              <Button 
                variant="ghost" 
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => router.push('/analysis')}
              >
                Analysis
              </Button>
              <Button
                variant="ghost"
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => router.push('/jdxr-analyser')}
              >
                Compare with JD
              </Button>
              {user ? (
                <>
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    onClick={() => router.push('/dashboard')}
                  >
                    Dashboard
                  </Button>
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    onClick={() => router.push('/profile')}
                  >
                    Profile
                  </Button>
                  <Button
                    variant="outline"
                    className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    onClick={async () => {
                      await signOut();
                      router.push('/auth/login');
                    }}
                  >
                    Sign Out
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                    onClick={() => router.push('/auth/login')}
                  >
                    Sign In
                  </Button>
                  <Button
                    className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800"
                    onClick={() => router.push('/auth/signup')}
                  >
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-6">
          AI-Powered Career Guidance <br />
          <span className="text-blue-600 dark:text-blue-400">For Your Future Success</span>
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 mb-10 max-w-3xl mx-auto">
          Get personalized career recommendations based on your skills, interests, and goals with our advanced AI technology.
        </p>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
          {user ? (
            <Button
              size="lg"
              className="bg-blue-600 hover:bg-blue-700 text-lg h-12 px-8"
              onClick={() => router.push('/dashboard')}
            >
              Continue to Dashboard
            </Button>
          ) : (
            <Button
              size="lg"
              className="bg-blue-600 hover:bg-blue-700 text-lg h-12 px-8"
              onClick={() => router.push('/auth/signup')}
            >
              Get Started
            </Button>
          )}
          <Button
            size="lg"
            variant="outline"
            className="text-lg h-12 px-8"
            onClick={scrollToUpload}
          >
            <Upload className="mr-2 h-5 w-5" /> Upload Your Resume
          </Button>
          <Button
            size="lg"
            variant="outline"
            className="text-lg h-12 px-8"
            onClick={() => router.push('/jdxr-analyser')}
          >
            <FileText className="mr-2 h-5 w-5" /> Compare Resume with JD
          </Button>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-white dark:bg-gray-900 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">How It Works</h2>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              Our AI analyzes your profile to provide personalized career guidance and recommendations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                icon: <FileText className="h-10 w-10 text-blue-600 mb-4" />,
                title: "Upload Your Resume",
                description: "Easily upload your resume or fill in your details manually.",
                onClick: () => scrollToUpload()
              },
              {
                icon: <BarChart3 className="h-10 w-10 text-blue-600 mb-4" />,
                title: "Get AI Analysis",
                description: "Our AI analyzes your skills, experience, and preferences.",
                onClick: () => router.push('/analysis')
              },
              {
                icon: <Lightbulb className="h-10 w-10 text-blue-600 mb-4" />,
                title: "Receive Recommendations",
                description: "Get personalized career paths and skill development suggestions.",
                onClick: () => router.push('/job-recommendation')
              }
            ].map((feature, index) => (
              <Card 
                key={index} 
                className="p-6 text-center hover:shadow-lg transition-all cursor-pointer hover:scale-105 dark:bg-gray-800 dark:border-gray-700"
                onClick={feature.onClick}
              >
                <div className="flex justify-center">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">{feature.title}</h3>
                <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-blue-600 dark:bg-blue-900 text-white py-16">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold mb-6">Ready to Transform Your Career?</h2>
          <p className="text-xl mb-8 text-blue-100 dark:text-blue-200">
            Join thousands of professionals who have discovered their ideal career paths with our AI-powered platform.
          </p>
          <Button 
            size="lg" 
            className="bg-white text-blue-600 hover:bg-blue-50 text-lg h-12 px-8"
            onClick={() => router.push('/search')}
          >
            Start Searching
          </Button>
        </div>
      </div>

      {/* Upload Resume Section */}
      <div id="upload" ref={uploadRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Card className="w-full max-w-2xl mx-auto dark:bg-gray-800 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-2xl dark:text-white">Upload Your Resume</CardTitle>
            <CardDescription className="dark:text-gray-300">
              Upload your resume (PDF or DOCX) to get personalized career advice and skill analysis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div 
              {...getRootProps()} 
              className={`flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
                isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'
              }`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="text-center">
                  <div className="flex items-center justify-center space-x-2 mb-4">
                    <FileText className="w-8 h-8 text-blue-600" />
                    <span className="font-medium text-gray-900">{file.name}</span>
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile();
                      }}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                      aria-label="Remove file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-sm text-gray-500 mb-4">
                    {(file.size / 1024 / 1024).toFixed(2)} MB • {file.type.split('/')[1].toUpperCase()}
                  </p>
                  <Button 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUpload();
                    }}
                    disabled={isUploading}
                    className="mt-2"
                  >
                    {isUploading ? 'Uploading...' : 'Upload Resume'}
                  </Button>
                </div>
              ) : (
                <div className="text-center">
                  <FileUp className="w-12 h-12 mb-4 text-gray-400 mx-auto" />
                  <p className="text-gray-600 mb-1">
                    {isDragActive ? 'Drop the file here' : 'Drag and drop your resume here, or click to browse'}
                  </p>
                  <p className="text-sm text-gray-500">PDF or DOCX (max. 5MB)</p>
                </div>
              )}
            </div>
            {!file && (
              <div className="mt-4 text-center">
                <p className="text-xs text-gray-500">
                  By uploading your resume, you agree to our Terms of Service and Privacy Policy.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">AI Career Advisor</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Empowering your career journey with deterministic skill analysis and AI-driven career guidance.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Platform</h4>
              <ul className="space-y-2 text-sm">
                <li>
                  <button
                    type="button"
                    onClick={() => router.push('/analysis')}
                    className="text-gray-400 hover:text-white transition-colors text-left"
                  >
                    Resume Analysis
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => router.push('/job-recommendation')}
                    className="text-gray-400 hover:text-white transition-colors text-left"
                  >
                    Job Recommendations
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={() => router.push('/jdxr-analyser')}
                    className="text-gray-400 hover:text-white transition-colors text-left"
                  >
                    Compare with JD
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    onClick={scrollToUpload}
                    className="text-gray-400 hover:text-white transition-colors text-left"
                  >
                    Upload Resume
                  </button>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Resources</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <span>Career Guides</span>
                  <span className="text-[10px] text-gray-400 rounded bg-gray-800 px-1.5 py-0.5">Coming Soon</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>Resume Tips</span>
                  <span className="text-[10px] text-gray-400 rounded bg-gray-800 px-1.5 py-0.5">Coming Soon</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>Interview Prep</span>
                  <span className="text-[10px] text-gray-400 rounded bg-gray-800 px-1.5 py-0.5">Coming Soon</span>
                </li>
                <li className="flex items-center gap-2">
                  <span>Skill Benchmarks</span>
                  <span className="text-[10px] text-gray-400 rounded bg-gray-800 px-1.5 py-0.5">Coming Soon</span>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">About</h4>
              <p className="text-sm text-gray-400 leading-relaxed">
                Built with FastAPI and Next.js, AI Career Advisor provides private, deterministic resume parsing and intelligent career matching.
              </p>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-400 text-sm">
            <p>© {new Date().getFullYear()} AI Career Advisor. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function sanitizeAnalysisForStorage(analysis: any) {
  if (!analysis || typeof analysis !== 'object') return analysis;
  const candidateInfo = analysis.candidate_info && typeof analysis.candidate_info === 'object'
    ? analysis.candidate_info
    : {};
  const { name: _name, email: _email, phone: _phone, ...safeCandidateInfo } = candidateInfo;
  return { ...analysis, candidate_info: safeCandidateInfo };
}

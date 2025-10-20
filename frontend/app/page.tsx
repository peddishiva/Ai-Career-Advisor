'use client';

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUp, Upload, FileText, BarChart3, Lightbulb, BookOpen, X, Moon, Sun } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { useTheme } from 'next-themes';

export default function Home() {
  const router = useRouter();
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const uploadRef = useRef<HTMLDivElement>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      // Check file type (PDF or DOCX)
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!validTypes.includes(selectedFile.type)) {
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
      formData.append('resume', file);

      // Here you would typically send the file to your backend
      // For now, we'll just simulate an API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      toast({
        title: 'Upload successful!',
        description: 'Your resume has been uploaded successfully.',
      });
      
      // Reset after successful upload
      setFile(null);
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: 'Upload failed',
        description: 'There was an error uploading your resume. Please try again.',
        variant: 'destructive',
      });
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
            <div className="flex items-center">
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
                onClick={() => router.push('/settings')}
              >
                Profile
              </Button>
              <Button 
                className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-800"
                onClick={() => router.push('/search')}
              >
                Search
              </Button>
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
          <Button 
            size="lg" 
            className="bg-blue-600 hover:bg-blue-700 text-lg h-12 px-8"
            onClick={scrollToUpload}
          >
            <Upload className="mr-2 h-5 w-5" /> Upload Your Resume
          </Button>
          <Button 
            size="lg" 
            variant="outline" 
            className="text-lg h-12 px-8"
            onClick={() => router.push('/search')}
          >
            Search
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
                description: "Easily upload your resume or fill in your details manually."
              },
              {
                icon: <BarChart3 className="h-10 w-10 text-blue-600 mb-4" />,
                title: "Get AI Analysis",
                description: "Our AI analyzes your skills, experience, and preferences."
              },
              {
                icon: <Lightbulb className="h-10 w-10 text-blue-600 mb-4" />,
                title: "Receive Recommendations",
                description: "Get personalized career paths and skill development suggestions."
              }
            ].map((feature, index) => (
              <Card key={index} className="p-6 text-center hover:shadow-lg transition-shadow dark:bg-gray-800 dark:border-gray-700">
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
      <div ref={uploadRef} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
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
              <p className="text-gray-400">Empowering your career journey with AI-driven insights and guidance.</p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2">
                {['About Us', 'Careers', 'Blog', 'Contact'].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-gray-400 hover:text-white">{item}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Resources</h4>
              <ul className="space-y-2">
                {['Career Guides', 'Resume Tips', 'Interview Prep', 'Skill Assessment'].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-gray-400 hover:text-white">{item}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Connect</h4>
              <div className="flex space-x-4">
                {['Twitter', 'LinkedIn', 'Facebook', 'Instagram'].map((social) => (
                  <a key={social} href="#" className="text-gray-400 hover:text-white">
                    <span className="sr-only">{social}</span>
                    <span className="h-6 w-6">{social[0]}</span>
                  </a>
                ))}
              </div>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-12 pt-8 text-center text-gray-400">
            <p>© {new Date().getFullYear()} AI Career Advisor. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

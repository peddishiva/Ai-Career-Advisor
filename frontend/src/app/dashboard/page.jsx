'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { FileText, Upload as UploadIcon, BarChart2, LogOut, History } from 'lucide-react';
import { CalendarDays } from '@/components/ui/calendar-days';
import { formatDistanceToNow } from 'date-fns';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import UploadResumeModal from './components/UploadResumeModal';
import ResumeHistory from './components/ResumeHistory';
import AnalysisResults from './components/AnalysisResults';
import Recommendations from './components/Recommendations';

export default function DashboardPage() {
  const [userData, setUserData] = useState({
    name: 'John Doe',
    email: 'john.doe@example.com',
    profileCompletion: 75,
    lastUpdated: new Date().toISOString(),
    resumeHistory: [],
    analysis: {
      skills: [],
      experience: '',
      education: '',
      score: 0
    },
    recommendations: []
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  const router = useRouter();
  const { toast } = useToast();

  // Handle logout
  const handleLogout = () => {
    // Clear the auth cookie
    document.cookie = 'auth-token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    // Redirect to login page
    router.push('/login');
  };

  const handleUploadSuccess = async (uploadData) => {
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('resume', uploadData.file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to upload resume');
      }

      const result = await response.json();
      
      // Update the UI with the new resume data
      setUserData(prev => ({
        ...prev,
        resumeHistory: [
          {
            id: result.analysisId,
            name: uploadData.file.name,
            date: new Date().toISOString(),
            score: result.score || 0,
          },
          ...(prev.resumeHistory || [])
        ].slice(0, 5)
      }));

      toast({
        title: 'Success',
        description: 'Resume uploaded and analyzed successfully!',
      });
    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload resume',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      setIsUploadModalOpen(false);
    }
  };

  // Load initial data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // TODO: Replace with actual API call
        // const response = await fetch('/api/user/dashboard');
        // const data = await response.json();
        
        // Mock data for demonstration
        const mockUserData = {
          name: 'John Doe',
          email: 'john.doe@example.com',
          profileCompletion: 75,
          lastUpdated: new Date().toISOString(),
          resumeHistory: [
            { id: 1, name: 'Senior_Developer_Resume.pdf', date: new Date().toISOString(), score: 85 },
            { id: 2, name: 'Updated_Resume.pdf', date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), score: 78 },
            { id: 3, name: 'First_Resume.pdf', date: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(), score: 65 },
          ],
          analysis: {
            skills: ['JavaScript', 'React', 'Node.js', 'Python', 'AWS'],
            experience: '5+ years',
            education: 'BSc in Computer Science',
            strengths: ['Problem Solving', 'Team Leadership', 'Project Management'],
            areasForImprovement: ['Cloud Architecture', 'Machine Learning'],
            score: 85
          },
          recommendations: [
            'Consider obtaining AWS Certification',
            'Learn more about containerization with Docker',
            'Improve your machine learning skills',
            'Add more quantifiable achievements to your resume'
          ]
        };
        
        setUserData(mockUserData);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        toast({
          title: 'Error',
          description: 'Failed to load dashboard data. Please try again.',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, [toast]);

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="grid gap-6">
          <Skeleton className="h-12 w-full" />
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-6">
      {/* Upload Resume Modal */}
      <UploadResumeModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      <div className="flex flex-col space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold">Welcome back, {userData.name}!</h1>
            <p className="text-muted-foreground">Here's what's happening with your career profile</p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 w-full md:w-auto">
            <Button 
              onClick={() => setIsUploadModalOpen(true)}
              className="gap-2 w-full sm:w-auto"
              disabled={isUploading}
            >
              <UploadIcon className="h-4 w-4" />
              {isUploading ? 'Uploading...' : 'Upload Resume'}
            </Button>
            <Button 
              variant="outline" 
              onClick={handleLogout}
              className="w-full sm:w-auto"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Profile Completion</CardTitle>
              <BarChart2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userData.profileCompletion}%</div>
              <p className="text-xs text-muted-foreground">
                Complete your profile to improve your score
              </p>
              <Progress value={userData.profileCompletion} className="h-2 mt-2" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resume Score</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {userData.analysis?.score || 0}/100
              </div>
              <p className="text-xs text-muted-foreground">
                {userData.analysis?.score >= 80 ? 'Excellent!' : 'Good, but can be improved'}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Resumes</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{userData.resumeHistory?.length || 0}</div>
              <p className="text-xs text-muted-foreground">
                Total uploaded resumes
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
              <CalendarDays className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatDistanceToNow(new Date(userData.lastUpdated), { addSuffix: true })}
              </div>
              <p className="text-xs text-muted-foreground">
                Since last update
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid gap-6 md:grid-cols-3">
          {/* Resume History */}
          <div className="md:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Recent Resumes</CardTitle>
                <p className="text-sm text-muted-foreground">Your most recent resume uploads</p>
              </CardHeader>
              <CardContent>
                <ResumeHistory resumes={userData.resumeHistory} />
              </CardContent>
            </Card>
          </div>

          {/* Analysis Results */}
          <div className="md:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Resume Analysis</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Detailed analysis of your most recent resume
                </p>
              </CardHeader>
              <CardContent>
                <AnalysisResults analysis={userData.analysis} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Personalized suggestions to improve your resume
                </p>
              </CardHeader>
              <CardContent>
                <Recommendations recommendations={userData.recommendations} />
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview" onClick={() => setActiveTab('overview')}>
              Overview
            </TabsTrigger>
            <TabsTrigger value="resume-history" onClick={() => setActiveTab('resume-history')}>
              <History className="mr-2 h-4 w-4" />
              Resume History
            </TabsTrigger>
            <TabsTrigger value="analysis" onClick={() => setActiveTab('analysis')}>
              Analysis
            </TabsTrigger>
            <TabsTrigger value="recommendations" onClick={() => setActiveTab('recommendations')}>
              Recommendations
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Resume Analysis</CardTitle>
                  <CardDescription>Key insights from your latest resume</CardDescription>
                </CardHeader>
                <CardContent>
                  <AnalysisResults analysis={userData?.analysis} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Top Recommendations</CardTitle>
                  <CardDescription>Ways to improve your profile</CardDescription>
                </CardHeader>
                <CardContent>
                  <Recommendations recommendations={userData?.recommendations?.slice(0, 4) || []} />
                </CardContent>
              </Card>
            </div>
            <Card>
              <CardHeader>
                <CardTitle>Recent Resume Uploads</CardTitle>
                <CardDescription>Your most recent resume versions</CardDescription>
              </CardHeader>
              <CardContent>
                <ResumeHistory resumes={userData?.resumeHistory?.slice(0, 3) || []} />
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="resume-history">
            <Card>
              <CardHeader>
                <CardTitle>Resume History</CardTitle>
                <CardDescription>All your uploaded resumes and their analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <ResumeHistory resumes={userData?.resumeHistory || []} showAll />
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="analysis">
            <Card>
              <CardHeader>
                <CardTitle>Detailed Analysis</CardTitle>
                <CardDescription>In-depth analysis of your resume</CardDescription>
              </CardHeader>
              <CardContent>
                <AnalysisResults analysis={userData?.analysis} detailed />
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="recommendations">
            <Card>
              <CardHeader>
                <CardTitle>Career Recommendations</CardTitle>
                <CardDescription>Personalized suggestions to boost your career</CardDescription>
              </CardHeader>
              <CardContent>
                <Recommendations 
                  recommendations={userData?.recommendations || []} 
                  detailed 
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

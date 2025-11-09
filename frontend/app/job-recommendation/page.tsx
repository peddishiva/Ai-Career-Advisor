'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  Briefcase,
  Clock,
  MapPin,
  DollarSign,
  Sparkles,
  TrendingUp,
  Moon,
  Sun,
  Search,
  Loader2,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/use-toast';

const jobRecommendations = [
  {
    id: 'jr-01',
    title: 'Senior Data Analyst',
    company: 'Insightful Analytics',
    location: 'Remote (North America)',
    salary: '$110k – $135k',
    posted: '2 days ago',
    description:
      'Own reporting pipelines, partner with product teams, and surface insights that drive strategic decisions.',
    tags: ['SQL', 'Looker', 'Stakeholder Management'],
  },
  {
    id: 'jr-02',
    title: 'Product Intelligence Lead',
    company: 'NovaTech Labs',
    location: 'Austin, TX',
    salary: '$120k – $150k',
    posted: '4 days ago',
    description:
      'Lead cross-functional experiments, build dashboards, and translate data into compelling product strategies.',
    tags: ['A/B Testing', 'Product Strategy', 'Storytelling'],
  },
  {
    id: 'jr-03',
    title: 'Business Analyst, Growth',
    company: 'Velocity Ventures',
    location: 'New York, NY',
    salary: '$95k – $118k',
    posted: '1 day ago',
    description:
      'Collaborate with marketing and finance to uncover opportunities that accelerate revenue and retention.',
    tags: ['SQL', 'Forecasting', 'Financial Modeling'],
  },
];

const highlightStats = [
  {
    label: 'New matches this week',
    value: '12',
    icon: Sparkles,
    description: 'Fresh roles curated for your profile in the last 7 days.',
  },
  {
    label: 'Growth market roles',
    value: '68%',
    icon: TrendingUp,
    description: 'Positions focused on data-driven product teams and analytics.',
  },
  {
    label: 'Remote friendly',
    value: '45%',
    icon: MapPin,
    description: 'Opportunities offering fully remote or hybrid flexibility.',
  },
];

interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  salary: string;
  posted: string;
  description: string;
  tags: string[];
  type?: string;
  experience?: string;
}

export default function JobRecommendationPage() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [jobs, setJobs] = useState<Job[]>(jobRecommendations);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [savedJobs, setSavedJobs] = useState<string[]>([]);
  const [isAlertsModalOpen, setIsAlertsModalOpen] = useState<boolean>(false);
  const [alertsEnabled, setAlertsEnabled] = useState<boolean>(false);
  const [alertEmail, setAlertEmail] = useState<string>('');
  const [alertFrequency, setAlertFrequency] = useState<string>('weekly');

  // Load saved jobs from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('savedJobs');
    if (saved) {
      try {
        setSavedJobs(JSON.parse(saved));
      } catch (e) {
        console.error('Error loading saved jobs:', e);
      }
    }

    // Load alert preferences
    const alertPrefs = localStorage.getItem('jobAlerts');
    if (alertPrefs) {
      try {
        const prefs = JSON.parse(alertPrefs);
        setAlertsEnabled(prefs.enabled || false);
        setAlertEmail(prefs.email || '');
        setAlertFrequency(prefs.frequency || 'weekly');
      } catch (e) {
        console.error('Error loading alert preferences:', e);
      }
    }
  }, []);

  useEffect(() => {
    // Load search query from localStorage if it exists
    const storedQuery = localStorage.getItem('jobSearchQuery');
    if (storedQuery) {
      setSearchQuery(storedQuery);
      // Clear it after loading
      localStorage.removeItem('jobSearchQuery');
      // Fetch jobs based on search query
      fetchJobs(storedQuery);
    }
  }, []);

  const saveJob = (job: Job) => {
    try {
      // Get existing saved jobs
      const existingSaved = localStorage.getItem('savedJobs');
      let savedJobsList: Job[] = [];
      
      if (existingSaved) {
        savedJobsList = JSON.parse(existingSaved);
      }
      
      // Check if job is already saved
      const isAlreadySaved = savedJobsList.some(savedJob => savedJob.id === job.id);
      
      if (isAlreadySaved) {
        toast({
          title: 'Already saved',
          description: 'This job is already in your saved list.',
        });
        return;
      }
      
      // Add new job
      savedJobsList.push(job);
      localStorage.setItem('savedJobs', JSON.stringify(savedJobsList));
      setSavedJobs(savedJobsList.map(j => j.id));
      
      toast({
        title: 'Job saved!',
        description: 'Job has been added to your profile.',
      });
    } catch (error) {
      console.error('Error saving job:', error);
      toast({
        title: 'Error',
        description: 'Failed to save job. Please try again.',
        variant: 'destructive',
      });
    }
  };

  const isJobSaved = (jobId: string) => {
    return savedJobs.includes(jobId);
  };

  const handleEnableAlerts = () => {
    if (alertsEnabled) {
      // If already enabled, show settings
      setIsAlertsModalOpen(true);
    } else {
      // If not enabled, open modal to configure
      setIsAlertsModalOpen(true);
    }
  };

  const handleSaveAlerts = () => {
    if (!alertEmail) {
      toast({
        title: 'Email required',
        description: 'Please enter your email address to receive alerts.',
        variant: 'destructive',
      });
      return;
    }

    const alertPrefs = {
      enabled: true,
      email: alertEmail,
      frequency: alertFrequency,
      searchQuery: searchQuery || 'all jobs',
      enabledAt: new Date().toISOString(),
    };

    localStorage.setItem('jobAlerts', JSON.stringify(alertPrefs));
    setAlertsEnabled(true);
    setIsAlertsModalOpen(false);

    toast({
      title: 'Alerts enabled!',
      description: `You'll receive ${alertFrequency} job updates at ${alertEmail}`,
    });
  };

  const handleDisableAlerts = () => {
    localStorage.removeItem('jobAlerts');
    setAlertsEnabled(false);
    setIsAlertsModalOpen(false);

    toast({
      title: 'Alerts disabled',
      description: 'You will no longer receive job notifications.',
    });
  };

  const fetchJobs = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      console.log('Fetching jobs from:', `${apiUrl}/api/jobs/recommendations?query=${encodeURIComponent(query)}`);
      
      const response = await fetch(`${apiUrl}/api/jobs/recommendations?query=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received jobs:', data);
      
      if (data.success && data.jobs) {
        setJobs(data.jobs);
      } else {
        throw new Error('Invalid response format from server');
      }
    } catch (err) {
      console.error('Error fetching jobs:', err);
      
      // Provide more specific error messages
      let errorMessage = 'Failed to load job recommendations';
      
      if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Cannot connect to backend server. Please make sure the backend is running on http://localhost:5000';
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      // Keep default jobs on error
      setJobs(jobRecommendations);
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950">
      <nav className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div 
              className="flex items-center cursor-pointer hover:opacity-80 transition-opacity"
              onClick={() => router.push('/')}
            >
              <BookOpen className="h-8 w-8 text-blue-600 dark:text-blue-500" />
              <span className="ml-2 text-xl font-semibold text-gray-900 dark:text-white">
                AI Career Advisor
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="icon"
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </Button>
              <Button
                variant="ghost"
                className="text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                onClick={() => router.push('/')}
              >
                Home
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Job Recommendations</h1>
            {searchQuery ? (
              <div className="mt-2 flex items-center gap-2">
                <Search className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Showing results for: <span className="font-semibold text-blue-600 dark:text-blue-400">&quot;{searchQuery}&quot;</span>
                </p>
              </div>
            ) : (
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Curated opportunities aligned with your skills, interests, and target roles.
              </p>
            )}
          </div>
          <Button
            variant="outline"
            className="border-blue-200 text-blue-600 hover:bg-blue-50 dark:border-blue-500/40 dark:text-blue-300 dark:hover:bg-blue-500/10"
            onClick={() => router.push('/search')}
          >
            Explore Full Job Board
          </Button>
        </header>

        <section className="grid gap-6 md:grid-cols-3">
          {highlightStats.map((stat) => (
            <Card key={stat.label} className="dark:bg-gray-900/60 dark:border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-300">
                  {stat.label}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{stat.description}</p>
              </CardContent>
            </Card>
          ))}
        </section>

        <section className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Newest Matches</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Updated daily based on your profile and market trends.
            </p>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">Loading job recommendations...</span>
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/20">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {!isLoading && !error && (
            <div className="grid gap-6 lg:grid-cols-2">
              {jobs.map((job: Job) => (
              <Card
                key={job.id}
                className="dark:bg-gray-900/60 dark:border-gray-800 bg-white/80 backdrop-blur"
              >
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-gray-900 dark:text-white">{job.title}</CardTitle>
                      <CardDescription className="mt-1 text-gray-500 dark:text-gray-300">
                        {job.company}
                      </CardDescription>
                    </div>
                    <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-500/20 dark:text-blue-200">
                      Recommended
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 text-sm text-gray-700 dark:text-gray-300">
                  <p>{job.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs font-medium text-gray-600 dark:text-gray-400">
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">
                      <MapPin className="h-4 w-4 text-blue-500" />
                      {job.location}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">
                      <DollarSign className="h-4 w-4 text-green-500" />
                      {job.salary}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 dark:bg-gray-800">
                      <Clock className="h-4 w-4 text-amber-500" />
                      Posted {job.posted}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {job.tags.map((tag: string) => (
                      <span
                        key={tag}
                        className="rounded-full border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-600 dark:border-gray-700 dark:text-gray-300"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-3 pt-2">
                    <Button
                      variant="default"
                      className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700"
                      onClick={() => {
                        setSelectedJob(job);
                        setIsModalOpen(true);
                      }}
                    >
                      View Details
                    </Button>
                    <Button
                      variant="outline"
                      className={`border-gray-200 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800 ${
                        isJobSaved(job.id) ? 'bg-green-50 border-green-500 text-green-700 dark:bg-green-900/20 dark:border-green-500 dark:text-green-400' : ''
                      }`}
                      onClick={() => saveJob(job)}
                      disabled={isJobSaved(job.id)}
                    >
                      {isJobSaved(job.id) ? '✓ Saved' : 'Save Role'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          )}
        </section>

        <section className="rounded-2xl bg-blue-50/70 p-8 shadow-sm dark:bg-blue-900/30 dark:text-blue-100">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-2xl font-semibold text-blue-900 dark:text-blue-100">Stay ahead of the market</h3>
              <p className="mt-2 text-sm text-blue-800/80 dark:text-blue-100/80">
                Enable weekly alerts to receive personalized job updates directly in your inbox.
              </p>
            </div>
            <Button
              className={`${
                alertsEnabled
                  ? 'bg-green-600 text-white hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700'
                  : 'bg-white text-blue-600 hover:bg-blue-100 dark:bg-blue-500 dark:text-white dark:hover:bg-blue-400'
              }`}
              onClick={handleEnableAlerts}
            >
              {alertsEnabled ? '✓ Alerts Enabled' : 'Enable Alerts'}
            </Button>
          </div>
        </section>
      </main>

      {/* Job Details Modal */}
      {isModalOpen && selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900 m-4">
            {/* Close button */}
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute right-4 top-4 rounded-full p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Header */}
            <div className="mb-6 pr-8">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{selectedJob.title}</h2>
                  <p className="mt-1 text-lg text-gray-600 dark:text-gray-300">{selectedJob.company}</p>
                </div>
                <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-500/20 dark:text-blue-200">
                  {selectedJob.type || 'Full-time'}
                </span>
              </div>
            </div>

            {/* Job Info Grid */}
            <div className="mb-6 grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-800/50">
              <div className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Location</p>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedJob.location}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-green-500" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Salary</p>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedJob.salary}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-amber-500" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Posted</p>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedJob.posted}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-purple-500" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Experience</p>
                  <p className="font-medium text-gray-900 dark:text-white">{selectedJob.experience || 'Mid-level'}</p>
                </div>
              </div>
            </div>

            {/* Job Description */}
            <div className="mb-6">
              <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Job Description</h3>
              <p className="text-gray-700 leading-relaxed dark:text-gray-300">{selectedJob.description}</p>
            </div>

            {/* Skills/Tags */}
            <div className="mb-6">
              <h3 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Required Skills</h3>
              <div className="flex flex-wrap gap-2">
                {selectedJob.tags.map((tag: string) => (
                  <span
                    key={tag}
                    className="rounded-full bg-blue-100 px-4 py-2 text-sm font-medium text-blue-700 dark:bg-blue-500/20 dark:text-blue-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 border-t pt-4 dark:border-gray-800">
              <Button
                className="flex-1 bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700"
                onClick={() => {
                  // Handle apply action
                  window.open(`https://www.google.com/search?q=${encodeURIComponent(selectedJob.title + ' ' + selectedJob.company + ' job application')}`, '_blank');
                }}
              >
                Apply Now
              </Button>
              <Button
                variant="outline"
                className={`flex-1 border-gray-200 text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800 ${
                  isJobSaved(selectedJob.id) ? 'bg-green-50 border-green-500 text-green-700 dark:bg-green-900/20 dark:border-green-500 dark:text-green-400' : ''
                }`}
                onClick={() => {
                  saveJob(selectedJob);
                  setTimeout(() => setIsModalOpen(false), 500);
                }}
                disabled={isJobSaved(selectedJob.id)}
              >
                {isJobSaved(selectedJob.id) ? '✓ Saved' : 'Save for Later'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Job Alerts Configuration Modal */}
      {isAlertsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900 m-4">
            {/* Close button */}
            <button
              onClick={() => setIsAlertsModalOpen(false)}
              className="absolute right-4 top-4 rounded-full p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Header */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Job Alerts</h2>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Get notified about new job opportunities matching your interests
              </p>
            </div>

            {/* Alert Form */}
            <div className="space-y-4">
              {/* Email Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                />
              </div>

              {/* Frequency Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Alert Frequency
                </label>
                <select
                  value={alertFrequency}
                  onChange={(e) => setAlertFrequency(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="biweekly">Bi-weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              {/* Search Query Info */}
              {searchQuery && (
                <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>Alerts for:</strong> {searchQuery}
                  </p>
                </div>
              )}

              {/* Current Status */}
              {alertsEnabled && (
                <div className="rounded-lg bg-green-50 p-3 dark:bg-green-900/20">
                  <p className="text-sm text-green-800 dark:text-green-200">
                    ✓ Alerts are currently enabled
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex gap-3">
              {alertsEnabled ? (
                <>
                  <Button
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={handleSaveAlerts}
                  >
                    Update Alerts
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
                    onClick={handleDisableAlerts}
                  >
                    Disable
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={handleSaveAlerts}
                  >
                    Enable Alerts
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setIsAlertsModalOpen(false)}
                  >
                    Cancel
                  </Button>
                </>
              )}
            </div>

            {/* Info Text */}
            <p className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
              You can change these settings anytime from your profile
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

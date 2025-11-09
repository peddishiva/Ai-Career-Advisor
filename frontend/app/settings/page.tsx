'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { useToast } from '@/components/ui/use-toast';
import { Briefcase, MapPin, DollarSign, Clock, Trash2, ExternalLink } from 'lucide-react';

interface SavedJob {
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

export default function SettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();
  const [username, setUsername] = useState('John Doe');
  const [email, setEmail] = useState('john.doe@example.com');
  const [isSaving, setIsSaving] = useState(false);
  const [avatar, setAvatar] = useState('/default-avatar.jpg');
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(false);

  // Load saved jobs from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('savedJobs');
    if (saved) {
      try {
        setSavedJobs(JSON.parse(saved));
      } catch (e) {
        console.error('Error loading saved jobs:', e);
      }
    }
  }, []);

  // Sync dark mode state with theme
  useEffect(() => {
    setDarkMode(theme === 'dark');
  }, [theme]);

  // Handle dark mode toggle
  const handleDarkModeToggle = () => {
    const newTheme = darkMode ? 'light' : 'dark';
    setTheme(newTheme);
    setDarkMode(!darkMode);
    
    toast({
      title: 'Theme updated',
      description: `Switched to ${newTheme} mode`,
    });
  };

  const handleSaveChanges = async () => {
    try {
      setIsSaving(true);
      // Here you would typically make an API call to save the changes
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      toast({
        title: 'Success',
        description: 'Your profile has been updated successfully!',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update profile. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          setAvatar(reader.result);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const removeSavedJob = (jobId: string) => {
    const updatedJobs = savedJobs.filter(job => job.id !== jobId);
    setSavedJobs(updatedJobs);
    localStorage.setItem('savedJobs', JSON.stringify(updatedJobs));
    
    toast({
      title: 'Job removed',
      description: 'Job has been removed from your saved list.',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Account Settings</h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Manage your account settings and preferences
          </p>
        </div>

        <div className="grid gap-6">
          {/* Profile Card */}
          <Card className="dark:bg-gray-800 dark:border-gray-700">
            <CardHeader>
              <CardTitle className="text-xl dark:text-white">Profile</CardTitle>
              <CardDescription className="dark:text-gray-300">
                Update your profile information and avatar
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="flex items-center space-x-6">
                  <div className="relative">
                    <Avatar className="h-24 w-24">
                      <AvatarImage src={avatar} alt="Profile" />
                      <AvatarFallback className="text-2xl">
                        {username.split(' ').map(n => n[0]).join('')}
                      </AvatarFallback>
                    </Avatar>
                    <label 
                      htmlFor="avatar-upload" 
                      className="absolute -bottom-2 -right-2 bg-blue-600 text-white p-2 rounded-full cursor-pointer hover:bg-blue-700 transition-colors"
                      title="Change avatar"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                      </svg>
                      <input
                        id="avatar-upload"
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleAvatarChange}
                      />
                    </label>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Profile Picture</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">JPG, GIF or PNG. Max 2MB</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="username" className="dark:text-gray-300">Username</Label>
                    <Input
                      id="username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="dark:text-gray-300">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      disabled
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Account Preferences */}
          <Card className="dark:bg-gray-800 dark:border-gray-700">
            <CardHeader>
              <CardTitle className="text-xl dark:text-white">Preferences</CardTitle>
              <CardDescription className="dark:text-gray-300">
                Configure how you want to use the platform
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Email Notifications</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Receive email notifications</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={emailNotifications}
                      onChange={(e) => {
                        setEmailNotifications(e.target.checked);
                        toast({
                          title: 'Notification settings updated',
                          description: `Email notifications ${e.target.checked ? 'enabled' : 'disabled'}`,
                        });
                      }}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">Dark Mode</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">Switch between light and dark theme</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={darkMode}
                      onChange={handleDarkModeToggle}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Saved Jobs Section */}
          <Card className="dark:bg-gray-800 dark:border-gray-700">
            <CardHeader>
              <CardTitle className="text-xl dark:text-white">Saved Jobs</CardTitle>
              <CardDescription className="dark:text-gray-300">
                Jobs you've saved for later ({savedJobs.length})
              </CardDescription>
            </CardHeader>
            <CardContent>
              {savedJobs.length === 0 ? (
                <div className="text-center py-12">
                  <Briefcase className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-4 text-sm font-medium text-gray-900 dark:text-white">No saved jobs</h3>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Start saving jobs you're interested in from the job recommendations page.
                  </p>
                  <Button
                    onClick={() => router.push('/job-recommendation')}
                    className="mt-4 bg-blue-600 hover:bg-blue-700"
                  >
                    Browse Jobs
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {savedJobs.map((job) => (
                    <div
                      key={job.id}
                      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                {job.title}
                              </h3>
                              <p className="text-sm text-gray-600 dark:text-gray-300">{job.company}</p>
                            </div>
                            {job.type && (
                              <span className="ml-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-500/20 dark:text-blue-200">
                                {job.type}
                              </span>
                            )}
                          </div>

                          <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-400">
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {job.location}
                            </span>
                            <span className="flex items-center gap-1">
                              <DollarSign className="h-3 w-3" />
                              {job.salary}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {job.posted}
                            </span>
                          </div>

                          <div className="mt-3 flex flex-wrap gap-2">
                            {job.tags.slice(0, 4).map((tag) => (
                              <span
                                key={tag}
                                className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                              >
                                {tag}
                              </span>
                            ))}
                            {job.tags.length > 4 && (
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                +{job.tags.length - 4} more
                              </span>
                            )}
                          </div>

                          <div className="mt-4 flex gap-2">
                            <Button
                              size="sm"
                              className="bg-blue-600 hover:bg-blue-700"
                              onClick={() => {
                                window.open(
                                  `https://www.google.com/search?q=${encodeURIComponent(job.title + ' ' + job.company + ' job application')}`,
                                  '_blank'
                                );
                              }}
                            >
                              <ExternalLink className="h-3 w-3 mr-1" />
                              Apply
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
                              onClick={() => removeSavedJob(job.id)}
                            >
                              <Trash2 className="h-3 w-3 mr-1" />
                              Remove
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex justify-end space-x-3">
            <Button 
              variant="outline" 
              onClick={() => router.back()}
              className="dark:border-gray-600 dark:text-white dark:hover:bg-gray-700"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveChanges}
              disabled={isSaving}
              className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700"
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

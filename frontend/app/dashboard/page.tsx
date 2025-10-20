import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileUp, User, BookOpen, BarChart2, Settings, Menu } from 'lucide-react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center h-16 px-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">AI Career Advisor</h1>
          </div>
          <nav className="flex-1 px-2 py-4 space-y-1">
            <Link href="/dashboard" className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md group">
              <BarChart2 className="w-5 h-5 mr-3" />
              Dashboard
            </Link>
            <Link href="/dashboard/profile" className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
              <User className="w-5 h-5 mr-3" />
              Profile
            </Link>
            <Link href="/dashboard/upload" className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
              <FileUp className="w-5 h-5 mr-3" />
              Upload Resume
            </Link>
            <Link href="/dashboard/learning" className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
              <BookOpen className="w-5 h-5 mr-3" />
              Learning Paths
            </Link>
          </nav>
          <div className="p-4 mt-auto">
            <div className="p-4 text-sm text-gray-700 bg-gray-100 rounded-lg dark:bg-gray-700 dark:text-gray-300">
              <p>Need help? Check out our documentation or contact support.</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top navigation */}
        <header className="flex items-center justify-between h-16 px-4 bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700">
          <div className="flex items-center">
            <Button variant="ghost" size="icon" className="md:hidden">
              <Menu className="w-5 h-5" />
            </Button>
            <h2 className="ml-2 text-lg font-semibold text-gray-900 dark:text-white">Dashboard</h2>
          </div>
          <div className="flex items-center space-x-4">
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
            <Button variant="outline" size="sm">
              Sign Out
            </Button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="grid gap-6">
            {/* Welcome Card */}
            <Card>
              <CardHeader>
                <CardTitle>Welcome back, Alex</CardTitle>
                <CardDescription>Here's what's happening with your career progress.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="p-4 bg-blue-50 rounded-lg dark:bg-blue-900/20">
                    <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">Skills Matched</h3>
                    <p className="text-2xl font-bold text-blue-600 dark:text-blue-300">24/35</p>
                    <p className="text-xs text-blue-600/70 dark:text-blue-300/70">68% match rate</p>
                  </div>
                  <div className="p-4 bg-green-50 rounded-lg dark:bg-green-900/20">
                    <h3 className="text-sm font-medium text-green-800 dark:text-green-200">Learning Progress</h3>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-300">42%</p>
                    <p className="text-xs text-green-600/70 dark:text-green-300/70">3/7 skills in progress</p>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg dark:bg-purple-900/20">
                    <h3 className="text-sm font-medium text-purple-800 dark:text-purple-200">Recommended Jobs</h3>
                    <p className="text-2xl font-bold text-purple-600 dark:text-purple-300">12</p>
                    <p className="text-xs text-purple-600/70 dark:text-purple-300/70">Based on your profile</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Skills & Recommendations */}
            <div className="grid gap-6 md:grid-cols-2">
              {/* Skills Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Your Skills</CardTitle>
                  <CardDescription>Skills extracted from your resume and profile</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Strong Skills</h3>
                      <div className="flex flex-wrap gap-2">
                        {['JavaScript', 'React', 'Node.js', 'TypeScript', 'REST APIs', 'Git'].map((skill) => (
                          <span key={skill} className="inline-flex items-center px-3 py-1 text-sm font-medium bg-green-100 text-green-800 rounded-full dark:bg-green-900/30 dark:text-green-300">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Skills to Improve</h3>
                      <div className="flex flex-wrap gap-2">
                        {['Docker', 'AWS', 'GraphQL', 'Testing', 'CI/CD'].map((skill) => (
                          <span key={skill} className="inline-flex items-center px-3 py-1 text-sm font-medium bg-yellow-100 text-yellow-800 rounded-full dark:bg-yellow-900/30 dark:text-yellow-300">
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Recommendations Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Recommended Learning</CardTitle>
                  <CardDescription>Personalized courses to boost your career</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {[
                      {
                        title: 'Advanced React Patterns',
                        provider: 'Frontend Masters',
                        progress: 65,
                        category: 'Frontend'
                      },
                      {
                        title: 'AWS Certified Developer',
                        provider: 'A Cloud Guru',
                        progress: 30,
                        category: 'DevOps'
                      },
                      {
                        title: 'TypeScript Fundamentals',
                        provider: 'Pluralsight',
                        progress: 15,
                        category: 'Frontend'
                      }
                    ].map((course, index) => (
                      <div key={index} className="p-3 border rounded-lg hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800/50">
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="font-medium text-gray-900 dark:text-white">{course.title}</h4>
                            <p className="text-sm text-gray-500 dark:text-gray-400">{course.provider} • {course.category}</p>
                          </div>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                            {course.progress}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2 dark:bg-gray-700">
                          <div 
                            className="bg-blue-600 h-1.5 rounded-full dark:bg-blue-500" 
                            style={{ width: `${course.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Your recent interactions and updates</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { 
                      id: 1, 
                      title: 'Completed React Hooks course', 
                      description: 'You completed the React Hooks course on Frontend Masters',
                      time: '2 hours ago',
                      type: 'completion'
                    },
                    { 
                      id: 2, 
                      title: 'New job matches', 
                      description: '5 new jobs match your profile',
                      time: '1 day ago',
                      type: 'notification'
                    },
                    { 
                      id: 3, 
                      title: 'Skill assessment updated', 
                      description: 'Your JavaScript skill level has been updated to Advanced',
                      time: '2 days ago',
                      type: 'update'
                    }
                  ].map((activity) => (
                    <div key={activity.id} className="flex items-start pb-4 border-b border-gray-100 last:border-0 last:pb-0 dark:border-gray-800">
                      <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-blue-500"></div>
                      <div className="ml-3">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white">{activity.title}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{activity.description}</p>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">{activity.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}

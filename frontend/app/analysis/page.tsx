'use client';

import { useState, useEffect, useMemo } from 'react';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  TrendingUp,
  Target,
  ClipboardCheck,
  Lightbulb,
  BarChart3,
  Moon,
  Sun,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

// Default fallback data
const defaultSkillProgress = [
  { name: 'Python', level: 82 },
  { name: 'Data Analysis', level: 76 },
  { name: 'Communication', level: 69 },
  { name: 'Leadership', level: 60 },
];

const defaultRoleMatches = [
  {
    title: 'Data Analyst',
    match: 88,
    summary: 'Strong alignment with analytical strengths and project experience.',
  },
  {
    title: 'Product Analyst',
    match: 81,
    summary: 'Great fit for cross-functional collaboration and insight generation.',
  },
  {
    title: 'Business Intelligence Analyst',
    match: 78,
    summary: 'Solid foundation in reporting with opportunity to deepen leadership skills.',
  },
];

const defaultNextActions = [
  {
    title: 'Strengthen Storytelling',
    description: 'Create a portfolio case study that highlights impact-driven narratives.',
  },
  {
    title: 'Grow Leadership Exposure',
    description: 'Volunteer to lead a cross-team initiative to build people-management skills.',
  },
  {
    title: 'Deepen SQL Expertise',
    description: 'Complete an advanced SQL project focusing on query optimization.',
  },
];

export default function AnalysisPage() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load analysis data from localStorage
    const storedAnalysis = localStorage.getItem('resumeAnalysis');
    if (storedAnalysis) {
      try {
        const data = JSON.parse(storedAnalysis);
        setAnalysisData(data);
      } catch (error) {
        console.error('Error parsing analysis data:', error);
      }
    }
    setLoading(false);
  }, []);

  const overallInsights = useMemo(() => {
    if (analysisData?.overall_insights) {
      return {
        fitScore: analysisData.overall_insights.fit_score,
        weekChange: analysisData.overall_insights.week_change,
        highlights: analysisData.overall_insights.highlights,
      };
    }
    return {
      fitScore: 84,
      weekChange: 5,
      highlights: [
        'Resume showcases measurable impact across key projects.',
        'Skill profile strongly maps to analytical and strategy-focused roles.',
        'Opportunities exist to amplify leadership and stakeholder storytelling.',
      ],
    };
  }, [analysisData]);

  const skillProgress = useMemo(() => {
    if (analysisData?.skill_strengths) {
      return analysisData.skill_strengths;
    }
    return defaultSkillProgress;
  }, [analysisData]);

  const roleMatches = useMemo(() => {
    if (analysisData?.role_matches) {
      return analysisData.role_matches;
    }
    return defaultRoleMatches;
  }, [analysisData]);

  const nextActions = useMemo(() => {
    if (analysisData?.next_actions) {
      return analysisData.next_actions;
    }
    return defaultNextActions;
  }, [analysisData]);

  const metrics = useMemo(() => {
    if (analysisData?.metrics) {
      return analysisData.metrics;
    }
    return {
      role_alignment: 'High',
      skill_momentum: 12,
      readiness_actions_count: 3,
    };
  }, [analysisData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading analysis...</p>
        </div>
      </div>
    );
  }

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
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Analysis Overview</h1>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Personalized insights based on your uploaded resume and career preferences.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-blue-50 px-4 py-2 text-sm font-medium text-blue-600 dark:bg-blue-500/10 dark:text-blue-300">
              Overall Fit Score: <span className="font-semibold">{overallInsights.fitScore}%</span>
            </div>
            <span className="rounded-full bg-green-50 px-4 py-2 text-sm font-medium text-green-600 dark:bg-green-500/10 dark:text-green-300">
              +{overallInsights.weekChange}% vs last review
            </span>
          </div>
        </header>

        <section className="grid gap-6 md:grid-cols-3">
          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-300">
                Role Alignment
              </CardTitle>
              <Target className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.role_alignment}</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Matches highlight strong alignment with analytical roles.
              </p>
            </CardContent>
          </Card>

          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-300">
                Skill Momentum
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">+{metrics.skill_momentum}%</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Growth in technical proficiency quarter over quarter.
              </p>
            </CardContent>
          </Card>

          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-300">
                Readiness Actions
              </CardTitle>
              <ClipboardCheck className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.readiness_actions_count} steps</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Focus areas to elevate your profile for target roles.
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2 dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-gray-900 dark:text-white">Insights Breakdown</CardTitle>
                  <CardDescription className="dark:text-gray-400">
                    Key highlights extracted from your latest resume analysis.
                  </CardDescription>
                </div>
                <BarChart3 className="h-6 w-6 text-blue-500" />
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4">
                {overallInsights.highlights.map((highlight: string) => (
                  <li
                    key={highlight}
                    className="flex items-start gap-3 rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-700 dark:bg-gray-800/80 dark:text-gray-200"
                  >
                    <Lightbulb className="mt-0.5 h-4 w-4 text-amber-500" />
                    <span>{highlight}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Skill Strengths</CardTitle>
              <CardDescription className="dark:text-gray-400">
                Relative skill proficiency based on profile assessment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {skillProgress.map((skill: { name: string; level: number }) => (
                <div key={skill.name}>
                  <div className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-200">
                    <span>{skill.name}</span>
                    <span>{skill.level}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
                      style={{ width: `${skill.level}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 lg:grid-cols-2">
          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Top Role Matches</CardTitle>
              <CardDescription className="dark:text-gray-400">
                Roles that best align with your current capabilities.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {roleMatches.map((role: { title: string; match: number; summary: string }) => (
                <div
                  key={role.title}
                  className="rounded-xl border border-gray-200 bg-white/70 p-4 backdrop-blur dark:border-gray-800 dark:bg-gray-800/60"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{role.title}</h3>
                      <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">{role.summary}</p>
                    </div>
                    <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-semibold text-blue-700 dark:bg-blue-500/20 dark:text-blue-200">
                      {role.match}% match
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="dark:bg-gray-900/60 dark:border-gray-800">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Next Best Actions</CardTitle>
              <CardDescription className="dark:text-gray-400">
                High-leverage steps to continue strengthening your profile.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="space-y-4">
                {nextActions.map((action: { title: string; description: string }, index: number) => (
                  <li key={action.title} className="flex gap-4">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/10 text-sm font-semibold text-blue-600 dark:bg-blue-500/20 dark:text-blue-200">
                      {index + 1}
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{action.title}</h3>
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{action.description}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}

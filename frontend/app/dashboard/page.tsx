'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  Briefcase,
  FileText,
  FileUp,
  LayoutDashboard,
  LogOut,
  Menu,
  Sparkles,
  Target,
  User,
  X,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/auth-context';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

function DashboardContent() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [savedJobsCount, setSavedJobsCount] = useState<number>(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Safely load real application state from localStorage
    try {
      const storedAnalysis = localStorage.getItem('resumeAnalysis');
      if (storedAnalysis) {
        setAnalysisData(JSON.parse(storedAnalysis));
      }
    } catch {
      // Storage parsing failure fallback
      setAnalysisData(null);
    }

    try {
      const storedSaved = localStorage.getItem('savedJobs');
      if (storedSaved) {
        const parsed = JSON.parse(storedSaved);
        if (Array.isArray(parsed)) {
          setSavedJobsCount(parsed.length);
        }
      }
    } catch {
      setSavedJobsCount(0);
    }
  }, []);

  const handleSignOut = async () => {
    await signOut();
    router.replace('/auth/login');
  };

  const displayName = useMemo(() => {
    if (!user) return 'User';
    return (
      (user.user_metadata?.display_name as string) ||
      (user.user_metadata?.full_name as string) ||
      user.email?.split('@')[0] ||
      'User'
    );
  }, [user]);

  // Extract real metrics if analysis exists
  const realFitScore = analysisData?.overall_insights?.fit_score ?? analysisData?.overall_score ?? null;
  const realSkillCoverage = analysisData?.metrics?.skill_coverage ?? null;
  const realRoleMatches = Array.isArray(analysisData?.role_matches) ? analysisData.role_matches : [];
  const realSkills = Array.isArray(analysisData?.skill_strengths)
    ? analysisData.skill_strengths
    : Array.isArray(analysisData?.extracted_skills)
      ? analysisData.extracted_skills.map((s: string) => ({ name: s, level: 80 }))
      : [];
  const realNextActions = Array.isArray(analysisData?.next_actions)
    ? analysisData.next_actions
    : Array.isArray(analysisData?.overall_insights?.highlights)
      ? analysisData.overall_insights.highlights.map((h: string) => ({ title: 'Key Insight', description: h }))
      : [];

  const resumeFilename = analysisData?.metadata?.filename || null;

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Mobile Sidebar Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar (Desktop and Mobile Drawer) */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-200 dark:border-gray-800 dark:bg-gray-900 md:static md:translate-x-0 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Sidebar navigation"
      >
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4 dark:border-gray-800">
          <Link
            href="/"
            className="flex items-center gap-2 hover:opacity-85 transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          >
            <BookOpen className="h-6 w-6 text-blue-600 dark:text-blue-500" />
            <span className="text-lg font-bold text-gray-900 dark:text-white">AI Career Advisor</span>
          </Link>
          <button
            type="button"
            className="p-1 rounded-md text-gray-500 hover:text-gray-900 md:hidden dark:text-gray-400 dark:hover:text-white"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          <Link
            href="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-md dark:bg-blue-900/30 dark:text-blue-400"
          >
            <LayoutDashboard className="w-5 h-5 mr-3 text-blue-600 dark:text-blue-400" />
            Dashboard
          </Link>
          <Link
            href="/#upload"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <FileUp className="w-5 h-5 mr-3 text-gray-500 dark:text-gray-400" />
            Upload Resume
          </Link>
          <Link
            href="/analysis"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <BarChart3 className="w-5 h-5 mr-3 text-gray-500 dark:text-gray-400" />
            Resume Analysis
          </Link>
          <Link
            href="/job-recommendation"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <Briefcase className="w-5 h-5 mr-3 text-gray-500 dark:text-gray-400" />
            Job Recommendations
          </Link>
          <Link
            href="/jdxr-analyser"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <FileText className="w-5 h-5 mr-3 text-gray-500 dark:text-gray-400" />
            Compare with JD
          </Link>
          <Link
            href="/profile"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 rounded-md dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <User className="w-5 h-5 mr-3 text-gray-500 dark:text-gray-400" />
            Profile & Account
          </Link>
        </nav>

        <div className="border-t border-gray-200 p-3 dark:border-gray-800">
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center px-3 py-2 mb-1 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <BookOpen className="w-5 h-5 mr-3" />
            Back to Home
          </Link>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-600 rounded-md hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-800 dark:bg-gray-900 md:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="p-2 rounded-md text-gray-600 hover:bg-gray-100 md:hidden dark:text-gray-300 dark:hover:bg-gray-800"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400 hidden sm:inline">
              AI Career Advisor
            </span>
            <span className="text-gray-300 dark:text-gray-700 hidden sm:inline">/</span>
            <h1 className="text-base font-semibold text-gray-900 dark:text-white">Dashboard</h1>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/" className="hidden sm:inline-flex">
              <Button variant="ghost" size="sm">
                Main Site
              </Button>
            </Link>
            <Link href="/profile">
              <Button variant="outline" size="sm">
                <User className="w-4 h-4 mr-2" />
                Profile
              </Button>
            </Link>
            <Button variant="outline" size="sm" onClick={handleSignOut}>
              Sign Out
            </Button>
          </div>
        </header>

        {/* Dashboard Body */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="mx-auto max-w-6xl space-y-8">
            {/* Greeting Header */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white md:text-3xl">
                  Career Intelligence Dashboard
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Signed in as <span className="font-medium text-gray-700 dark:text-gray-300">{user?.email}</span>
                </p>
              </div>

              <div>
                {analysisData ? (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                    Resume Analyzed
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                    No Resume Loaded
                  </span>
                )}
              </div>
            </div>

            {/* REAL STATE 1: Resume Analysis is Loaded */}
            {analysisData ? (
              <div className="space-y-6">
                {/* Real Metrics Banner */}
                <Card className="border-blue-100 bg-gradient-to-r from-blue-50/50 via-white to-indigo-50/30 dark:border-blue-900/40 dark:from-gray-900 dark:via-gray-900 dark:to-blue-950/20">
                  <CardHeader className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4">
                    <div>
                      <CardTitle className="text-xl">Resume Overview</CardTitle>
                      <CardDescription>
                        {resumeFilename ? `File: ${resumeFilename}` : 'Deterministic resume evaluation active'}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Link href="/analysis">
                        <Button className="bg-blue-600 hover:bg-blue-700">
                          View Full Analysis
                          <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                      </Link>
                      <Link href="/#upload">
                        <Button variant="outline">Upload New Resume</Button>
                      </Link>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                      <div className="rounded-lg border bg-white p-4 dark:border-gray-800 dark:bg-gray-800/60">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Overall Fit Score</p>
                        <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                          {realFitScore !== null ? `${realFitScore}%` : 'Evaluated'}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Deterministic baseline</p>
                      </div>

                      <div className="rounded-lg border bg-white p-4 dark:border-gray-800 dark:bg-gray-800/60">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Skill Coverage</p>
                        <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                          {realSkillCoverage !== null ? `${realSkillCoverage}%` : `${realSkills.length} skills`}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">From parsed resume</p>
                      </div>

                      <div className="rounded-lg border bg-white p-4 dark:border-gray-800 dark:bg-gray-800/60">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Target Role Matches</p>
                        <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mt-1">
                          {realRoleMatches.length}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Identified role fits</p>
                      </div>

                      <div className="rounded-lg border bg-white p-4 dark:border-gray-800 dark:bg-gray-800/60">
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Saved Jobs</p>
                        <p className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                          {savedJobsCount}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">In your job tracker</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 2-Column: Real Skills + Real Role Matches */}
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Skills Card */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Target className="w-5 h-5 text-blue-600" />
                        Extracted Resume Skills
                      </CardTitle>
                      <CardDescription>Validated skills parsed directly from your document</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {realSkills.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {realSkills.map((skill: any, idx: number) => {
                            const skillName = typeof skill === 'string' ? skill : skill.name;
                            const skillLevel = typeof skill === 'object' && skill.level ? `${skill.level}%` : null;
                            return (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-200"
                              >
                                {skillName}
                                {skillLevel && (
                                  <span className="text-gray-400 dark:text-gray-500">· {skillLevel}</span>
                                )}
                              </span>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No specific skills parsed in this profile.</p>
                      )}
                    </CardContent>
                  </Card>

                  {/* Target Role Matches Card */}
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <div>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <Briefcase className="w-5 h-5 text-indigo-600" />
                          Top Matched Roles
                        </CardTitle>
                        <CardDescription>Roles that align with your experience</CardDescription>
                      </div>
                      <Link href="/job-recommendation">
                        <Button variant="ghost" size="sm" className="text-xs">
                          Browse Jobs
                        </Button>
                      </Link>
                    </CardHeader>
                    <CardContent className="space-y-3 pt-2">
                      {realRoleMatches.length > 0 ? (
                        realRoleMatches.slice(0, 3).map((role: any, idx: number) => (
                          <div
                            key={idx}
                            className="flex items-start justify-between rounded-lg border border-gray-100 p-3 dark:border-gray-800 dark:bg-gray-900/40"
                          >
                            <div className="space-y-0.5">
                              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                                {role.title}
                              </h4>
                              {role.summary && (
                                <p className="text-xs text-gray-500 line-clamp-1">{role.summary}</p>
                              )}
                            </div>
                            <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 ml-2 whitespace-nowrap">
                              {role.match ? `${role.match}% Match` : 'Matched'}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-gray-500">No role matches calculated yet.</p>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Real Recommendations Card */}
                {realNextActions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-amber-500" />
                        Prioritized Action Items
                      </CardTitle>
                      <CardDescription>Key recommendations to increase your role readiness</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {realNextActions.slice(0, 3).map((action: any, idx: number) => (
                          <div
                            key={idx}
                            className="rounded-lg border border-gray-100 p-4 dark:border-gray-800 dark:bg-gray-900/40"
                          >
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                              {action.title}
                            </h4>
                            <p className="text-xs text-gray-600 dark:text-gray-300">
                              {action.description}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              /* REAL STATE 2: No Resume Analyzed Yet (Polished Empty State) */
              <div className="space-y-6">
                <Card className="border-blue-100 bg-gradient-to-r from-blue-50/60 via-white to-indigo-50/40 dark:border-blue-900/40 dark:from-gray-900 dark:via-gray-900 dark:to-blue-950/20">
                  <CardHeader className="text-center sm:text-left">
                    <CardTitle className="text-2xl">Start Your Career Assessment</CardTitle>
                    <CardDescription className="max-w-2xl text-sm leading-relaxed mt-1">
                      Upload your resume in PDF or DOCX format to receive deterministic skill parsing, match
                      scoring against industry roles, and tailored career intelligence.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col sm:flex-row gap-3 pt-2">
                    <Link href="/#upload">
                      <Button size="lg" className="bg-blue-600 hover:bg-blue-700 w-full sm:w-auto">
                        <FileUp className="w-5 h-5 mr-2" />
                        Upload Your Resume
                      </Button>
                    </Link>
                    <Link href="/jdxr-analyser">
                      <Button variant="outline" size="lg" className="w-full sm:w-auto">
                        <FileText className="w-5 h-5 mr-2" />
                        Compare Resume with JD
                      </Button>
                    </Link>
                  </CardContent>
                </Card>

                {/* Workflow Cards */}
                <div className="grid gap-6 md:grid-cols-3">
                  <Card>
                    <CardHeader>
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400 mb-2">
                        <FileUp className="w-5 h-5" />
                      </div>
                      <CardTitle className="text-base">1. Resume Parsing</CardTitle>
                      <CardDescription className="text-xs leading-relaxed">
                        Extract structured education, work experience, and verified technical competencies.
                      </CardDescription>
                    </CardHeader>
                  </Card>

                  <Card>
                    <CardHeader>
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400 mb-2">
                        <BarChart3 className="w-5 h-5" />
                      </div>
                      <CardTitle className="text-base">2. Deterministic Scoring</CardTitle>
                      <CardDescription className="text-xs leading-relaxed">
                        Evaluate skill coverage and objective role alignment without hallucinations.
                      </CardDescription>
                    </CardHeader>
                  </Card>

                  <Card>
                    <CardHeader>
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400 mb-2">
                        <Briefcase className="w-5 h-5" />
                      </div>
                      <CardTitle className="text-base">3. Job Recommendations</CardTitle>
                      <CardDescription className="text-xs leading-relaxed">
                        Discover matching opportunities and prioritize specific actions to enhance your profile.
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </div>
              </div>
            )}

            {/* Platform Quick Launch Hub (Always Available) */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Career Tools & Actions
              </h3>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Link href="/#upload" className="group">
                  <Card className="h-full transition-all duration-200 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700">
                    <CardHeader className="p-5">
                      <FileUp className="w-6 h-6 text-blue-600 mb-2 group-hover:scale-105 transition-transform" />
                      <CardTitle className="text-sm">Upload Resume</CardTitle>
                      <CardDescription className="text-xs mt-1">
                        Upload or replace your PDF/DOCX resume file
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>

                <Link href="/analysis" className="group">
                  <Card className="h-full transition-all duration-200 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700">
                    <CardHeader className="p-5">
                      <BarChart3 className="w-6 h-6 text-indigo-600 mb-2 group-hover:scale-105 transition-transform" />
                      <CardTitle className="text-sm">In-Depth Analysis</CardTitle>
                      <CardDescription className="text-xs mt-1">
                        View skill breakdown, gap analysis, and AI enrichment
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>

                <Link href="/job-recommendation" className="group">
                  <Card className="h-full transition-all duration-200 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700">
                    <CardHeader className="p-5">
                      <Briefcase className="w-6 h-6 text-emerald-600 mb-2 group-hover:scale-105 transition-transform" />
                      <CardTitle className="text-sm flex items-center justify-between">
                        <span>Job Recommendations</span>
                        {savedJobsCount > 0 && (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                            {savedJobsCount} saved
                          </span>
                        )}
                      </CardTitle>
                      <CardDescription className="text-xs mt-1">
                        Browse positions aligned with your target skills
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>

                <Link href="/jdxr-analyser" className="group">
                  <Card className="h-full transition-all duration-200 hover:border-blue-300 hover:shadow-sm dark:hover:border-blue-700">
                    <CardHeader className="p-5">
                      <FileText className="w-6 h-6 text-purple-600 mb-2 group-hover:scale-105 transition-transform" />
                      <CardTitle className="text-sm">Compare with JD</CardTitle>
                      <CardDescription className="text-xs mt-1">
                        JDxR comparison between resume and job description
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

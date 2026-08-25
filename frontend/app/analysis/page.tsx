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
  AlertTriangle,
  Loader2,
  Sparkles,
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

type AIEnrichmentResult = {
  ai_status: 'disabled' | 'unavailable' | 'complete' | 'abstained' | 'grounding_failed' | 'invalid';
  ai?: {
    summary?: string;
    strengths?: Array<{ text: string }>;
    priority_gaps?: Array<{ text: string }>;
    learning_actions?: Array<{ text: string }>;
    resume_actions?: Array<{ text: string }>;
    interview_actions?: Array<{ text: string }>;
    improvements?: AIImprovementItem[];
    confidence_notes?: string[];
    refusal_or_abstention_reason?: string | null;
  } | null;
  error_code?: string | null;
};

type AIImprovementItem = {
  improvement_id: string;
  category: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  problem: string;
  recommendation: string;
  evidence_reference_ids: string[];
  knowledge_reference_ids: string[];
  action_type: string;
  fact_status: string;
};

export default function AnalysisPage() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [resumeFileId, setResumeFileId] = useState<string | null>(null);
  const [aiResult, setAiResult] = useState<AIEnrichmentResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [improvementResult, setImprovementResult] = useState<AIEnrichmentResult | null>(null);
  const [improvementLoading, setImprovementLoading] = useState(false);
  const [improvementError, setImprovementError] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

  useEffect(() => {
    // Load analysis data from localStorage
    const storedAnalysis = localStorage.getItem('resumeAnalysis');
    if (storedAnalysis) {
      try {
        const data = sanitizeAnalysisForStorage(JSON.parse(storedAnalysis));
        localStorage.setItem('resumeAnalysis', JSON.stringify(data));
        setAnalysisData(data);
        setResumeFileId(data?.metadata?.file_id || localStorage.getItem('resumeFileId'));
      } catch (error) {
        console.error('Error parsing analysis data:', error);
      }
    }
    if (!storedAnalysis) {
      setResumeFileId(localStorage.getItem('resumeFileId'));
    }
    setLoading(false);
  }, []);

  const generateAiGuidance = async () => {
    if (!resumeFileId) {
      setAiError('Upload a resume and complete deterministic analysis before requesting AI guidance.');
      return;
    }
    setAiLoading(true);
    setAiError(null);
    try {
      const response = await fetch(
        apiUrl + '/api/analysis/ai?file_id=' + encodeURIComponent(resumeFileId),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task: 'resume_career_guidance' }),
        },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'AI guidance is currently unavailable.');
      }
      setAiResult(data as AIEnrichmentResult);
    } catch (requestError) {
      setAiResult(null);
      setAiError(requestError instanceof Error ? requestError.message : 'AI guidance is currently unavailable.');
    } finally {
      setAiLoading(false);
    }
  };

  const generateResumeImprovements = async () => {
    if (!resumeFileId) {
      setImprovementError('Upload a resume and complete deterministic analysis before requesting improvements.');
      return;
    }
    setImprovementLoading(true);
    setImprovementError(null);
    try {
      const response = await fetch(
        apiUrl + '/api/analysis/ai/improvements?file_id=' + encodeURIComponent(resumeFileId),
        { method: 'POST' },
      );
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'AI improvement guidance is currently unavailable.');
      }
      setImprovementResult(data as AIEnrichmentResult);
    } catch (requestError) {
      setImprovementResult(null);
      setImprovementError(requestError instanceof Error ? requestError.message : 'AI improvement guidance is currently unavailable.');
    } finally {
      setImprovementLoading(false);
    }
  };

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
      skill_coverage: 62,
      skill_momentum: 62,
      readiness_actions_count: 3,
    };
  }, [analysisData]);
  
  const skillCoverage = metrics.skill_coverage ?? metrics.skill_momentum ?? 0;

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
            {overallInsights.weekChange != null ? (
              <span className="rounded-full bg-green-50 px-4 py-2 text-sm font-medium text-green-600 dark:bg-green-500/10 dark:text-green-300">
                {overallInsights.weekChange >= 0 ? `+${overallInsights.weekChange}` : overallInsights.weekChange}% vs last review
              </span>
            ) : (
              <span className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                Verified Profile Analysis
              </span>
            )}
          </div>
        </header>

        <section aria-labelledby="ai-guidance-heading">
          <Card className="border-indigo-200 bg-indigo-50/60 dark:border-indigo-500/30 dark:bg-indigo-500/10">
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle id="ai-guidance-heading" className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <Sparkles className="h-5 w-5 text-indigo-500" />
                  AI Career Guidance
                </CardTitle>
                <CardDescription className="dark:text-gray-300">
                  Optional grounded explanations and next steps based on this deterministic analysis.
                </CardDescription>
              </div>
              <Button
                type="button"
                onClick={generateAiGuidance}
                disabled={aiLoading || !resumeFileId}
                className="bg-indigo-600 hover:bg-indigo-700"
              >
                {aiLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                Generate AI Guidance
              </Button>
            </CardHeader>
            <CardContent>
              {aiLoading && <p className="text-sm text-gray-600 dark:text-gray-300">Generating grounded guidance...</p>}
              {!aiLoading && !aiResult && !aiError && (
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  AI guidance runs only when you request it. Your deterministic results remain available independently.
                </p>
              )}
              {!aiLoading && aiError && (
                <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4" />
                  <span>{aiError}</span>
                </div>
              )}
              {!aiLoading && aiResult?.ai_status === 'disabled' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">AI guidance is disabled. Deterministic analysis is unchanged.</p>
              )}
              {!aiLoading && aiResult?.ai_status === 'unavailable' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  AI guidance is unavailable right now. The deterministic analysis remains the source of truth.
                </p>
              )}
              {!aiLoading && aiResult?.ai_status === 'abstained' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  AI guidance abstained because the available evidence was insufficient.
                </p>
              )}
              {!aiLoading && aiResult?.ai_status === 'complete' && aiResult.ai && (
                <div className="space-y-5">
                  {aiResult.ai.summary && <p className="text-sm leading-6 text-gray-700 dark:text-gray-200">{aiResult.ai.summary}</p>}
                  <AIItems title="Strengths" items={aiResult.ai.strengths} />
                  <AIItems title="Priority Improvements" items={aiResult.ai.priority_gaps} />
                  <AIItems title="Learning Roadmap" items={aiResult.ai.learning_actions} />
                  <AIItems title="Resume Guidance" items={aiResult.ai.resume_actions} />
                  <AIItems title="Interview Preparation" items={aiResult.ai.interview_actions} />
                  {aiResult.ai.confidence_notes?.length ? (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{aiResult.ai.confidence_notes.join(' ')}</p>
                  ) : null}
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        <section aria-labelledby="ai-improvement-heading">
          <Card className="border-emerald-200 bg-emerald-50/60 dark:border-emerald-500/30 dark:bg-emerald-500/10">
            <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <CardTitle id="ai-improvement-heading" className="flex items-center gap-2 text-gray-900 dark:text-white">
                  <Sparkles className="h-5 w-5 text-emerald-600" />
                  AI Resume Improvement
                </CardTitle>
                <CardDescription className="dark:text-gray-300">
                  Evidence-based priorities for improving this resume. Deterministic scores remain unchanged.
                </CardDescription>
              </div>
              <Button
                type="button"
                onClick={generateResumeImprovements}
                disabled={improvementLoading || !resumeFileId}
                className="bg-emerald-600 hover:bg-emerald-700"
              >
                {improvementLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                Generate Resume Improvements
              </Button>
            </CardHeader>
            <CardContent>
              {improvementLoading && <p className="text-sm text-gray-600 dark:text-gray-300">Generating improvement guidance...</p>}
              {!improvementLoading && !improvementResult && !improvementError && (
                <p className="text-sm text-gray-600 dark:text-gray-300">Request improvement guidance when you are ready to review your evidence.</p>
              )}
              {!improvementLoading && improvementError && (
                <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4" />
                  <span>{improvementError}</span>
                </div>
              )}
              {!improvementLoading && improvementResult?.ai_status === 'disabled' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">AI improvement guidance is disabled. Deterministic analysis is unchanged.</p>
              )}
              {!improvementLoading && improvementResult?.ai_status === 'unavailable' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">AI improvement guidance is temporarily unavailable. Your deterministic analysis is still available.</p>
              )}
              {!improvementLoading && improvementResult?.ai_status === 'grounding_failed' && (
                <p className="text-sm text-gray-600 dark:text-gray-300">AI guidance could not be safely validated. Your deterministic results remain available.</p>
              )}
              {!improvementLoading && improvementResult?.ai_status === 'complete' && improvementResult.ai && (
                <div className="space-y-4">
                  {improvementResult.ai.summary && <p className="text-sm leading-6 text-gray-700 dark:text-gray-200">{improvementResult.ai.summary}</p>}
                  <AIImprovementItems items={improvementResult.ai.improvements} />
                </div>
              )}
            </CardContent>
          </Card>
        </section>

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
                Skill Coverage
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{skillCoverage}%</p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Current resume evidence across skills, projects, and experience.
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
                Skill evidence scores based on resume sections.
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

function sanitizeAnalysisForStorage(analysis: any) {
  if (!analysis || typeof analysis !== 'object') return analysis;
  const candidateInfo = analysis.candidate_info && typeof analysis.candidate_info === 'object'
    ? analysis.candidate_info
    : {};
  const { name: _name, email: _email, phone: _phone, ...safeCandidateInfo } = candidateInfo;
  return { ...analysis, candidate_info: safeCandidateInfo };
}

function AIItems({ title, items }: { title: string; items?: Array<{ text: string }> }) {
  if (!items?.length) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
      <ul className="mt-2 space-y-2">
        {items.map((item, index) => (
          <li key={title + '-' + index} className="rounded-lg border border-indigo-100 bg-white/70 px-3 py-2 text-sm text-gray-700 dark:border-indigo-500/20 dark:bg-gray-900/40 dark:text-gray-200">
            {item.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AIImprovementItems({ items }: { items?: AIImprovementItem[] }) {
  if (!items?.length) return <p className="text-sm text-gray-600 dark:text-gray-300">No grounded improvement priorities were available.</p>;
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Priorities</h3>
      {items.map((item) => (
        <article key={item.improvement_id} className="rounded-lg border border-emerald-100 bg-white/70 p-4 dark:border-emerald-500/20 dark:bg-gray-900/40">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold text-gray-900 dark:text-white">{item.title}</h4>
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200">{item.priority}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">{item.fact_status.replaceAll('_', ' ')}</span>
          </div>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-200"><strong>Why:</strong> {item.problem}</p>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-200"><strong>Action:</strong> {item.recommendation}</p>
          {item.evidence_reference_ids.length > 0 && (
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Evidence: {item.evidence_reference_ids.join(', ')}</p>
          )}
        </article>
      ))}
      <p className="text-xs text-gray-500 dark:text-gray-400">Only add information that is true and verifiable.</p>
    </div>
  );
}

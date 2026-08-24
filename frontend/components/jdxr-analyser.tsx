'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Loader2, Sparkles, Target, Upload, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { JobMatchResponse, JobMatchResults } from '@/components/job-match-panel';

type JdxrSession = {
  session_id: string;
  status: string;
  jd: {
    status?: string;
    filename?: string;
    job_title?: string | null;
    company?: string | null;
    required_count?: number;
    preferred_count?: number;
    required_skill_count?: number;
    preferred_skill_count?: number;
    capability_count?: number;
    eligibility_count?: number;
    availability_count?: number;
    experience_count?: number;
    education_count?: number;
  };
  resume: {
    status?: string;
    filename?: string;
    size_bytes?: number;
    experience_count?: number;
    project_count?: number;
    education_count?: number;
    certification_count?: number;
  };
  has_match_result?: boolean;
};

type JdxrResponse = {
  success: boolean;
  session: JdxrSession;
  job?: JobMatchResponse['job'];
  match?: JobMatchResponse['match'];
};

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
  } | null;
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

const SESSION_KEY = 'jdxrSessionId';
const RESULT_KEY = 'jdxrResult';
const MAX_FILE_SIZE = 5 * 1024 * 1024;

export default function JdxrAnalyser() {
  const [session, setSession] = useState<JdxrSession | null>(null);
  const [jdText, setJdText] = useState('');
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [result, setResult] = useState<JdxrResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [aiResult, setAiResult] = useState<AIEnrichmentResult | null>(null);
  const [improvementResult, setImprovementResult] = useState<AIEnrichmentResult | null>(null);
  const [improvementLoading, setImprovementLoading] = useState(false);
  const [improvementError, setImprovementError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
  const jdValid = session?.jd?.status === 'valid';
  const resumeValid = session?.resume?.status === 'valid';
  const canCompare = Boolean(session && jdValid && resumeValid && !isLoading);

  useEffect(() => {
    let cancelled = false;

    const loadSession = async () => {
      const storedSessionId = localStorage.getItem(SESSION_KEY);
      try {
        let loadedSession: JdxrSession;
        if (storedSessionId) {
          const response = await fetch(`${apiUrl}/api/jdxr/session/${storedSessionId}`);
          if (!response.ok) {
            localStorage.removeItem(SESSION_KEY);
            localStorage.removeItem(RESULT_KEY);
            loadedSession = await createSession(apiUrl);
          } else {
            loadedSession = (await response.json()).session;
          }
        } else {
          loadedSession = await createSession(apiUrl);
        }

        if (cancelled) return;
        setSession(loadedSession);
        localStorage.setItem(SESSION_KEY, loadedSession.session_id);

        const savedResult = localStorage.getItem(RESULT_KEY);
        if (savedResult) {
          try {
            const parsedResult = JSON.parse(savedResult) as JdxrResponse;
            if (parsedResult.session?.session_id === loadedSession.session_id && parsedResult.match) {
              setResult(parsedResult);
            } else {
              localStorage.removeItem(RESULT_KEY);
            }
          } catch {
            localStorage.removeItem(RESULT_KEY);
          }
        }
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : 'Unable to start a JDxR session.');
      }
    };

    loadSession();
    return () => {
      cancelled = true;
    };
  }, [apiUrl]);

  const clearResult = () => {
    setResult(null);
    setAiResult(null);
    localStorage.removeItem(RESULT_KEY);
  };

  const handleJdFile = (file: File | null) => {
    if (!file) return;
    if (!['.pdf', '.docx', '.doc'].some((extension) => file.name.toLowerCase().endsWith(extension))) {
      setError('Please upload a PDF, DOCX, or DOC job description.');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError('Job description files are limited to 5 MB.');
      return;
    }
    setError(null);
    setJdFile(file);
    clearResult();
  };

  const handleResumeFile = (file: File | null) => {
    if (!file) return;
    if (!['.pdf', '.docx', '.doc'].some((extension) => file.name.toLowerCase().endsWith(extension))) {
      setError('Please upload a PDF, DOCX, or DOC resume.');
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError('Resume files are limited to 5 MB.');
      return;
    }
    setError(null);
    setResumeFile(file);
    clearResult();
  };

  const submitJd = async () => {
    if (!session) return;
    if (!jdText.trim() && !jdFile) {
      setError('Paste a job description or upload a JD document first.');
      return;
    }
    if (jdText.trim() && jdFile) {
      setError('Use either pasted text or one JD document, not both.');
      return;
    }

    setIsLoading(true);
    setLoadingLabel('Validating job description...');
    setError(null);
    try {
      const formData = new FormData();
      if (jdText.trim()) formData.append('job_description', jdText.trim());
      if (jdFile) formData.append('file', jdFile);
      const response = await fetch(`${apiUrl}/api/jdxr/session/${session.session_id}/jd`, { method: 'POST', body: formData });
      const data = await readResponse(response);
      if (!response.ok) throw new Error(data.message || 'This does not appear to be a valid job description.');
      setSession(data.session);
      setJdFile(null);
      clearResult();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to validate this job description.');
    } finally {
      setIsLoading(false);
      setLoadingLabel('');
    }
  };

  const submitResume = async () => {
    if (!session || !resumeFile) return;
    setIsLoading(true);
    setLoadingLabel('Validating resume...');
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', resumeFile);
      const response = await fetch(`${apiUrl}/api/jdxr/session/${session.session_id}/resume`, { method: 'POST', body: formData });
      const data = await readResponse(response);
      if (!response.ok) throw new Error(data.message || 'Please upload a valid resume.');
      setSession(data.session);
      setResumeFile(null);
      clearResult();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to validate this resume.');
    } finally {
      setIsLoading(false);
      setLoadingLabel('');
    }
  };

  const compare = async () => {
    if (!session || !canCompare) return;
    setIsLoading(true);
    setLoadingLabel('Comparing resume with job...');
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/api/jdxr/session/${session.session_id}/analyze`, { method: 'POST' });
      const data = await readResponse(response);
      if (!response.ok) throw new Error(data.message || 'Unable to compare this resume with the job.');
      setSession(data.session);
      setResult(data);
      localStorage.setItem(RESULT_KEY, JSON.stringify(data));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to compare this resume with the job.');
    } finally {
      setIsLoading(false);
      setLoadingLabel('');
    }
  };

  const generateAiExplanation = async () => {
    if (!session || !result?.match) return;
    setIsLoading(true);
    setLoadingLabel('Generating grounded AI explanation...');
    setError(null);
    try {
      const response = await fetch(apiUrl + '/api/jdxr/session/' + session.session_id + '/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: 'jdxr_match_explanation' }),
      });
      const data = await readResponse(response);
      if (!response.ok || data.success === false) {
        throw new Error(data.message || 'AI explanation is currently unavailable.');
      }
      setAiResult(data as AIEnrichmentResult);
    } catch (requestError) {
      setAiResult(null);
      setError(requestError instanceof Error ? requestError.message : 'AI explanation is currently unavailable.');
    } finally {
      setIsLoading(false);
      setLoadingLabel('');
    }
  };

  const generateResumeImprovements = async () => {
    if (!session || !result?.match) return;
    setImprovementLoading(true);
    setImprovementError(null);
    try {
      const response = await fetch(apiUrl + '/api/jdxr/session/' + session.session_id + '/ai/improvements', {
        method: 'POST',
      });
      const data = await readResponse(response);
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

  const steps = useMemo(() => [
    { label: 'Job Description', complete: jdValid },
    { label: 'Resume', complete: resumeValid },
    { label: 'Compare', complete: Boolean(result?.match) },
    { label: 'Results', complete: Boolean(result?.match) },
  ], [jdValid, resumeValid, result]);

  return (
    <div className="space-y-6">
      <Card className="dark:border-gray-800 dark:bg-gray-900/60">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-white">JDxR Analyser</CardTitle>
          <CardDescription className="dark:text-gray-400">
            Compare your resume against a specific job and discover what to improve before you apply.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-4">
            {steps.map((step, index) => (
              <div key={step.label} className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${step.complete ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200' : 'border-gray-200 bg-gray-50 text-gray-600 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-300'}`}>
                {step.complete ? <CheckCircle2 className="h-4 w-4" /> : <span className="flex h-4 w-4 items-center justify-center rounded-full border text-[10px]">{index + 1}</span>}
                {step.label}
              </div>
            ))}
          </div>

          <section className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Step 1 — Job Description</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">Paste the job description or upload one document.</p>
            </div>
            <textarea
              value={jdText}
              onChange={(event) => { setJdText(event.target.value); clearResult(); }}
              disabled={isLoading || jdValid}
              rows={9}
              placeholder="Paste the full job description here..."
              className="min-h-[220px] w-full resize-y rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500 disabled:opacity-70 dark:border-gray-700 dark:bg-gray-950 dark:text-white"
            />
            {!jdValid && (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-700 hover:border-blue-400 dark:border-gray-700 dark:text-gray-200">
                  <Upload className="h-4 w-4 text-blue-500" />
                  Upload JD PDF/DOCX/DOC
                  <input type="file" accept=".pdf,.docx,.doc" className="sr-only" disabled={isLoading} onChange={(event) => handleJdFile(event.target.files?.[0] || null)} />
                </label>
                {jdFile && <FileChip file={jdFile} onRemove={() => setJdFile(null)} />}
                <Button type="button" onClick={submitJd} disabled={isLoading || (!jdText.trim() && !jdFile)}>
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Target className="mr-2 h-4 w-4" />}
                  Validate Job Description
                </Button>
              </div>
            )}
            {jdValid && <JdConfirmation session={session} />}
          </section>

          <section className={`space-y-4 border-t pt-5 dark:border-gray-800 ${jdValid ? '' : 'opacity-50'}`}>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Step 2 — Upload Your Resume</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">This resume belongs only to this JDxR session.</p>
            </div>
            {!resumeValid && (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-700 hover:border-blue-400 dark:border-gray-700 dark:text-gray-200">
                  <Upload className="h-4 w-4 text-blue-500" />
                  Browse Resume PDF/DOCX/DOC
                  <input type="file" accept=".pdf,.docx,.doc" className="sr-only" disabled={!jdValid || isLoading} onChange={(event) => handleResumeFile(event.target.files?.[0] || null)} />
                </label>
                {resumeFile && <FileChip file={resumeFile} onRemove={() => setResumeFile(null)} />}
                <Button type="button" onClick={submitResume} disabled={!jdValid || isLoading || !resumeFile}>
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
                  Validate Resume
                </Button>
              </div>
            )}
            {resumeValid && <ResumeConfirmation session={session} />}
          </section>

          <section className="border-t pt-5 dark:border-gray-800">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Step 3 — Compare</h2>
            <Button type="button" onClick={compare} disabled={!canCompare} className="mt-3 bg-blue-600 hover:bg-blue-700">
              {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Target className="mr-2 h-4 w-4" />}
              Compare Resume with Job
            </Button>
            {loadingLabel && <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{loadingLabel}</p>}
          </section>

          <section className={`border-t pt-5 dark:border-gray-800 ${result?.match ? '' : 'opacity-50'}`}>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Step 4 — Results</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              {result?.match ? 'Match results are ready below.' : 'Results will appear after a successful comparison.'}
            </p>
          </section>

          {error && <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200"><AlertTriangle className="mt-0.5 h-4 w-4" />{error}</div>}
        </CardContent>
      </Card>

      {result?.match && <JobMatchResults result={{ success: true, message: 'Job match analysis completed successfully', job: result.job || {}, match: result.match }} />}
      {result?.match && (
        <AIExplanationPanel result={aiResult} loading={isLoading} onGenerate={generateAiExplanation} />
      )}
      {result?.match && (
        <AIImprovementPanel
          result={improvementResult}
          loading={improvementLoading}
          error={improvementError}
          onGenerate={generateResumeImprovements}
        />
      )}
    </div>
  );
}

async function createSession(apiUrl: string): Promise<JdxrSession> {
  const response = await fetch(`${apiUrl}/api/jdxr/session`, { method: 'POST' });
  const data = await readResponse(response);
  if (!response.ok) throw new Error(data.message || 'Unable to start a JDxR session.');
  return data.session;
}

async function readResponse(response: Response): Promise<any> {
  const data = await response.json().catch(() => ({}));
  return data;
}

function FileChip({ file, onRemove }: { file: File; onRemove: () => void }) {
  return <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700"><span className="max-w-[220px] truncate">{file.name}</span><span className="text-xs text-gray-500">{formatBytes(file.size)}</span><button type="button" onClick={onRemove} aria-label={`Remove ${file.name}`}><X className="h-4 w-4 text-gray-500" /></button></div>;
}

function JdConfirmation({ session }: { session: JdxrSession }) {
  const jd = session.jd;
  return <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10"><p className="font-semibold text-emerald-800 dark:text-emerald-100">Job Description Recognized</p><p className="mt-1 text-sm text-emerald-700 dark:text-emerald-200">{jd.job_title || jd.filename || 'Validated job description'}{jd.company ? ` · ${jd.company}` : ''}</p><p className="mt-2 text-xs text-emerald-700 dark:text-emerald-200">Requirements detected: {jd.required_count || 0} required · {jd.preferred_count || 0} preferred · {jd.required_skill_count || 0} required skills · {jd.preferred_skill_count || 0} preferred skills · {jd.experience_count || 0} experience · {jd.education_count || 0} education</p></div>;
}

function ResumeConfirmation({ session }: { session: JdxrSession }) {
  const resume = session.resume;
  return <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10"><p className="font-semibold text-emerald-800 dark:text-emerald-100">Resume Recognized</p><p className="mt-1 text-sm text-emerald-700 dark:text-emerald-200">{resume.filename}</p><p className="mt-2 text-xs text-emerald-700 dark:text-emerald-200">{resume.experience_count || 0} experiences · {resume.project_count || 0} projects · {resume.education_count || 0} education · {resume.certification_count || 0} certifications</p></div>;
}

function AIExplanationPanel({
  result,
  loading,
  onGenerate,
}: {
  result: AIEnrichmentResult | null;
  loading: boolean;
  onGenerate: () => void;
}) {
  return (
    <Card className="border-indigo-200 bg-indigo-50/60 dark:border-indigo-500/30 dark:bg-indigo-500/10">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
            <Sparkles className="h-5 w-5 text-indigo-500" />
            AI Match Explanation
          </CardTitle>
          <CardDescription className="dark:text-gray-300">
            Optional grounded guidance. The deterministic Job Match Score above remains authoritative.
          </CardDescription>
        </div>
        <Button type="button" onClick={onGenerate} disabled={loading} className="bg-indigo-600 hover:bg-indigo-700">
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
          Generate AI Explanation
        </Button>
      </CardHeader>
      <CardContent>
        {loading && <p className="text-sm text-gray-600 dark:text-gray-300">Generating grounded explanation...</p>}
        {!loading && !result && (
          <p className="text-sm text-gray-600 dark:text-gray-300">
            AI explanation runs only when requested and never changes the deterministic match.
          </p>
        )}
        {!loading && result?.ai_status === 'disabled' && (
          <p className="text-sm text-gray-600 dark:text-gray-300">AI explanation is disabled. The deterministic match is unchanged.</p>
        )}
        {!loading && result?.ai_status === 'unavailable' && (
          <p className="text-sm text-gray-600 dark:text-gray-300">AI explanation is unavailable right now. The deterministic match remains available.</p>
        )}
        {!loading && result?.ai_status === 'abstained' && (
          <p className="text-sm text-gray-600 dark:text-gray-300">AI explanation abstained because the available evidence was insufficient.</p>
        )}
        {!loading && result?.ai_status === 'grounding_failed' && (
          <p className="text-sm text-gray-600 dark:text-gray-300">AI guidance could not be safely validated. The deterministic match remains available.</p>
        )}
        {!loading && result?.ai_status === 'complete' && result.ai && (
          <div className="space-y-5">
            {result.ai.summary && <p className="text-sm leading-6 text-gray-700 dark:text-gray-200">{result.ai.summary}</p>}
            <AIItems title="Strengths" items={result.ai.strengths} />
            <AIItems title="Priority Gaps" items={result.ai.priority_gaps} />
            <AIItems title="Resume Improvements" items={result.ai.resume_actions} />
            <AIItems title="Interview Preparation" items={result.ai.interview_actions} />
            {result.ai.confidence_notes?.length ? (
              <p className="text-xs text-gray-500 dark:text-gray-400">{result.ai.confidence_notes.join(' ')}</p>
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AIImprovementPanel({
  result,
  loading,
  error,
  onGenerate,
}: {
  result: AIEnrichmentResult | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
}) {
  return (
    <Card className="border-emerald-200 bg-emerald-50/60 dark:border-emerald-500/30 dark:bg-emerald-500/10">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
            <Sparkles className="h-5 w-5 text-emerald-600" />
            Improve My Resume for This Job
          </CardTitle>
          <CardDescription className="dark:text-gray-300">
            Grounded suggestions based on this resume and the selected job. The deterministic match remains authoritative.
          </CardDescription>
        </div>
        <Button type="button" onClick={onGenerate} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
          Generate Resume Improvements
        </Button>
      </CardHeader>
      <CardContent>
        {loading && <p className="text-sm text-gray-600 dark:text-gray-300">Generating improvement guidance...</p>}
        {!loading && error && (
          <div className="flex items-start gap-2 text-sm text-red-700 dark:text-red-200"><AlertTriangle className="mt-0.5 h-4 w-4" />{error}</div>
        )}
        {!loading && !error && !result && (
          <p className="text-sm text-gray-600 dark:text-gray-300">Request targeted improvement guidance after reviewing the deterministic match.</p>
        )}
        {!loading && result?.ai_status === 'disabled' && <p className="text-sm text-gray-600 dark:text-gray-300">AI improvement guidance is disabled. The deterministic match is unchanged.</p>}
        {!loading && result?.ai_status === 'unavailable' && <p className="text-sm text-gray-600 dark:text-gray-300">AI improvement guidance is temporarily unavailable. Your deterministic match is still available.</p>}
        {!loading && result?.ai_status === 'grounding_failed' && <p className="text-sm text-gray-600 dark:text-gray-300">AI guidance could not be safely validated. Your deterministic match remains available.</p>}
        {!loading && result?.ai_status === 'complete' && result.ai && (
          <div className="space-y-4">
            {result.ai.summary && <p className="text-sm leading-6 text-gray-700 dark:text-gray-200">{result.ai.summary}</p>}
            <AIImprovementItems items={result.ai.improvements} />
            <p className="text-xs text-gray-500 dark:text-gray-400">Only add information that is true and verifiable.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AIImprovementItems({ items }: { items?: AIImprovementItem[] }) {
  if (!items?.length) return <p className="text-sm text-gray-600 dark:text-gray-300">No grounded improvement priorities were available.</p>;
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Top Changes</h3>
      {items.map((item) => (
        <article key={item.improvement_id} className="rounded-lg border border-emerald-100 bg-white/70 p-4 dark:border-emerald-500/20 dark:bg-gray-900/40">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-semibold text-gray-900 dark:text-white">{item.title}</h4>
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200">{item.priority}</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">{item.fact_status.replaceAll('_', ' ')}</span>
          </div>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-200"><strong>Why:</strong> {item.problem}</p>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-200"><strong>Action:</strong> {item.recommendation}</p>
          {item.evidence_reference_ids.length > 0 && <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Evidence: {item.evidence_reference_ids.join(', ')}</p>}
        </article>
      ))}
    </div>
  );
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

function formatBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

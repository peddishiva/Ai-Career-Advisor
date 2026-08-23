'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileText, Loader2, Target, Upload, X } from 'lucide-react';

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

function formatBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

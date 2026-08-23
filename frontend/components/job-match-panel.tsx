'use client';

import { useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ListChecks,
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type SkillItem = {
  skill: string;
  status: string;
  importance: string;
  reason: string;
};

type SkillGroup = {
  matched?: SkillItem[];
  partial?: SkillItem[];
  missing?: SkillItem[];
};

type Gap = {
  type: string;
  requirement: string;
  reason: string;
};

type Recommendation = {
  title: string;
  description: string;
};

export type MatchResult = {
  score: number;
  readiness: string;
  breakdown: Record<string, number>;
  required_skills: SkillGroup;
  preferred_skills: SkillGroup;
  experience_alignment: any;
  project_alignment: any;
  education_alignment: any;
  certification_alignment: any;
  eligibility_alignment: any;
  qualification_alignment: any;
  availability_alignment: any;
  responsibility_alignment: any;
  critical_gaps: Gap[];
  non_critical_gaps: Gap[];
  recommendations: Recommendation[];
  resume_alignment: Gap[];
};

export type JobMatchResponse = {
  success: boolean;
  message: string;
  job: {
    job_title?: string | null;
    company?: string | null;
    location?: string | null;
    employment_type?: string | null;
  };
  match: MatchResult;
};

export function JobMatchResults({ result }: { result: JobMatchResponse }) {
  const match = result.match;
  const jobMeta = useMemo(
    () => [result.job.company, result.job.location, result.job.employment_type].filter(Boolean),
    [result.job.company, result.job.location, result.job.employment_type],
  );

  return (
    <div className="space-y-6">
      <Card className="dark:bg-gray-900/60 dark:border-gray-800">
        <CardHeader>
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              {result.job.job_title && (
                <CardTitle className="text-2xl text-gray-900 dark:text-white">{result.job.job_title}</CardTitle>
              )}
              {jobMeta.length > 0 && (
                <CardDescription className="mt-2 dark:text-gray-400">{jobMeta.join(' • ')}</CardDescription>
              )}
            </div>
            <div className="grid min-w-[220px] grid-cols-2 gap-3">
              <ScoreBox label="Job Match Score" value={`${match.score} / 100`} />
              <ScoreBox label="Readiness" value={match.readiness} />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(match.breakdown || {}).map(([key, value]) => (
              <div key={key} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-950">
                <p className="text-xs capitalize text-gray-500 dark:text-gray-400">{key.replace(/_/g, ' ')}</p>
                <p className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">{value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <SkillCard title="Required Skills" group={match.required_skills} />
        <SkillCard title="Preferred Skills" group={match.preferred_skills} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AlignmentCard title="Experience Alignment" alignment={match.experience_alignment} />
        <ProjectAlignmentCard alignment={match.project_alignment} />
        <AlignmentCard title="Education Alignment" alignment={match.education_alignment} />
        <AlignmentCard title="Certification Alignment" alignment={match.certification_alignment} />
        <AlignmentCard title="Eligibility Alignment" alignment={match.eligibility_alignment} />
        <AlignmentCard title="Required Capability / Knowledge" alignment={match.qualification_alignment} />
        <AlignmentCard title="Availability Alignment" alignment={match.availability_alignment} />
        <ResponsibilityAlignmentCard alignment={match.responsibility_alignment} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <GapCard title="Critical Gaps" gaps={match.critical_gaps} tone="critical" />
        <GapCard title="Non-Critical Gaps" gaps={match.non_critical_gaps} tone="optional" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <GapCard title="Resume Alignment Suggestions" gaps={match.resume_alignment} tone="aligned" />
        <RecommendationCard recommendations={match.recommendations} />
      </div>
    </div>
  );
}

function ScoreBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-center dark:border-blue-500/20 dark:bg-blue-500/10">
      <p className="text-xs font-medium uppercase tracking-wide text-blue-700 dark:text-blue-200">{label}</p>
      <p className="mt-1 text-xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

function SkillCard({ title, group }: { title: string; group: SkillGroup }) {
  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-white">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <SkillList title="Matched" items={group?.matched || []} tone="matched" />
        <SkillList title="Partial" items={group?.partial || []} tone="partial" />
        <SkillList title="Missing" items={group?.missing || []} tone="missing" />
      </CardContent>
    </Card>
  );
}

function SkillList({ title, items, tone }: { title: string; items: SkillItem[]; tone: 'matched' | 'partial' | 'missing' }) {
  const toneClass =
    tone === 'matched'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-200 dark:border-emerald-500/20'
      : tone === 'partial'
        ? 'bg-amber-50 text-amber-700 border-amber-100 dark:bg-amber-500/10 dark:text-amber-100 dark:border-amber-500/20'
        : 'bg-red-50 text-red-700 border-red-100 dark:bg-red-500/10 dark:text-red-200 dark:border-red-500/20';

  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-200">{title}</h4>
      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={`${title}-${item.skill}`} className={`rounded-lg border px-3 py-2 text-sm ${toneClass}`}>
              <p className="font-semibold">{item.skill}</p>
              <p className="mt-1 text-xs opacity-90">{item.reason}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">None</p>
      )}
    </div>
  );
}

function AlignmentCard({ title, alignment }: { title: string; alignment: any }) {
  const requirements = alignment?.requirements || [];

  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-white">{title}</CardTitle>
        {alignment?.status && <CardDescription className="capitalize dark:text-gray-400">Status: {alignment.status.replace(/_/g, ' ')}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        {alignment?.reason && <p>{alignment.reason}</p>}
        {requirements.length > 0 ? (
          <div className="space-y-3">
            {requirements.map((item: any, index: number) => (
              <div key={`${title}-${index}`} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-950">
                {item.requirement && <p className="font-medium text-gray-900 dark:text-white">Job requirement: {item.requirement}</p>}
                {item.resume_evidence && (
                  <p className="mt-1 text-gray-600 dark:text-gray-300">
                    Candidate: {formatEvidence(item.resume_evidence)}
                  </p>
                )}
                {item.required_years != null && (
                  <p className="mt-1 text-gray-600 dark:text-gray-300">
                    Years: {item.candidate_years ?? 'insufficient evidence'} / {item.required_years} required
                  </p>
                )}
                {item.reason && <p className="mt-1 text-gray-600 dark:text-gray-300">{item.reason}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No explicit job requirement was provided.</p>
        )}
      </CardContent>
    </Card>
  );
}

function ProjectAlignmentCard({ alignment }: { alignment: any }) {
  const projects = alignment?.matched_projects || [];

  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-white">Project Alignment</CardTitle>
        <CardDescription className="dark:text-gray-400">Score: {alignment?.score ?? 0}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        {alignment?.reason && <p>{alignment.reason}</p>}
        {projects.length > 0 ? (
          projects.map((project: any, index: number) => (
            <div key={`${project.title}-${index}`} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-950">
              <p className="font-medium text-gray-900 dark:text-white">{project.title || 'Project evidence'}</p>
              <p className="mt-1 text-gray-600 dark:text-gray-300">
                Matched: {(project.matched_skills || []).join(', ')}
              </p>
            </div>
          ))
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No matching project evidence was found.</p>
        )}
      </CardContent>
    </Card>
  );
}

function ResponsibilityAlignmentCard({ alignment }: { alignment: any }) {
  const items = alignment?.items || [];
  if (!alignment || (!alignment.reason && items.length === 0)) {
    return null;
  }

  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-gray-900 dark:text-white">
          <ListChecks className="h-5 w-5 text-blue-500" />
          Responsibility Alignment
        </CardTitle>
        <CardDescription className="capitalize dark:text-gray-400">
          Score: {alignment.score ?? 0}
          {alignment.status ? ` • Status: ${String(alignment.status).replace(/_/g, ' ')}` : ''}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
        {alignment.reason && <p>{alignment.reason}</p>}
        {items.length > 0 ? (
          <div className="space-y-3">
            {items.map((item: any, index: number) => (
              <div key={`${item.requirement || 'responsibility'}-${index}`} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-950">
                {item.requirement && <p className="font-medium text-gray-900 dark:text-white">{item.requirement}</p>}
                <div className="mt-2 flex flex-wrap gap-2 text-xs">
                  {item.status && (
                    <span className="rounded-full bg-blue-50 px-2 py-1 font-medium capitalize text-blue-700 dark:bg-blue-500/10 dark:text-blue-200">
                      {String(item.status).replace(/_/g, ' ')}
                    </span>
                  )}
                  {item.score != null && (
                    <span className="rounded-full bg-gray-100 px-2 py-1 font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                      Score: {item.score}
                    </span>
                  )}
                </div>
                {item.reason && <p className="mt-2 text-gray-600 dark:text-gray-300">{item.reason}</p>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No explicit job responsibilities were provided.</p>
        )}
      </CardContent>
    </Card>
  );
}

function GapCard({ title, gaps, tone }: { title: string; gaps: Gap[]; tone: 'critical' | 'optional' | 'aligned' }) {
  const iconClass =
    tone === 'critical'
      ? 'text-red-500'
      : tone === 'aligned'
        ? 'text-emerald-500'
        : 'text-amber-500';

  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-white">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {gaps && gaps.length > 0 ? (
          <div className="space-y-3">
            {gaps.map((gap, index) => (
              <div key={`${gap.type}-${gap.requirement}-${index}`} className="flex gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm dark:border-gray-800 dark:bg-gray-950">
                {tone === 'aligned' ? <CheckCircle2 className={`mt-0.5 h-4 w-4 ${iconClass}`} /> : <AlertTriangle className={`mt-0.5 h-4 w-4 ${iconClass}`} />}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{gap.requirement}</p>
                  <p className="mt-1 text-gray-600 dark:text-gray-300">{gap.reason}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">None</p>
        )}
      </CardContent>
    </Card>
  );
}

function RecommendationCard({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <Card className="dark:bg-gray-900/60 dark:border-gray-800">
      <CardHeader>
        <CardTitle className="text-gray-900 dark:text-white">Personalized Recommendations</CardTitle>
      </CardHeader>
      <CardContent>
        {recommendations && recommendations.length > 0 ? (
          <ol className="space-y-3">
            {recommendations.map((recommendation, index) => (
              <li key={`${recommendation.title}-${index}`} className="flex gap-3 text-sm">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700 dark:bg-blue-500/10 dark:text-blue-200">
                  {index + 1}
                </span>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{recommendation.title}</p>
                  <p className="mt-1 text-gray-600 dark:text-gray-300">{recommendation.description}</p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">None</p>
        )}
      </CardContent>
    </Card>
  );
}

function formatEvidence(evidence: any): string {
  if (typeof evidence === 'string') {
    return evidence;
  }
  if (Array.isArray(evidence)) {
    return evidence.map(formatEvidence).join(', ');
  }
  if (evidence && typeof evidence === 'object') {
    return Object.values(evidence).filter(Boolean).join(' ');
  }
  return 'No candidate evidence';
}

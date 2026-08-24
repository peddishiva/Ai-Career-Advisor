"""Deterministic facts used by the Phase 3D improvement boundary."""

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from config.roles import ROLE_DEFINITIONS
from config.scoring_config import IMPACT_ACTION_VERBS
from config.skill_aliases import get_canonical_skill, satisfies_skill
from utils.normalization import extract_matched_skills, normalize_skill_list


class ImprovementFactsBuilder:
    """Derive improvement opportunities without model inference or scoring changes."""

    _METRIC_RE = re.compile(
        r"(?:\b\d+(?:\.\d+)?\s*(?:%|percent|users?|requests?|ms|milliseconds?|seconds?|minutes?|hours?|days?|x|times)\b|"
        r"\b(?:increased|reduced|improved|saved|grew|cut)\b[^.\n]{0,80}\b\d+(?:\.\d+)?\b)",
        re.IGNORECASE,
    )

    def build_resume(self, parsed_resume: Mapping[str, Any], analysis: Mapping[str, Any]) -> Dict[str, Any]:
        top_role = (analysis.get("role_matches") or [{}])[0] if isinstance(analysis, Mapping) else {}
        role_title = top_role.get("title") if isinstance(top_role, Mapping) else None
        role_definition = ROLE_DEFINITIONS.get(role_title, {}) if role_title else {}
        target_skills = self._unique(
            [
                *(role_definition.get("required_skills") or []),
                *(role_definition.get("preferred_skills") or []),
                *(parsed_resume.get("skills") or []),
            ]
        )
        facts = self._base_facts(parsed_resume, target_skills, None)
        facts["mode"] = "resume_analysis"
        facts["top_role"] = role_title
        facts["role_match"] = top_role.get("match") if isinstance(top_role, Mapping) else None
        facts["opportunities"] = self._resume_opportunities(
            parsed_resume,
            analysis,
            facts,
            role_definition,
        )
        return facts

    def build_jdxr(
        self,
        parsed_resume: Mapping[str, Any],
        parsed_jd: Mapping[str, Any],
        match_result: Mapping[str, Any],
    ) -> Dict[str, Any]:
        jd_skills = [*(parsed_jd.get("required_skills") or []), *(parsed_jd.get("preferred_skills") or [])]
        target_skills = self._unique([*jd_skills, *(parsed_resume.get("skills") or [])])
        facts = self._base_facts(parsed_resume, target_skills, parsed_jd)
        facts["mode"] = "jdxr"
        facts["job_title"] = parsed_jd.get("job_title")
        facts["education_alignment"] = self._alignment_snapshot(match_result.get("education_alignment"))
        facts["eligibility_alignment"] = self._alignment_snapshot(match_result.get("eligibility_alignment"))
        facts["opportunities"] = self._jdxr_opportunities(
            parsed_resume,
            parsed_jd,
            match_result,
            facts,
        )
        return facts

    def _base_facts(
        self,
        parsed_resume: Mapping[str, Any],
        target_skills: Iterable[str],
        parsed_jd: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        target = self._unique(target_skills)
        skill_evidence = [self._skill_evidence(skill, parsed_resume, parsed_jd) for skill in target]
        projects = self._project_facts(parsed_resume, parsed_jd)
        experience = self._experience_facts(parsed_resume, parsed_jd)
        return {
            "version": "phase3d.facts.v1",
            "skills": skill_evidence,
            "skills_needing_evidence": [
                item["skill"]
                for item in skill_evidence
                if item["evidence_strength"] in {"NOT_FOUND", "SKILL_LIST_ONLY", "INSUFFICIENT_EVIDENCE"}
            ],
            "projects": projects,
            "experience": experience,
            "metric_summary": {
                "projects_without_metrics": sum(1 for item in projects if item["metric_status"] == "NO_METRIC_FOUND"),
                "experience_without_metrics": sum(1 for item in experience if item["metric_status"] == "NO_METRIC_FOUND"),
            },
            "education": self._education_facts(parsed_resume),
        }

    def _skill_evidence(
        self,
        skill: str,
        parsed_resume: Mapping[str, Any],
        parsed_jd: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        canonical = self._canonical(skill)
        skills = self._canonical_values(parsed_resume.get("skills"))
        section_evidence = parsed_resume.get("section_evidence") or {}
        skills_section = set(self._canonical_values(section_evidence.get("skills_section")))
        experience_hits: List[Dict[str, Any]] = []
        project_hits: List[Dict[str, Any]] = []
        certification_hits: List[str] = []

        for index, entry in enumerate(self._mappings(parsed_resume.get("experience"))):
            text = " ".join(
                str(entry.get(key, "")) for key in ("title", "company", "date", "description", "skills_applied")
            )
            if canonical in self._canonical_values([*self._as_list(entry.get("skills_applied")), text]):
                experience_hits.append(
                    {"title": entry.get("title", ""), "evidence_id": f"RESUME-EXP-{index + 1:03d}"}
                )

        for index, project in enumerate(self._mappings(parsed_resume.get("projects"))):
            text = " ".join(
                str(project.get(key, "")) for key in ("title", "description", "technologies", "technology", "skills")
            )
            if canonical in self._canonical_values([*self._as_list(project.get("technologies")), text]):
                project_hits.append(
                    {"title": project.get("title", ""), "evidence_id": f"RESUME-PROJECT-{index + 1:03d}"}
                )

        for cert in self._mappings(parsed_resume.get("certifications")):
            name = str(cert.get("name", ""))
            if canonical in self._canonical_values([name]):
                certification_hits.append(name)

        if experience_hits and project_hits:
            strength = "STRONG_EXPERIENCE_AND_PROJECT_EVIDENCE"
        elif experience_hits:
            strength = "EXPERIENCE_EVIDENCE"
        elif project_hits:
            strength = "PROJECT_EVIDENCE"
        elif certification_hits:
            strength = "CERTIFICATION_EVIDENCE"
        elif canonical in skills_section or canonical in skills:
            strength = "SKILL_LIST_ONLY"
        else:
            strength = "NOT_FOUND"

        evidence_ids: List[str] = []
        if canonical in skills:
            skill_index = skills.index(canonical)
            evidence_ids.append(f"RESUME-SKILL-{skill_index + 1:03d}")
        evidence_ids.extend(item["evidence_id"] for item in experience_hits)
        evidence_ids.extend(item["evidence_id"] for item in project_hits)
        evidence_ids = self._unique(evidence_ids)

        jd_refs = self._jd_skill_refs(canonical, parsed_jd)
        weak_context = self._weak_skill_context(canonical, parsed_resume)
        return {
            "skill": canonical,
            "in_skills_section": canonical in skills_section,
            "in_experience": bool(experience_hits),
            "in_projects": bool(project_hits),
            "in_certifications": bool(certification_hits),
            "evidence_depth": len(evidence_ids),
            "evidence_strength": "INSUFFICIENT_EVIDENCE" if weak_context and not (experience_hits or project_hits) else strength,
            "experience_titles": experience_hits,
            "project_titles": project_hits,
            "certification_names": certification_hits,
            "evidence_reference_ids": evidence_ids,
            "jd_evidence_reference_ids": jd_refs,
            "candidate_skill_present": canonical in skills or bool(experience_hits or project_hits or certification_hits),
            "related_context_without_exact_skill": weak_context,
        }

    def _project_facts(
        self,
        parsed_resume: Mapping[str, Any],
        parsed_jd: Optional[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        jd_skills = self._canonical_values(
            [*(parsed_jd.get("required_skills") or []), *(parsed_jd.get("preferred_skills") or [])]
        ) if parsed_jd else []
        results = []
        for index, project in enumerate(self._mappings(parsed_resume.get("projects"))):
            description = str(project.get("description", ""))
            text = " ".join(
                str(project.get(key, "")) for key in ("title", "description", "technologies", "technology", "skills")
            )
            project_skills = self._canonical_values([*self._as_list(project.get("technologies")), text])
            matched = [skill for skill in jd_skills if satisfies_skill(skill, set(project_skills))]
            results.append(
                {
                    "project_id": f"RESUME-PROJECT-{index + 1:03d}",
                    "title": project.get("title", ""),
                    "matched_jd_skills": matched,
                    "jd_evidence_reference_ids": self._jd_skill_refs_for_skills(matched, parsed_jd),
                    "project_skills": project_skills,
                    "technologies_explicit": self._as_list(project.get("technologies")),
                    "description_present": bool(description.strip()),
                    "relevance_status": "RELEVANT" if matched else "NOT_RELEVANT_OR_NO_JD",
                    "metric_status": self._metric_status(text),
                }
            )
        return results

    def _experience_facts(
        self,
        parsed_resume: Mapping[str, Any],
        parsed_jd: Optional[Mapping[str, Any]],
    ) -> List[Dict[str, Any]]:
        jd_skills = self._canonical_values(
            [*(parsed_jd.get("required_skills") or []), *(parsed_jd.get("preferred_skills") or [])]
        ) if parsed_jd else []
        results = []
        for index, entry in enumerate(self._mappings(parsed_resume.get("experience"))):
            description = str(entry.get("description", ""))
            text = " ".join(
                str(entry.get(key, "")) for key in ("title", "company", "date", "description", "skills_applied")
            )
            technologies = self._canonical_values([*self._as_list(entry.get("skills_applied")), description])
            action_terms = [
                verb for verb in IMPACT_ACTION_VERBS
                if re.search(rf"\b{re.escape(verb)}\b", description, re.IGNORECASE)
            ]
            relevant = not jd_skills or bool(set(technologies).intersection(jd_skills))
            results.append(
                {
                    "experience_id": f"RESUME-EXP-{index + 1:03d}",
                    "title": entry.get("title", ""),
                    "company": entry.get("company", ""),
                    "date": entry.get("date", ""),
                    "technologies": technologies,
                    "action_terms": sorted(set(action_terms)),
                    "description_present": bool(description.strip()),
                    "relevance_status": "RELEVANT" if relevant else "NOT_RELEVANT",
                    "metric_status": self._metric_status(text),
                }
            )
        return results

    def _resume_opportunities(
        self,
        parsed_resume: Mapping[str, Any],
        analysis: Mapping[str, Any],
        facts: Mapping[str, Any],
        role_definition: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        top_role = (analysis.get("role_matches") or [{}])[0] if isinstance(analysis, Mapping) else {}
        required = list(top_role.get("missing_required_skills", [])) if isinstance(top_role, Mapping) else []
        preferred = list(top_role.get("missing_preferred_skills", [])) if isinstance(top_role, Mapping) else []
        evidence_by_skill = {item["skill"]: item for item in facts["skills"]}

        for index, raw_skill in enumerate(required):
            skill = self._canonical(raw_skill)
            evidence = evidence_by_skill.get(skill, {})
            if evidence.get("related_context_without_exact_skill"):
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-SKILL-CONTEXT-{index + 1:03d}", "SKILL_EVIDENCE", "HIGH",
                    f"Clarify {skill} evidence", f"Resume content suggests related API work, but {skill} is not explicit.",
                    f"If the existing work used {skill}, name that technology clearly in the project or experience description.",
                    [*evidence.get("evidence_reference_ids", [])], "CLARIFY", "INSUFFICIENT_EVIDENCE",
                    f"{skill} evidence visibility", facts,
                ))
            elif evidence.get("in_skills_section") and not evidence.get("in_experience") and not evidence.get("in_projects"):
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-SKILL-EVIDENCE-{index + 1:03d}", "SKILL_EVIDENCE", "HIGH",
                    f"Strengthen {skill} evidence", f"{skill} is listed for the target role but applied evidence is limited.",
                    f"If you have used {skill}, make that existing project or experience evidence more visible. Do not add unsupported experience.",
                    [*evidence.get("evidence_reference_ids", [])], "IMPROVE_EVIDENCE", "INSUFFICIENT_EVIDENCE",
                    f"{skill} resume evidence", facts,
                ))
            elif not evidence.get("candidate_skill_present"):
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-SKILL-GAP-{index + 1:03d}", "LEARNING_ACTION", "HIGH",
                    f"Build {skill} capability", f"{skill} is a required skill for the strongest detected role and is not evidenced in the resume.",
                    f"Learn {skill} and gain practical experience before listing it on your resume.",
                    [], "LEARN", "LEARNING_ACTION", f"{skill} learning resume guidance", facts,
                ))

        for index, raw_skill in enumerate(preferred[:2]):
            skill = self._canonical(raw_skill)
            evidence = evidence_by_skill.get(skill, {})
            if not evidence.get("candidate_skill_present"):
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-PREFERRED-GAP-{index + 1:03d}", "LEARNING_ACTION", "MEDIUM",
                    f"Explore {skill}", f"{skill} is a preferred skill for the strongest detected role and is not evidenced in the resume.",
                    f"Treat {skill} as a learning priority and add it to the resume only after gaining verifiable experience.",
                    [], "LEARN", "LEARNING_ACTION", f"{skill} preferred skill learning", facts,
                ))

        for item in facts["projects"]:
            if item["relevance_status"] == "RELEVANT" and item["metric_status"] == "NO_METRIC_FOUND":
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-PROJECT-IMPACT-{len(opportunities) + 1:03d}", "IMPACT_CLARITY", "MEDIUM",
                    f"Clarify impact in {item['title'] or 'the relevant project'}",
                    "The relevant project has technical evidence but no measurable impact was detected.",
                    "Add a measurable impact metric if you have one; never invent a number.",
                    [item["project_id"]], "IMPROVE_EVIDENCE", "SAFE_SUGGESTION", "resume project impact metrics", facts,
                ))

        if facts["projects"] and top_role:
            refs = [item["project_id"] for item in facts["projects"] if item["relevance_status"] == "RELEVANT"][:2]
            if refs:
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-RESUME-ROLE-ALIGNMENT-{len(opportunities) + 1:03d}", "ROLE_ALIGNMENT", "LOW",
                    f"Emphasize evidence for {top_role.get('title', 'the target role')}",
                    "The strongest detected role is supported by resume evidence that may need clearer emphasis.",
                    "Place the most relevant existing projects and technologies where they are easy to find, using only accurate terminology.",
                    refs, "REORDER", "SAFE_SUGGESTION", "role-aligned resume structure", facts,
                ))

        return opportunities[:8]

    def _jdxr_opportunities(
        self,
        parsed_resume: Mapping[str, Any],
        parsed_jd: Mapping[str, Any],
        match_result: Mapping[str, Any],
        facts: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        evidence_by_skill = {item["skill"]: item for item in facts["skills"]}
        for importance, raw_skills, priority in (
            ("required", parsed_jd.get("required_skills") or [], "CRITICAL"),
            ("preferred", parsed_jd.get("preferred_skills") or [], "MEDIUM"),
        ):
            for index, raw_skill in enumerate(raw_skills):
                skill = self._canonical(raw_skill)
                evidence = evidence_by_skill.get(skill, {})
                jd_refs = evidence.get("jd_evidence_reference_ids", [])
                resume_refs = evidence.get("evidence_reference_ids", [])
                if not evidence.get("candidate_skill_present") and not evidence.get("related_context_without_exact_skill"):
                    opportunities.append(self._opportunity(
                        f"IMPROVEMENT-JDXR-{importance.upper()}-SKILL-{index + 1:03d}", "MISSING_EVIDENCE", priority,
                        f"Build evidence for {skill}",
                        f"{skill} is a {importance} job requirement and is not evidenced in the resume.",
                        f"Learn {skill}, gain practical experience, and add it to the resume only when the experience is verifiable.",
                        jd_refs, "LEARN", "LEARNING_ACTION", f"{skill} learning and job requirement guidance", facts,
                    ))
                elif evidence.get("evidence_strength") in {"SKILL_LIST_ONLY", "INSUFFICIENT_EVIDENCE"} or evidence.get("related_context_without_exact_skill"):
                    opportunities.append(self._opportunity(
                        f"IMPROVEMENT-JDXR-{importance.upper()}-EVIDENCE-{index + 1:03d}", "SKILL_EVIDENCE", "HIGH" if importance == "required" else "MEDIUM",
                        f"Clarify {skill} evidence",
                        f"The resume references {skill} weakly or without clear applied evidence for this job.",
                        f"If your existing work used {skill}, make that project or experience evidence explicit using accurate details.",
                        [*resume_refs, *jd_refs], "IMPROVE_EVIDENCE", "INSUFFICIENT_EVIDENCE", f"{skill} evidence visibility", facts,
                    ))

        education = match_result.get("education_alignment") or {}
        if education.get("status") in {"missing", "not_aligned", "partially_aligned"}:
            if education.get("status") != "aligned" and education.get("requirements"):
                opportunities.append(self._opportunity(
                    "IMPROVEMENT-JDXR-EDUCATION-BLOCKER", "JD_REQUIREMENT_ALIGNMENT", "CRITICAL",
                    "Review the education requirement",
                    "The deterministic education alignment is not fully matched for this job.",
                    "Treat this as an eligibility consideration. Do not add or imply a degree or field that you do not hold.",
                    self._requirement_refs("education", parsed_jd), "REVIEW", "VERIFIED_FACT", "education requirement alignment", facts,
                ))

        eligibility = match_result.get("eligibility_alignment") or {}
        if eligibility.get("status") == "missing":
            opportunities.append(self._opportunity(
                "IMPROVEMENT-JDXR-ELIGIBILITY-BLOCKER", "JD_REQUIREMENT_ALIGNMENT", "CRITICAL",
                "Review the eligibility blocker",
                "The deterministic eligibility result shows a required or preferred qualification is not matched.",
                "Do not add or imply an unearned qualification. Verify the requirement separately before applying.",
                self._requirement_refs("eligibility", parsed_jd), "REVIEW", "VERIFIED_FACT", "eligibility requirement guidance", facts,
            ))

        for item in facts["projects"]:
            if item["relevance_status"] == "RELEVANT" and item["metric_status"] == "NO_METRIC_FOUND":
                opportunities.append(self._opportunity(
                    f"IMPROVEMENT-JDXR-PROJECT-IMPACT-{len(opportunities) + 1:03d}", "PROJECT_EVIDENCE", "MEDIUM",
                    f"Strengthen {item['title'] or 'the relevant project'} for this job",
                    "The project is relevant to the job requirements but no measurable impact was detected.",
                    "Add a measurable impact metric if you have one, and clarify your actual technical responsibility.",
                    [item["project_id"], *item["jd_evidence_reference_ids"]], "IMPROVE_EVIDENCE", "SAFE_SUGGESTION", "project evidence and impact guidance", facts,
                ))

        experience = next((item for item in facts["experience"] if item["relevance_status"] == "RELEVANT"), None)
        experience_alignment = match_result.get("experience_alignment") or {}
        if experience and experience_alignment.get("status") in {"unmet", "insufficient_evidence", "needs_review"}:
            opportunities.append(self._opportunity(
                "IMPROVEMENT-JDXR-EXPERIENCE-EVIDENCE", "EXPERIENCE_EVIDENCE", "HIGH",
                "Clarify relevant experience evidence",
                "The deterministic experience alignment needs clearer or stronger evidence for this job.",
                "Clarify only the responsibilities, technologies, and dates that are true for your existing experience; do not add unearned years.",
                [experience["experience_id"]], "CLARIFY", "INSUFFICIENT_EVIDENCE", "experience evidence clarity", facts,
            ))

        return opportunities[:10]

    def _opportunity(
        self,
        improvement_id: str,
        category: str,
        priority: str,
        title: str,
        problem: str,
        recommendation: str,
        evidence_ids: Iterable[str],
        action_type: str,
        fact_status: str,
        knowledge_query: str,
        facts: Mapping[str, Any],
    ) -> Dict[str, Any]:
        return {
            "improvement_id": improvement_id,
            "category": category,
            "priority": priority,
            "title": title,
            "problem": problem,
            "recommendation": recommendation,
            "evidence_reference_ids": self._unique(evidence_ids),
            "action_type": action_type,
            "fact_status": fact_status,
            "knowledge_query": knowledge_query,
        }

    def _education_facts(self, parsed_resume: Mapping[str, Any]) -> List[Dict[str, Any]]:
        return [
            {
                "education_id": f"RESUME-EDU-{index + 1:03d}",
                "degree": entry.get("degree", ""),
                "field": entry.get("field", ""),
            }
            for index, entry in enumerate(self._mappings(parsed_resume.get("education")))
        ]

    def _alignment_snapshot(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, Mapping):
            return {"status": "not_available", "requirements": []}
        return {
            "status": value.get("status"),
            "requirements": [
                {
                    key: item.get(key)
                    for key in ("requirement", "status", "importance", "requirement_type", "required")
                    if item.get(key) is not None
                }
                for item in value.get("requirements", [])
                if isinstance(item, Mapping)
            ],
        }

    def _metric_status(self, text: str) -> str:
        return "HAS_VERIFIED_METRIC" if self._METRIC_RE.search(text or "") else "NO_METRIC_FOUND"

    def _weak_skill_context(self, skill: str, parsed_resume: Mapping[str, Any]) -> bool:
        if skill != "REST APIs":
            return False
        text = " ".join(
            str(value.get("description", ""))
            for value in self._mappings(parsed_resume.get("projects")) + self._mappings(parsed_resume.get("experience"))
        ).casefold()
        return "api" in text and "rest" not in text and "restful" not in text

    def _jd_skill_refs(self, skill: str, parsed_jd: Optional[Mapping[str, Any]]) -> List[str]:
        if not parsed_jd:
            return []
        required = list(parsed_jd.get("required_skills") or [])
        preferred = list(parsed_jd.get("preferred_skills") or [])
        for index, raw in enumerate(required):
            if self._canonical(raw) == skill:
                return [f"JD-SKILL-{index + 1:03d}"]
        for index, raw in enumerate(preferred):
            if self._canonical(raw) == skill:
                return [f"JD-PREF-SKILL-{index + 1:03d}"]
        return []

    def _jd_skill_refs_for_skills(self, skills: Iterable[str], parsed_jd: Optional[Mapping[str, Any]]) -> List[str]:
        refs: List[str] = []
        for skill in skills:
            refs.extend(self._jd_skill_refs(skill, parsed_jd))
        return self._unique(refs)

    def _requirement_refs(self, kind: str, parsed_jd: Mapping[str, Any]) -> List[str]:
        if kind == "education":
            return [f"JD-EDU-{index + 1:03d}" for index, _ in enumerate(parsed_jd.get("education_requirements") or [])]
        if kind == "eligibility":
            return [
                *[f"JD-ELIG-{index + 1:03d}" for index, _ in enumerate(parsed_jd.get("required_eligibility_requirements") or [])],
                *[f"JD-PREF-ELIG-{index + 1:03d}" for index, _ in enumerate(parsed_jd.get("preferred_eligibility_requirements") or [])],
            ]
        return []

    def _canonical_values(self, values: Any) -> List[str]:
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, (list, tuple, set)):
            return []
        results: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            extracted = list(extract_matched_skills(text).keys())
            candidates = extracted or normalize_skill_list([text])
            for candidate in candidates:
                canonical = self._canonical(candidate)
                if canonical and canonical not in results:
                    results.append(canonical)
        return results

    def _canonical(self, value: Any) -> str:
        return get_canonical_skill(str(value or "").strip()) if str(value or "").strip() else ""

    def _unique(self, values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        for value in values:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    def _as_list(self, value: Any) -> List[Any]:
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value] if value else []

    def _mappings(self, value: Any) -> List[Mapping[str, Any]]:
        return [item for item in value or [] if isinstance(item, Mapping)] if isinstance(value, list) else []

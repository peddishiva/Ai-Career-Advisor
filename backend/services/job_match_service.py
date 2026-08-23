"""
Deterministic resume-to-job-description matching service for Phase 2B.
"""

import re
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from config.job_match_config import (
    CERTIFICATION_TOKEN_MATCH_THRESHOLD,
    CERTIFICATION_STATUS_SCORES,
    EDUCATION_STATUS_SCORES,
    EXPERIENCE_ALIGNMENT_WEIGHTS,
    EXPERIENCE_NO_YEAR_CONTEXT_SCORE,
    EXPERIENCE_UNKNOWN_YEAR_SCORE,
    EXPERIENCE_UNMET_YEAR_MAX_SCORE,
    JOB_MATCH_WEIGHTS,
    MAX_COMPONENT_SCORE,
    PARTIAL_SKILL_COVERAGE_CREDIT,
    PROJECT_DEPTH_TARGET_COUNT,
    PROJECT_ALIGNMENT_WEIGHTS,
    READINESS_THRESHOLDS,
    RECOMMENDATION_LIMIT,
    RELATED_EDUCATION_FIELDS,
    RESPONSIBILITY_ALIGNMENT_WEIGHTS,
    RESPONSIBILITY_STATUS_THRESHOLDS,
    SKILL_EVIDENCE_THRESHOLDS,
    SKILL_STATUS_SCORES,
    TEXT_STOP_WORDS,
)
from config.skill_aliases import SKILL_ALIASES, SKILL_RELATIONS, get_canonical_skill, satisfies_skill
from utils.normalization import extract_matched_skills
from utils.scoring_logic import ScoringEngine


class JobMatchService:
    """Match parsed resume evidence against a parsed actual job description."""

    def __init__(self, reference_date: Optional[date] = None, reference_year: Optional[int] = None):
        self.scoring_engine = ScoringEngine()
        self.reference_year = self._resolve_reference_year(reference_date, reference_year)

    def _resolve_reference_year(self, reference_date: Optional[date], reference_year: Optional[int]) -> int:
        if reference_year is not None:
            return int(reference_year)
        if reference_date is not None:
            return reference_date.year
        return date.today().year

    def match(self, resume_data: Dict[str, Any], job_description_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a deterministic, explainable job match result."""
        resume_data = resume_data or {}
        job_description_data = job_description_data or {}

        required_skill_matches = self._match_skill_group(
            job_description_data.get("required_skills", []),
            resume_data,
            "required",
        )
        preferred_skill_matches = self._match_skill_group(
            job_description_data.get("preferred_skills", []),
            resume_data,
            "preferred",
        )

        required_skill_score = self._average_status_score(required_skill_matches)
        preferred_skill_score = self._average_status_score(preferred_skill_matches)
        required_skill_coverage = self._required_skill_coverage(required_skill_matches)

        experience_alignment = self._align_experience(resume_data, job_description_data)
        project_alignment = self._align_projects(resume_data, job_description_data)
        education_alignment = self._align_education(resume_data, job_description_data)
        certification_alignment = self._align_certifications(resume_data, job_description_data)
        eligibility_alignment = self._align_eligibility(resume_data, job_description_data)
        qualification_alignment = self._align_requirement_group(
            resume_data,
            job_description_data,
            "required_capability_requirements",
            "preferred_capability_requirements",
            "required capability or domain knowledge",
        )
        availability_alignment = self._align_requirement_group(
            resume_data,
            job_description_data,
            "required_availability_requirements",
            "preferred_availability_requirements",
            "availability or duration",
        )
        responsibility_alignment = self._align_responsibilities(resume_data, job_description_data)

        component_scores = {
            "required_skills": required_skill_score,
            "preferred_skills": preferred_skill_score,
            "experience": experience_alignment["score"],
            "projects": project_alignment["score"],
            "education": education_alignment["score"],
            "certifications": self._credential_component_score(certification_alignment, eligibility_alignment),
            "responsibilities": responsibility_alignment["score"],
        }
        weighted_breakdown = self._weighted_breakdown(component_scores)
        unconstrained_score = int(round(sum(weighted_breakdown.values())))
        constraint = self._required_skill_constraint(unconstrained_score, required_skill_coverage, required_skill_matches)
        score = constraint["score"]

        required_skills = self._group_skill_matches(required_skill_matches)
        preferred_skills = self._group_skill_matches(preferred_skill_matches)
        critical_gaps = self._critical_gaps(
            required_skill_matches,
            experience_alignment,
            education_alignment,
            certification_alignment,
            eligibility_alignment,
            qualification_alignment,
            availability_alignment,
        )
        non_critical_gaps = self._non_critical_gaps(
            preferred_skill_matches,
            certification_alignment,
            eligibility_alignment,
            qualification_alignment,
            availability_alignment,
            responsibility_alignment,
        )

        return {
            "score": score,
            "unconstrained_score": unconstrained_score,
            "readiness": self._readiness(score, required_skill_coverage, critical_gaps),
            "breakdown": weighted_breakdown,
            "component_scores": component_scores,
            "score_constraint": constraint,
            "required_skill_coverage": round(required_skill_coverage, 2),
            "required_skills": required_skills,
            "preferred_skills": preferred_skills,
            "experience_alignment": experience_alignment,
            "project_alignment": project_alignment,
            "education_alignment": education_alignment,
            "certification_alignment": certification_alignment,
            "eligibility_alignment": eligibility_alignment,
            "qualification_alignment": qualification_alignment,
            "availability_alignment": availability_alignment,
            "responsibility_alignment": responsibility_alignment,
            "critical_gaps": critical_gaps,
            "non_critical_gaps": non_critical_gaps,
            "recommendations": self._recommendations(
                required_skill_matches,
                preferred_skill_matches,
                experience_alignment,
                education_alignment,
                certification_alignment,
                eligibility_alignment,
                qualification_alignment,
                availability_alignment,
            ),
            "resume_alignment": self._resume_alignment(
                required_skill_matches,
                preferred_skill_matches,
                experience_alignment,
                project_alignment,
                education_alignment,
                certification_alignment,
                eligibility_alignment,
                responsibility_alignment,
            ),
        }

    def _match_skill_group(
        self,
        jd_skills: Sequence[str],
        resume_data: Dict[str, Any],
        importance: str,
    ) -> List[Dict[str, Any]]:
        matches = []
        for skill in self._canonical_skills(jd_skills):
            evidence = self._skill_evidence(skill, resume_data)
            status = self._skill_status(skill, evidence)
            matches.append(
                {
                    "skill": skill,
                    "importance": importance,
                    "status": status,
                    "evidence": evidence if status != "missing" else None,
                    "reason": self._skill_reason(skill, status, evidence, importance),
                }
            )
        return matches

    def _skill_evidence(self, skill: str, resume_data: Dict[str, Any]) -> Dict[str, Any]:
        candidate_skills = set(self._canonical_skills(resume_data.get("skills", [])))
        section_evidence = resume_data.get("section_evidence", {})
        skills_section = set(self._canonical_skills(section_evidence.get("skills_section", [])))

        exact_present = skill in candidate_skills
        related_skills = self._related_candidate_skills(skill, candidate_skills)

        experience_entries = []
        for entry in resume_data.get("experience", []):
            entry_skills = set(self._canonical_skills(entry.get("skills_applied", [])))
            entry_text_skills = set(extract_matched_skills(entry.get("description", "")).keys())
            if skill in entry_skills or skill in entry_text_skills:
                experience_entries.append(entry.get("title") or entry.get("description", "")[:80])

        projects = []
        for project in resume_data.get("projects", []):
            project_skills = set(self._canonical_skills(project.get("technologies", [])))
            project_text_skills = set(extract_matched_skills(project.get("description", "")).keys())
            if skill in project_skills or skill in project_text_skills:
                projects.append(project.get("title") or project.get("description", "")[:80])

        certification_matches = []
        for cert in resume_data.get("certifications", []):
            name = cert.get("name", "")
            cert_skills = set(extract_matched_skills(name).keys())
            if skill in cert_skills or self._text_match(skill, name):
                certification_matches.append(name)

        evidence_score = self.scoring_engine.calculate_skill_evidence_score(skill, resume_data) if exact_present else 0
        return {
            "skills_section": skill in skills_section,
            "candidate_skill_present": exact_present,
            "experience_entries": len(experience_entries),
            "experience_titles": experience_entries,
            "projects": len(projects),
            "project_titles": projects,
            "certifications": len(certification_matches),
            "certification_names": certification_matches,
            "related_skills": related_skills,
            "evidence_score": evidence_score,
        }

    def _skill_status(self, skill: str, evidence: Dict[str, Any]) -> str:
        if evidence["experience_entries"] or evidence["projects"] or evidence["certifications"]:
            return "matched"
        if evidence["candidate_skill_present"] and evidence["evidence_score"] >= SKILL_EVIDENCE_THRESHOLDS["matched"]:
            return "matched"
        if evidence["candidate_skill_present"] and evidence["evidence_score"] >= SKILL_EVIDENCE_THRESHOLDS["partial"]:
            return "partial"
        if evidence["related_skills"]:
            return "partial"
        return "missing"

    def _skill_reason(self, skill: str, status: str, evidence: Dict[str, Any], importance: str) -> str:
        if status == "matched":
            sources = []
            if evidence["skills_section"]:
                sources.append("Skills section")
            if evidence["experience_entries"]:
                sources.append("professional Experience")
            if evidence["projects"]:
                sources.append("Projects")
            if evidence["certifications"]:
                sources.append("Certifications")
            return f"{skill} is {importance} and is supported by {', '.join(sources)} evidence."
        if status == "partial":
            if evidence["related_skills"]:
                return f"{skill} is not explicit, but related resume skill evidence was found: {', '.join(evidence['related_skills'])}."
            return f"{skill} appears in the resume skills evidence, but no professional or project application was found."
        return f"No {skill} evidence was found in the resume."

    def _average_status_score(self, matches: List[Dict[str, Any]]) -> int:
        if not matches:
            return 0
        total = sum(SKILL_STATUS_SCORES[item["status"]] for item in matches)
        return int(round(total / len(matches)))

    def _required_skill_coverage(self, matches: List[Dict[str, Any]]) -> float:
        if not matches:
            return 1.0
        matched = sum(1.0 for item in matches if item["status"] == "matched")
        partial = sum(PARTIAL_SKILL_COVERAGE_CREDIT for item in matches if item["status"] == "partial")
        return (matched + partial) / len(matches)

    def _align_experience(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = jd_data.get("experience_requirements", [])
        experience_entries = resume_data.get("experience", [])
        jd_skills = self._canonical_skills(jd_data.get("required_skills", []) + jd_data.get("preferred_skills", []))
        results = []

        if not requirements:
            relevance = self._resume_text_alignment_score(
                "\n".join(jd_data.get("responsibilities", [])),
                self._experience_text(resume_data),
            )
            return {
                "score": relevance,
                "requirements": [],
                "candidate_years": None,
                "status": "not_required" if relevance == 0 else "context_aligned",
                "reason": "No explicit JD experience requirement was provided.",
            }

        for requirement in requirements:
            required_years = requirement.get("min_years", requirement.get("years"))
            maximum_years = requirement.get("max_years")
            domain = requirement.get("domain")
            job_title = jd_data.get("job_title")
            candidate_years = self._candidate_years_for_domain(experience_entries, domain, jd_skills, job_title)
            domain_score = self._domain_alignment_score(domain, jd_skills, self._experience_text(resume_data))
            years_score, status = self._years_score(required_years, candidate_years)
            score = int(round(
                years_score * EXPERIENCE_ALIGNMENT_WEIGHTS["years"]
                + domain_score * EXPERIENCE_ALIGNMENT_WEIGHTS["domain"]
            ))
            results.append(
                {
                    "requirement": requirement.get("text", ""),
                    "required_years": required_years,
                    "minimum_required_years": required_years,
                    "maximum_target_years": maximum_years,
                    "candidate_years": candidate_years,
                    "domain": domain,
                    "domain_score": domain_score,
                    "score": score,
                    "status": status,
                    "resume_evidence": self._experience_evidence_summary(experience_entries, domain, jd_skills, job_title),
                    "reason": self._experience_reason(required_years, maximum_years, candidate_years, domain_score, status),
                    "requirement_type": requirement.get("requirement_type", "required"),
                }
            )

        score = int(round(sum(item["score"] for item in results) / len(results))) if results else 0
        status = "met" if results and all(item["status"] == "met" for item in results) else "needs_review"
        if any(item["status"] == "unmet" for item in results):
            status = "unmet"
        elif any(item["status"] == "insufficient_evidence" for item in results):
            status = "insufficient_evidence"
        return {
            "score": score,
            "requirements": results,
            "candidate_years": max(
                [item["candidate_years"] for item in results if item["candidate_years"] is not None],
                default=None,
            ),
            "status": status,
            "reason": "Professional experience alignment uses resume experience entries only.",
        }

    def _align_projects(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        projects = resume_data.get("projects", [])
        target_skills = self._canonical_skills(jd_data.get("required_skills", []) + jd_data.get("preferred_skills", []))
        if not projects or not target_skills:
            return {
                "score": 0,
                "matched_skills": [],
                "matched_projects": [],
                "reason": "No project evidence or no JD skills were available for project alignment.",
            }

        matched_skills: Set[str] = set()
        matched_projects = []
        for project in projects:
            project_text = self._project_evidence_text(project)
            project_skills = set(self._canonical_skills(project.get("technologies", [])))
            project_skills.update(extract_matched_skills(project_text).keys())
            overlap = sorted(
                skill
                for skill in target_skills
                if skill in project_skills
                or satisfies_skill(skill, project_skills)
                or self._skill_text_present(skill, project_text)
            )
            if overlap:
                matched_skills.update(overlap)
                matched_projects.append(
                    {
                        "title": project.get("title", ""),
                        "matched_skills": overlap,
                        "source": "project",
                    }
                )

        skill_coverage = len(matched_skills) / len(target_skills) if target_skills else 0.0
        project_depth = min(len(matched_projects) / PROJECT_DEPTH_TARGET_COUNT, 1.0)
        score = int(round(
            (
                skill_coverage * PROJECT_ALIGNMENT_WEIGHTS["skill_coverage"]
                + project_depth * PROJECT_ALIGNMENT_WEIGHTS["project_depth"]
            )
            * MAX_COMPONENT_SCORE
        ))
        return {
            "score": min(score, MAX_COMPONENT_SCORE),
            "matched_skills": sorted(matched_skills),
            "matched_projects": matched_projects,
            "reason": "Project alignment uses parsed projects only and does not satisfy professional experience years.",
        }

    def _align_education(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = jd_data.get("education_requirements", [])
        education = resume_data.get("education", [])
        if not requirements:
            return {"score": 0, "requirements": [], "status": "not_required", "reason": "No JD education requirement was provided."}

        results = []
        for requirement in requirements:
            result = self._match_single_education_requirement(requirement, education)
            results.append(result)
        score = int(round(sum(item["score"] for item in results) / len(results))) if results else 0
        status = "aligned" if results and all(item["status"] == "aligned" for item in results) else "not_aligned"
        if any(item["status"] == "partially_aligned" for item in results):
            status = "partially_aligned"
        if any(item["status"] == "missing" for item in results):
            status = "missing"
        return {
            "score": score,
            "requirements": results,
            "status": status,
            "reason": "Education alignment uses actual JD education requirements and parsed resume education only.",
        }

    def _match_single_education_requirement(
        self,
        requirement: Dict[str, Any],
        education: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not education:
            return {
                "requirement": requirement.get("raw_text", ""),
                "status": "missing",
                "score": EDUCATION_STATUS_SCORES["missing"],
                "resume_evidence": None,
                "reason": "No resume education evidence was found.",
                "requirement_type": requirement.get("requirement_type", "required"),
            }

        required_levels = [level.lower() for level in requirement.get("degree_level", [])]
        required_fields = [field.lower() for field in requirement.get("fields", [])]
        related_allowed = bool(requirement.get("related_field_allowed"))

        best = None
        for edu in education:
            degree_level = self._resume_degree_level(edu.get("degree", ""))
            field = self._normalize_education_field(edu.get("field", ""))
            level_match = not required_levels or degree_level in required_levels
            field_match = self._education_field_match(field, required_fields, related_allowed)
            status = "aligned" if level_match and field_match else "not_aligned"
            if level_match and not field_match and related_allowed and self._is_related_education_field(field):
                status = "partially_aligned"
            score = EDUCATION_STATUS_SCORES[status]
            candidate = {
                "requirement": requirement.get("raw_text", ""),
                "status": status,
                "score": score,
                "resume_evidence": {"degree": edu.get("degree", ""), "field": edu.get("field", "")},
                "reason": self._education_reason(status, edu, requirement),
                "requirement_type": requirement.get("requirement_type", "required"),
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate

        return best or {
            "requirement": requirement.get("raw_text", ""),
            "status": "not_aligned",
            "score": 0,
            "resume_evidence": None,
            "reason": "No aligned education evidence was found.",
            "requirement_type": requirement.get("requirement_type", "required"),
        }

    def _align_certifications(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = jd_data.get("certifications", [])
        resume_certs = resume_data.get("certifications", [])
        if not requirements:
            return {"score": 0, "requirements": [], "status": "not_required", "reason": "No JD certification requirement was provided."}

        results = []
        for requirement in requirements:
            matched = self._matching_certification(requirement.get("name", ""), resume_certs)
            status = "matched" if matched else "missing"
            results.append(
                {
                    "requirement": requirement.get("name", ""),
                    "required": bool(requirement.get("required", True)),
                    "status": status,
                    "score": CERTIFICATION_STATUS_SCORES[status],
                    "resume_evidence": matched,
                    "reason": (
                        f"Resume certification evidence matches {requirement.get('name', '')}."
                        if matched else f"No certification evidence matched {requirement.get('name', '')}."
                    ),
                }
            )

        score = int(round(sum(item["score"] for item in results) / len(results))) if results else 0
        status = "matched" if results and all(item["status"] == "matched" for item in results) else "missing"
        return {"score": score, "requirements": results, "status": status, "reason": "Certification alignment uses parsed resume certifications only."}

    def _align_eligibility(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        required = self._eligibility_requirements(jd_data, "required")
        preferred = self._eligibility_requirements(jd_data, "preferred")
        requirements = required + preferred
        if not requirements:
            return {
                "score": 0,
                "requirements": [],
                "status": "not_required",
                "reason": "No explicit professional qualification or eligibility requirement was provided.",
            }

        resume_evidence = self._eligibility_resume_evidence(resume_data)
        results = [self._match_single_eligibility_requirement(requirement, resume_evidence) for requirement in requirements]
        score = int(round(sum(item["score"] for item in results) / len(results))) if results else 0
        status = "matched" if results and all(item["status"] == "matched" for item in results) else "needs_review"
        if any(item["status"] in {"missing", "insufficient_evidence"} for item in results):
            status = "missing"
        return {
            "score": score,
            "requirements": results,
            "status": status,
            "reason": "Professional qualification alignment uses explicit resume evidence outside project descriptions.",
        }

    def _align_requirement_group(
        self,
        resume_data: Dict[str, Any],
        jd_data: Dict[str, Any],
        required_key: str,
        preferred_key: str,
        label: str,
    ) -> Dict[str, Any]:
        required = list(jd_data.get(required_key) or [])
        preferred = list(jd_data.get(preferred_key) or [])
        requirements = required + preferred
        if not requirements:
            return {
                "score": 0,
                "requirements": [],
                "status": "not_required",
                "reason": f"No explicit {label} requirement was provided.",
            }

        resume_evidence = self._eligibility_resume_evidence(resume_data)
        results = [self._match_single_requirement(item, resume_evidence) for item in requirements]
        score = int(round(sum(item["score"] for item in results) / len(results))) if results else 0
        status = "matched" if results and all(item["status"] == "matched" for item in results) else "needs_review"
        if any(item["status"] in {"missing", "insufficient_evidence"} for item in results):
            status = "missing"
        return {
            "score": score,
            "requirements": results,
            "status": status,
            "reason": f"{label.title()} alignment uses explicit JD requirements and parsed resume evidence only.",
        }

    def _match_single_requirement(
        self,
        requirement: Dict[str, Any],
        resume_evidence: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        requirement_text = requirement.get("text", requirement.get("raw_text", ""))
        requirement_terms = self._eligibility_terms(requirement_text)
        matched_evidence = [
            evidence
            for evidence in resume_evidence
            if self._requirement_evidence_matches(requirement, requirement_terms, evidence["text"])
        ]
        requirement_type = requirement.get("requirement_type", "required")
        if matched_evidence:
            status = "matched"
            reason = f"Resume evidence supports the requirement: {requirement_text}"
        elif resume_evidence:
            status = "insufficient_evidence"
            reason = f"No qualifying resume evidence was found for: {requirement_text}"
        else:
            status = "missing"
            reason = f"No resume evidence was found for: {requirement_text}"

        return {
            "requirement": requirement_text,
            "category": requirement.get("category"),
            "status": status,
            "importance": "critical" if requirement_type == "required" else "non_critical",
            "score": 100 if status == "matched" else 0,
            "evidence": matched_evidence,
            "resume_evidence": matched_evidence,
            "reason": reason,
            "requirement_type": requirement_type,
            "source_section": requirement.get("source_section"),
        }

    def _requirement_evidence_matches(
        self,
        requirement: Dict[str, Any],
        requirement_terms: Set[str],
        evidence_text: str,
    ) -> bool:
        if requirement.get("category") == "capability":
            required_skills = set(extract_matched_skills(requirement.get("text", "")).keys())
            evidence_skills = set(extract_matched_skills(evidence_text).keys())
            if required_skills:
                if any(satisfies_skill(skill, evidence_skills) for skill in required_skills):
                    return True
                if any(self._skill_text_present(skill, evidence_text) for skill in required_skills):
                    return True
        return self._eligibility_evidence_matches(requirement_terms, evidence_text)

    def _eligibility_requirements(self, jd_data: Dict[str, Any], requirement_type: str) -> List[Dict[str, Any]]:
        key = f"{requirement_type}_eligibility_requirements"
        if key in jd_data:
            return list(jd_data.get(key) or [])
        return [
            item
            for item in jd_data.get(f"{requirement_type}_qualifications", [])
            if item.get("category") == "eligibility"
        ]

    def _eligibility_resume_evidence(self, resume_data: Dict[str, Any]) -> List[Dict[str, str]]:
        evidence: List[Dict[str, str]] = []
        for skill in resume_data.get("skills", []) or []:
            if skill:
                evidence.append({"source": "skills", "text": str(skill)})
        for certification in resume_data.get("certifications", []) or []:
            name = certification.get("name", "") if isinstance(certification, dict) else str(certification)
            if name:
                evidence.append({"source": "certifications", "text": str(name)})
        for education in resume_data.get("education", []) or []:
            if not isinstance(education, dict):
                continue
            text = " ".join(str(education.get(field, "")) for field in ("degree", "field", "institution"))
            if text.strip():
                evidence.append({"source": "education", "text": text.strip()})
        sections = resume_data.get("sections", {}) or {}
        for source, section_name in (
            ("education", "education_text"),
            ("certifications", "certifications_text"),
            ("skills", "skills_text"),
        ):
            section_text = sections.get(section_name, "")
            if section_text and not any(item["source"] == source and item["text"] == section_text for item in evidence):
                evidence.append({"source": source, "text": section_text})
        for experience in resume_data.get("experience", []) or []:
            if not isinstance(experience, dict):
                continue
            text = " ".join(str(experience.get(field, "")) for field in ("title", "company", "date", "description"))
            if text.strip():
                evidence.append({"source": "experience", "text": text.strip()})
        return evidence

    def _match_single_eligibility_requirement(
        self,
        requirement: Dict[str, Any],
        resume_evidence: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        requirement_text = requirement.get("text", requirement.get("raw_text", ""))
        evidence_terms = self._eligibility_terms(requirement_text)
        matched_evidence = []
        for evidence in resume_evidence:
            if self._eligibility_evidence_matches(evidence_terms, evidence["text"]):
                matched_evidence.append(evidence)

        requirement_type = requirement.get("requirement_type", "required")
        if matched_evidence:
            status = "matched"
            reason = f"Resume evidence supports the eligibility requirement: {requirement_text}"
        elif resume_evidence:
            status = "insufficient_evidence"
            reason = f"No qualifying resume evidence was found for: {requirement_text}"
        else:
            status = "missing"
            reason = f"No resume evidence was found for: {requirement_text}"

        return {
            "requirement": requirement_text,
            "status": status,
            "importance": "critical" if requirement_type == "required" else "non_critical",
            "score": 100 if status == "matched" else 0,
            "evidence": matched_evidence,
            "resume_evidence": matched_evidence,
            "reason": reason,
            "requirement_type": requirement_type,
            "source_section": requirement.get("source_section"),
        }

    def _eligibility_terms(self, requirement: str) -> Set[str]:
        terms = {
            token
            for token in re.findall(r"[a-z0-9+#]+", (requirement or "").lower())
            if len(token) > 1 and token not in TEXT_STOP_WORDS
        }
        return terms.difference({
            "must", "have", "has", "been", "being", "candidate", "candidates", "only",
            "currently", "active", "actively", "required", "preferred", "mandatory", "eligible",
            "professional", "qualification", "qualifications", "program", "status", "relevant",
        })

    def _eligibility_evidence_matches(self, requirement_terms: Set[str], evidence_text: str) -> bool:
        if not requirement_terms or not evidence_text:
            return False
        evidence_terms = {
            token
            for token in re.findall(r"[a-z0-9+#]+", evidence_text.lower())
            if len(token) > 1 and token not in TEXT_STOP_WORDS
        }
        overlap = requirement_terms.intersection(evidence_terms)
        if not overlap:
            return False
        if len(requirement_terms) == 1:
            return len(overlap) == 1
        return len(overlap) >= max(2, int(round(len(requirement_terms) * 0.5)))

    def _credential_component_score(
        self,
        certification_alignment: Dict[str, Any],
        eligibility_alignment: Dict[str, Any],
    ) -> int:
        scores = [
            item.get("score", 0)
            for alignment in (certification_alignment, eligibility_alignment)
            for item in alignment.get("requirements", [])
        ]
        return int(round(sum(scores) / len(scores))) if scores else certification_alignment.get("score", 0)

    def _align_responsibilities(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
        responsibilities = jd_data.get("responsibilities", [])
        if not responsibilities:
            return {"score": 0, "items": [], "status": "not_required", "reason": "No JD responsibilities were provided."}

        resume_text = "\n".join([self._experience_text(resume_data), self._project_text(resume_data)])
        items = []
        for responsibility in responsibilities:
            score = self._responsibility_score(responsibility, resume_text)
            if score >= RESPONSIBILITY_STATUS_THRESHOLDS["matched"]:
                status = "matched"
            elif score >= RESPONSIBILITY_STATUS_THRESHOLDS["partial"]:
                status = "partial"
            else:
                status = "missing"
            items.append(
                {
                    "requirement": responsibility,
                    "status": status,
                    "score": score,
                    "reason": self._responsibility_reason(responsibility, score, status),
                }
            )
        score = int(round(sum(item["score"] for item in items) / len(items)))
        return {
            "score": score,
            "items": items,
            "status": "aligned" if all(item["status"] == "matched" for item in items) else "partial_or_missing",
            "reason": "Responsibility alignment uses deterministic skill and phrase overlap.",
        }

    def _weighted_breakdown(self, component_scores: Dict[str, int]) -> Dict[str, int]:
        return {
            component: int(round(component_scores.get(component, 0) * weight))
            for component, weight in JOB_MATCH_WEIGHTS.items()
        }

    def _required_skill_constraint(
        self,
        unconstrained_score: int,
        required_skill_coverage: float,
        required_skill_matches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not required_skill_matches:
            return {
                "applied": False,
                "score": unconstrained_score,
                "max_score": MAX_COMPONENT_SCORE,
                "reason": "No required JD skills were provided, so no required-skill constraint was applied.",
            }
        non_required_weight = 1.0 - JOB_MATCH_WEIGHTS["required_skills"]
        max_score = int(round(
            JOB_MATCH_WEIGHTS["required_skills"] * MAX_COMPONENT_SCORE
            + non_required_weight * required_skill_coverage * MAX_COMPONENT_SCORE
        ))
        score = min(unconstrained_score, max_score)
        return {
            "applied": score < unconstrained_score,
            "score": score,
            "max_score": max_score,
            "reason": (
                "Required-skill coverage proportionally limits the non-required portion of the score."
                if score < unconstrained_score
                else "Required-skill coverage did not constrain the score."
            ),
        }

    def _readiness(self, score: int, required_skill_coverage: float, critical_gaps: List[Dict[str, Any]]) -> str:
        if (
            score >= READINESS_THRESHOLDS["high_score"]
            and required_skill_coverage >= READINESS_THRESHOLDS["high_min_required_skill_coverage"]
            and len(critical_gaps) <= READINESS_THRESHOLDS["max_high_critical_gaps"]
        ):
            return "HIGH"
        if (
            score >= READINESS_THRESHOLDS["moderate_score"]
            and required_skill_coverage >= READINESS_THRESHOLDS["moderate_min_required_skill_coverage"]
            and len(critical_gaps) <= READINESS_THRESHOLDS["max_moderate_critical_gaps"]
        ):
            return "MODERATE"
        return "LOW"

    def _critical_gaps(
        self,
        required_skill_matches: List[Dict[str, Any]],
        experience_alignment: Dict[str, Any],
        education_alignment: Dict[str, Any],
        certification_alignment: Dict[str, Any],
        eligibility_alignment: Dict[str, Any],
        qualification_alignment: Dict[str, Any],
        availability_alignment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        gaps = []
        for item in required_skill_matches:
            if item["status"] == "missing":
                gaps.append({"type": "required_skill", "requirement": item["skill"], "reason": item["reason"]})
        for requirement in experience_alignment.get("requirements", []):
            if requirement.get("requirement_type") == "required" and requirement.get("status") in {"unmet", "insufficient_evidence"}:
                gaps.append({"type": "experience", "requirement": requirement.get("requirement"), "reason": requirement.get("reason")})
        for requirement in education_alignment.get("requirements", []):
            if requirement.get("requirement_type") == "required" and requirement.get("status") in {"not_aligned", "missing"}:
                gaps.append({"type": "education", "requirement": requirement.get("requirement"), "reason": requirement.get("reason")})
        for requirement in certification_alignment.get("requirements", []):
            if requirement.get("required") and requirement.get("status") == "missing":
                gaps.append({"type": "certification", "requirement": requirement.get("requirement"), "reason": requirement.get("reason")})
        for requirement in eligibility_alignment.get("requirements", []):
            if requirement.get("importance") == "critical" and requirement.get("status") in {"missing", "insufficient_evidence"}:
                gaps.append(
                    {
                        "type": "eligibility",
                        "requirement": requirement.get("requirement"),
                        "reason": requirement.get("reason"),
                    }
                )
        for alignment in (qualification_alignment, availability_alignment):
            for requirement in alignment.get("requirements", []):
                if requirement.get("importance") == "critical" and requirement.get("status") in {"missing", "insufficient_evidence"}:
                    gaps.append(
                        {
                            "type": requirement.get("category") or "required_qualification",
                            "requirement": requirement.get("requirement"),
                            "reason": requirement.get("reason"),
                        }
                    )
        return gaps

    def _non_critical_gaps(
        self,
        preferred_skill_matches: List[Dict[str, Any]],
        certification_alignment: Dict[str, Any],
        eligibility_alignment: Dict[str, Any],
        qualification_alignment: Dict[str, Any],
        availability_alignment: Dict[str, Any],
        responsibility_alignment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        gaps = []
        for item in preferred_skill_matches:
            if item["status"] == "missing":
                gaps.append({"type": "preferred_skill", "requirement": item["skill"], "reason": item["reason"]})
        for requirement in certification_alignment.get("requirements", []):
            if not requirement.get("required") and requirement.get("status") == "missing":
                gaps.append({"type": "preferred_certification", "requirement": requirement.get("requirement"), "reason": requirement.get("reason")})
        for requirement in eligibility_alignment.get("requirements", []):
            if requirement.get("importance") == "non_critical" and requirement.get("status") in {"missing", "insufficient_evidence"}:
                gaps.append(
                    {
                        "type": "preferred_eligibility",
                        "requirement": requirement.get("requirement"),
                        "reason": requirement.get("reason"),
                    }
                )
        for alignment in (qualification_alignment, availability_alignment):
            for requirement in alignment.get("requirements", []):
                if requirement.get("importance") == "non_critical" and requirement.get("status") in {"missing", "insufficient_evidence"}:
                    gaps.append(
                        {
                            "type": f"preferred_{requirement.get('category') or 'qualification'}",
                            "requirement": requirement.get("requirement"),
                            "reason": requirement.get("reason"),
                        }
                    )
        for item in responsibility_alignment.get("items", []):
            if item.get("status") == "missing":
                gaps.append({"type": "responsibility", "requirement": item.get("requirement"), "reason": item.get("reason")})
        return gaps

    def _recommendations(
        self,
        required_skill_matches: List[Dict[str, Any]],
        preferred_skill_matches: List[Dict[str, Any]],
        experience_alignment: Dict[str, Any],
        education_alignment: Dict[str, Any],
        certification_alignment: Dict[str, Any],
        eligibility_alignment: Dict[str, Any],
        qualification_alignment: Dict[str, Any],
        availability_alignment: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        recommendations = []
        for item in required_skill_matches:
            if item["status"] == "missing":
                recommendations.append(
                    {
                        "title": f"Build evidence for required {item['skill']}",
                        "description": f"{item['skill']} is required by the JD, but no resume evidence was found.",
                    }
                )
            elif item["status"] == "partial":
                recommendations.append(
                    {
                        "title": f"Strengthen applied {item['skill']} evidence",
                        "description": f"{item['skill']} appears weakly; add professional or project evidence if it is accurate.",
                    }
                )
        for requirement in experience_alignment.get("requirements", []):
            if requirement.get("status") in {"unmet", "insufficient_evidence"}:
                recommendations.append(
                    {
                        "title": "Clarify professional experience duration",
                        "description": requirement.get("reason", "The JD experience requirement is not fully supported by resume experience dates."),
                    }
                )
        for requirement in education_alignment.get("requirements", []):
            if requirement.get("status") in {"not_aligned", "missing"}:
                recommendations.append(
                    {
                        "title": "Address education requirement evidence",
                        "description": requirement.get("reason", "The JD education requirement is not supported by parsed resume education."),
                    }
                )
        for requirement in certification_alignment.get("requirements", []):
            if requirement.get("status") == "missing" and requirement.get("required"):
                recommendations.append(
                    {
                        "title": f"Add required certification evidence for {requirement.get('requirement')}",
                        "description": requirement.get("reason", "Required certification evidence is missing."),
                    }
                )
        for requirement in eligibility_alignment.get("requirements", []):
            if requirement.get("status") in {"missing", "insufficient_evidence"}:
                recommendations.append(
                    {
                        "title": "Address professional eligibility evidence",
                        "description": requirement.get("reason", "The JD qualification or eligibility requirement is not supported by the resume."),
                    }
                )
        for alignment, title in (
            (qualification_alignment, "Address required capability or domain knowledge evidence"),
            (availability_alignment, "Clarify availability or duration evidence"),
        ):
            for requirement in alignment.get("requirements", []):
                if requirement.get("status") in {"missing", "insufficient_evidence"}:
                    recommendations.append(
                        {
                            "title": title,
                            "description": requirement.get("reason", "The requirement is not supported by parsed resume evidence."),
                        }
                    )
        for item in preferred_skill_matches:
            if item["status"] == "missing" and len(recommendations) < RECOMMENDATION_LIMIT:
                recommendations.append(
                    {
                        "title": f"Consider adding preferred {item['skill']} evidence",
                        "description": f"{item['skill']} is preferred by the JD and could improve alignment if relevant.",
                    }
                )
        return recommendations[:RECOMMENDATION_LIMIT]

    def _resume_alignment(
        self,
        required_skill_matches: List[Dict[str, Any]],
        preferred_skill_matches: List[Dict[str, Any]],
        experience_alignment: Dict[str, Any],
        project_alignment: Dict[str, Any],
        education_alignment: Dict[str, Any],
        certification_alignment: Dict[str, Any],
        eligibility_alignment: Dict[str, Any],
        responsibility_alignment: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        alignment = []
        for item in required_skill_matches + preferred_skill_matches:
            if item["status"] == "matched":
                alignment.append({"type": f"{item['importance']}_skill", "requirement": item["skill"], "reason": item["reason"]})
        if experience_alignment.get("status") == "met":
            alignment.append({"type": "experience", "requirement": "experience", "reason": experience_alignment.get("reason", "")})
        if project_alignment.get("score", 0) > 0:
            alignment.append({"type": "projects", "requirement": "project evidence", "reason": project_alignment.get("reason", "")})
        if education_alignment.get("status") == "aligned":
            alignment.append({"type": "education", "requirement": "education", "reason": education_alignment.get("reason", "")})
        if certification_alignment.get("status") == "matched":
            alignment.append({"type": "certifications", "requirement": "certification", "reason": certification_alignment.get("reason", "")})
        if eligibility_alignment.get("status") == "matched":
            alignment.append({"type": "eligibility", "requirement": "professional qualification", "reason": eligibility_alignment.get("reason", "")})
        if responsibility_alignment.get("score", 0) > 0:
            alignment.append({"type": "responsibilities", "requirement": "responsibilities", "reason": responsibility_alignment.get("reason", "")})
        return alignment

    def _years_score(self, required_years: Optional[int], candidate_years: Optional[float]) -> Tuple[int, str]:
        if required_years is None:
            return (
                EXPERIENCE_NO_YEAR_CONTEXT_SCORE if candidate_years is not None else EXPERIENCE_UNKNOWN_YEAR_SCORE,
                "insufficient_evidence" if candidate_years is None else "context_aligned",
            )
        if candidate_years is None:
            return EXPERIENCE_UNKNOWN_YEAR_SCORE, "insufficient_evidence"
        if candidate_years >= required_years:
            return MAX_COMPONENT_SCORE, "met"
        if candidate_years > 0:
            return int(round((candidate_years / required_years) * EXPERIENCE_UNMET_YEAR_MAX_SCORE)), "unmet"
        return 0, "unmet"

    def _candidate_years_for_domain(
        self,
        entries: List[Dict[str, Any]],
        domain: Optional[str],
        jd_skills: List[str],
        job_title: Optional[str] = None,
    ) -> Optional[float]:
        total = 0.0
        saw_relevant_date = False
        saw_any_date = False
        for entry in entries:
            duration = self._duration_years(entry.get("date", ""))
            if duration is None:
                continue
            saw_any_date = True
            if self._experience_entry_relevant(entry, domain, jd_skills, job_title):
                total += duration
                saw_relevant_date = True
        if saw_relevant_date:
            return round(total, 1)
        if saw_any_date:
            return 0.0
        return None

    def _duration_years(self, date_text: str) -> Optional[float]:
        if not date_text:
            return None
        years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", date_text)]
        if not years:
            return None
        start = years[0]
        end = years[-1]
        if re.search(r"\b(?:present|current)\b", date_text, re.I):
            end = self.reference_year
        if end < start:
            return None
        if end == start:
            return 1.0
        return float(end - start)

    def _experience_entry_relevant(
        self,
        entry: Dict[str, Any],
        domain: Optional[str],
        jd_skills: List[str],
        job_title: Optional[str] = None,
    ) -> bool:
        text = " ".join([entry.get("title", ""), entry.get("description", "")]).lower()
        entry_skills = set(self._canonical_skills(entry.get("skills_applied", [])))
        if domain and self._token_overlap(self._tokens(domain), self._tokens(text)) > 0:
            return True
        if entry_skills.intersection(jd_skills):
            return True
        if not domain and self._token_overlap(self._role_tokens(job_title), self._role_tokens(entry.get("title", ""))) > 0:
            return True
        return False

    def _domain_alignment_score(self, domain: Optional[str], jd_skills: List[str], resume_text: str) -> int:
        resume_skills = set(extract_matched_skills(resume_text).keys())
        skill_overlap = len(set(jd_skills).intersection(resume_skills)) / len(jd_skills) if jd_skills else 0.0
        domain_overlap = self._token_overlap(self._tokens(domain or ""), self._tokens(resume_text)) if domain else 0.0
        return int(round(max(skill_overlap, domain_overlap) * MAX_COMPONENT_SCORE))

    def _experience_evidence_summary(
        self,
        entries: List[Dict[str, Any]],
        domain: Optional[str],
        jd_skills: List[str],
        job_title: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        evidence = []
        for entry in entries:
            if self._experience_entry_relevant(entry, domain, jd_skills, job_title):
                evidence.append({"title": entry.get("title", ""), "date": entry.get("date", "")})
        return evidence

    def _experience_reason(
        self,
        required_years: Optional[int],
        maximum_years: Optional[int],
        candidate_years: Optional[float],
        domain_score: int,
        status: str,
    ) -> str:
        requirement_label = self._experience_requirement_label(required_years, maximum_years)
        if status == "met":
            return (
                f"Required professional experience: {requirement_label}. Resume evidence supports approximately "
                f"{self._format_years(candidate_years)}, which meets the minimum {required_years}-year requirement."
            )
        if status == "unmet":
            return (
                f"Required professional experience: {requirement_label}. Resume evidence supports approximately "
                f"{self._format_years(candidate_years)}, which is below the minimum {required_years}-year requirement."
            )
        if status == "insufficient_evidence":
            return f"Required professional experience: {requirement_label}. Resume experience dates are unavailable or ambiguous, so professional duration was not guessed."
        return f"Experience has {domain_score}% deterministic domain/skill overlap with the JD requirement."

    def _experience_requirement_label(self, minimum_years: Optional[int], maximum_years: Optional[int]) -> str:
        if minimum_years is None:
            return "an unspecified duration"
        if maximum_years is not None:
            return f"{minimum_years}-{maximum_years} years"
        return f"{minimum_years}+ years"

    def _format_years(self, years: Optional[float]) -> str:
        if years is None:
            return "unknown"
        return f"{years:g} year" if years == 1 else f"{years:g} years"

    def _role_tokens(self, title: Optional[str]) -> Set[str]:
        tokens = self._tokens(title or "")
        families = {
            "developer": "development",
            "development": "development",
            "engineer": "engineering",
            "engineering": "engineering",
            "sdet": "testing",
            "tester": "testing",
            "testing": "testing",
            "qa": "testing",
            "analyst": "analysis",
            "analysis": "analysis",
            "scientist": "science",
            "science": "science",
        }
        return {families.get(token, token) for token in tokens}

    def _resume_text_alignment_score(self, target_text: str, resume_text: str) -> int:
        if not target_text or not resume_text:
            return 0
        return int(round(self._token_overlap(self._tokens(target_text), self._tokens(resume_text)) * MAX_COMPONENT_SCORE))

    def _responsibility_score(self, responsibility: str, resume_text: str) -> int:
        if not responsibility or not resume_text:
            return 0
        responsibility_skills = set(extract_matched_skills(responsibility).keys())
        resume_skills = set(extract_matched_skills(resume_text).keys())
        skill_score = (
            len(responsibility_skills.intersection(resume_skills)) / len(responsibility_skills)
            if responsibility_skills else 0.0
        )
        token_score = self._token_overlap(self._tokens(responsibility), self._tokens(resume_text))
        return int(round(
            (
                skill_score * RESPONSIBILITY_ALIGNMENT_WEIGHTS["skills"]
                + token_score * RESPONSIBILITY_ALIGNMENT_WEIGHTS["tokens"]
            )
            * MAX_COMPONENT_SCORE
        ))

    def _responsibility_reason(self, responsibility: str, score: int, status: str) -> str:
        if status == "matched":
            return f"Resume evidence strongly overlaps with responsibility: {responsibility}"
        if status == "partial":
            return f"Resume evidence partially overlaps with responsibility: {responsibility}"
        return f"No strong resume evidence was found for responsibility: {responsibility}"

    def _matching_certification(self, requirement_name: str, resume_certs: List[Dict[str, Any]]) -> Optional[str]:
        requirement_tokens = self._tokens(requirement_name)
        requirement_skills = set(extract_matched_skills(requirement_name).keys())
        for cert in resume_certs:
            name = cert.get("name", "")
            cert_tokens = self._tokens(name)
            cert_skills = set(extract_matched_skills(name).keys())
            if requirement_skills and requirement_skills.intersection(cert_skills):
                return name
            if self._token_overlap(requirement_tokens, cert_tokens) >= CERTIFICATION_TOKEN_MATCH_THRESHOLD:
                return name
        return None

    def _resume_degree_level(self, degree: str) -> str:
        text = degree.lower()
        if re.search(r"\bassociate", text):
            return "associate"
        if re.search(r"\bbachelor|b\.?\s?s\.?|b\.?\s?tech|btech|b\.?\s?e\.?", text):
            return "bachelor"
        if re.search(r"\bmaster|m\.?\s?s\.?|m\.?\s?tech|mba", text):
            return "master"
        if re.search(r"\bph\.?d\.?|\bdoctorate", text):
            return "phd"
        return ""

    def _education_field_match(self, resume_field: str, required_fields: List[str], related_allowed: bool) -> bool:
        if not required_fields:
            return True
        normalized_resume_field = self._normalize_education_field(resume_field)
        for field in required_fields:
            normalized_required_field = self._normalize_education_field(field)
            if normalized_required_field in normalized_resume_field or normalized_resume_field in normalized_required_field:
                return True
        return related_allowed and self._is_related_education_field(normalized_resume_field)

    def _is_related_education_field(self, resume_field: str) -> bool:
        return any(field in self._normalize_education_field(resume_field) for field in RELATED_EDUCATION_FIELDS)

    def _normalize_education_field(self, field: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", str(field or "").lower()).strip()
        aliases = {
            "cse": "computer science",
            "cs": "computer science",
            "ce": "computer engineering",
            "ece": "electronics and communication engineering",
            "aiml": "artificial intelligence machine learning",
            "ai ml": "artificial intelligence machine learning",
        }
        for alias, replacement in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
            normalized = re.sub(rf"\b{re.escape(alias)}\b", replacement, normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _education_reason(self, status: str, edu: Dict[str, Any], requirement: Dict[str, Any]) -> str:
        resume_label = f"{edu.get('degree', '')} {edu.get('field', '')}".strip()
        if status == "aligned":
            return f"Resume education '{resume_label}' aligns with JD requirement '{requirement.get('raw_text', '')}'."
        if status == "partially_aligned":
            return f"Resume education '{resume_label}' is related but not an exact field match for '{requirement.get('raw_text', '')}'."
        return f"Resume education '{resume_label}' does not align with JD requirement '{requirement.get('raw_text', '')}'."

    def _related_candidate_skills(self, skill: str, candidate_skills: Set[str]) -> List[str]:
        if skill in candidate_skills:
            return []
        if satisfies_skill(skill, candidate_skills):
            related = sorted(candidate_skills.intersection(SKILL_RELATIONS.get(skill, set())))
            return related or sorted(candidate_skills)
        return []

    def _group_skill_matches(self, matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "matched": [item for item in matches if item["status"] == "matched"],
            "partial": [item for item in matches if item["status"] == "partial"],
            "missing": [item for item in matches if item["status"] == "missing"],
        }

    def _canonical_skills(self, skills: Iterable[str]) -> List[str]:
        canonical = []
        seen = set()
        for skill in skills or []:
            if not skill:
                continue
            normalized = get_canonical_skill(str(skill).strip())
            if normalized and normalized not in seen:
                seen.add(normalized)
                canonical.append(normalized)
        return canonical

    def _text_match(self, skill: str, text: str) -> bool:
        return skill.lower() in text.lower()

    def _skill_text_present(self, skill: str, text: str) -> bool:
        related = SKILL_RELATIONS.get(skill, set())
        candidates = {skill, *related}
        terms = {
            alias
            for canonical in candidates
            for alias in [canonical, *SKILL_ALIASES.get(canonical, [])]
            if alias
        }
        return any(
            re.search(rf"(?<![a-z0-9_]){re.escape(term.lower())}(?![a-z0-9_])", (text or "").lower())
            for term in terms
        )

    def _experience_text(self, resume_data: Dict[str, Any]) -> str:
        return "\n".join(
            " ".join(
                str(entry.get(field, ""))
                for field in ("title", "company", "date", "description", "skills_applied")
            )
            for entry in resume_data.get("experience", [])
        )

    def _project_text(self, resume_data: Dict[str, Any]) -> str:
        return "\n".join(self._project_evidence_text(project) for project in resume_data.get("projects", []))

    def _project_evidence_text(self, project: Dict[str, Any]) -> str:
        return " ".join(
            str(project.get(field, ""))
            for field in ("title", "description", "technologies", "technology", "skills")
            if project.get(field)
        )

    def _tokens(self, text: str) -> Set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9+#/.]+", (text or "").lower())
            if len(token) > 2 and token not in TEXT_STOP_WORDS
        }

    def _token_overlap(self, target_tokens: Set[str], evidence_tokens: Set[str]) -> float:
        if not target_tokens or not evidence_tokens:
            return 0.0
        return len(target_tokens.intersection(evidence_tokens)) / len(target_tokens)

"""
Deterministic job description validation gate.

This gate classifies extracted document text before Phase 2 parsing so resumes,
cover letters, tutorials, and keyword lists do not enter the JD pipeline.
"""

import re
from typing import Any, Dict, List, Set, Tuple

from config.job_description_config import (
    EMPLOYMENT_TYPES,
    JOB_DESCRIPTION_DOCUMENT_TYPE,
    JOB_SECTION_ALIASES,
    JOB_STRUCTURE_SECTION_NAMES,
    JOB_TITLE_TERMS,
    NEGATIVE_DOCUMENT_PATTERNS,
    NOT_A_JOB_DESCRIPTION,
    NOT_JOB_DESCRIPTION_DOCUMENT_TYPE,
    PREFERRED_LANGUAGE,
    REQUIRED_LANGUAGE,
    RESPONSIBILITY_LANGUAGE,
    RESUME_SIGNAL_SECTIONS,
    UNCERTAIN,
    UNSECTIONED_JD_STRUCTURE_SCORE,
    VALID_JOB_DESCRIPTION,
    JobDescriptionValidationConfig,
)
from utils.job_description_normalization import canonical_jd_section, clean_jd_item, heading_key
from utils.normalization import extract_matched_skills


class JobDescriptionValidator:
    """Classify text as a job description, not a job description, or uncertain."""

    def __init__(self, config: JobDescriptionValidationConfig | None = None):
        self.config = config or JobDescriptionValidationConfig()
        self.negative_patterns = [re.compile(pattern, re.I) for pattern in NEGATIVE_DOCUMENT_PATTERNS]
        self.command_patterns = [
            re.compile(pattern, re.I)
            for pattern in [
                r"^\s*(?:\$|>)\s+\w+",
                r"^\s*(?:npm|npx|pip|python|docker|kubectl|helm|git|curl|wget|choco|winget|powershell|sudo)\b",
                r"^\s*(?:set|export)\s+[A-Z_][A-Z0-9_]*=",
                r"^\s*[A-Z]:\\",
            ]
        ]
        self.job_title_pattern = re.compile(
            rf"\b(?:entry[-\s]?level|junior|senior|staff|principal|lead)?\s*"
            rf"(?:software|backend|front[-\s]?end|full[-\s]?stack|data|business\s+intelligence|"
            rf"machine\s+learning|ml|ai|devops|cloud|site\s+reliability|platform|security|qa|test|systems|analytics)?\s*"
            rf"(?:{'|'.join(JOB_TITLE_TERMS)})\b",
            re.I,
        )
        self.exp_years_pattern = re.compile(r"\b\d+\s*(?:\+|-\s*\d+|to\s+\d+)?\s*(?:years?|yrs?)\b", re.I)
        self.degree_pattern = re.compile(
            r"\b(?:bachelor|master|ph\.?d\.?|doctorate|b\.?\s?s\.?|m\.?\s?s\.?|"
            r"b\.?\s?tech|m\.?\s?tech|degree)\b",
            re.I,
        )
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
        self.phone_pattern = re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

    def validate_text(self, text: str) -> Dict[str, Any]:
        """Return a structured local classification result for extracted JD text."""
        if not text or not text.strip():
            return self._result(
                False,
                NOT_A_JOB_DESCRIPTION,
                0.0,
                "Document text is empty.",
                [],
                ["empty_document"],
                set(),
            )

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text_lower = text.lower()
        sections = self._detected_sections(lines)

        positive_score, positive_signals = self._positive_score(text, lines, sections)
        negative_score, negative_signals = self._negative_score(text_lower, lines, sections)
        confidence = max(0.0, min((positive_score - negative_score) / self.config.max_score, 1.0))

        structure_score = self._structure_score(text, lines, sections)
        job_context_score = self._job_context_score(text, lines)
        has_minimum_jd_shape = (
            (structure_score >= self.config.minimum_structure_score or self._has_unsectioned_jd_shape(text, lines))
            and job_context_score >= self.config.minimum_job_context_score
            and not self._looks_keyword_only(text, lines)
        )

        if (
            negative_score >= self.config.strong_negative_threshold * self.config.max_score
            and confidence < self.config.valid_threshold + 0.15
        ):
            return self._result(
                False,
                NOT_A_JOB_DESCRIPTION,
                confidence,
                "This document appears to be non-job material rather than a job description.",
                positive_signals,
                negative_signals,
                sections,
            )

        if confidence >= self.config.valid_threshold and has_minimum_jd_shape:
            return self._result(
                True,
                VALID_JOB_DESCRIPTION,
                confidence,
                "Job description structure detected.",
                positive_signals,
                negative_signals,
                sections,
            )

        if confidence >= self.config.uncertain_threshold and has_minimum_jd_shape:
            return self._result(
                False,
                UNCERTAIN,
                confidence,
                "We could not confidently identify this document as a job description.",
                positive_signals,
                negative_signals,
                sections,
            )

        return self._result(
            False,
            NOT_A_JOB_DESCRIPTION,
            confidence,
            "This document does not appear to be a job description.",
            positive_signals,
            negative_signals,
            sections,
        )

    def _positive_score(self, text: str, lines: List[str], sections: Set[str]) -> Tuple[float, List[str]]:
        score = 0.0
        signals: List[str] = []

        if self._has_job_title(lines):
            score += self.config.title_weight
            signals.append("job_title")

        structure_sections = sections.intersection(JOB_STRUCTURE_SECTION_NAMES)
        if structure_sections:
            score += min(len(structure_sections), 6) * self.config.section_weight
            signals.extend(f"{section}_section" for section in sorted(structure_sections))

        required_hits = self._count_phrase_hits(text, REQUIRED_LANGUAGE)
        if required_hits:
            score += min(required_hits, 3) * self.config.requirement_language_weight
            signals.append("required_language")

        preferred_hits = self._count_phrase_hits(text, PREFERRED_LANGUAGE)
        if preferred_hits:
            score += min(preferred_hits, 2) * self.config.preferred_language_weight
            signals.append("preferred_language")

        responsibility_hits = self._count_phrase_hits(text, RESPONSIBILITY_LANGUAGE)
        if responsibility_hits:
            score += min(responsibility_hits, 2) * self.config.responsibility_weight
            signals.append("responsibility_language")

        employment_signals = self._employment_context_signals(lines)
        if employment_signals:
            score += min(len(employment_signals), 3) * self.config.employment_context_weight
            signals.extend(sorted(employment_signals))

        if self.exp_years_pattern.search(text):
            score += self.config.experience_requirement_weight
            signals.append("experience_years")

        if self.degree_pattern.search(text):
            score += self.config.education_requirement_weight
            signals.append("education_requirement")

        skill_count = len(extract_matched_skills(text))
        if skill_count >= 2 and (structure_sections or required_hits or preferred_hits):
            score += self.config.skill_context_weight
            signals.append("skill_context")

        bullet_count = sum(1 for line in lines if re.match(r"^\s*(?:[-*+]|\d+[\.)])\s+", line))
        if bullet_count >= 2:
            score += self.config.bullet_weight
            signals.append("list_structure")

        return min(score, self.config.max_score), signals

    def _negative_score(self, text_lower: str, lines: List[str], sections: Set[str]) -> Tuple[float, List[str]]:
        score = 0.0
        signals: List[str] = []

        for pattern in self.negative_patterns:
            if pattern.search(text_lower):
                score += self.config.negative_signal_weight
                signals.append(pattern.pattern)

        if self._looks_like_resume(lines, sections):
            score += self.config.resume_signal_weight * 3
            signals.append("resume_structure")

        if self._looks_like_cover_letter(text_lower):
            score += self.config.resume_signal_weight * 2
            signals.append("cover_letter_language")

        if self._looks_keyword_only("\n".join(lines), lines):
            score += self.config.resume_signal_weight * 2
            signals.append("keyword_list_only")

        command_count = 0
        for line in lines:
            if any(pattern.search(line) for pattern in self.command_patterns):
                command_count += 1
        if command_count >= 3:
            score += self.config.command_heavy_weight
            signals.append("command_heavy")
        if lines and command_count / len(lines) >= 0.25:
            score += self.config.command_heavy_weight
            signals.append("high_command_ratio")

        return min(score, self.config.max_score), signals

    def _detected_sections(self, lines: List[str]) -> Set[str]:
        detected = set()
        for line in lines:
            section, _ = canonical_jd_section(line, JOB_SECTION_ALIASES)
            if section:
                detected.add(section)
        return detected

    def _structure_score(self, text: str, lines: List[str], sections: Set[str]) -> float:
        structure_count = len(sections.intersection(JOB_STRUCTURE_SECTION_NAMES))
        if structure_count:
            return min(structure_count * self.config.section_weight, self.config.max_score) / self.config.max_score
        if self._has_unsectioned_jd_shape(text, lines):
            return UNSECTIONED_JD_STRUCTURE_SCORE
        return 0.0

    def _job_context_score(self, text: str, lines: List[str]) -> float:
        score = 0.0
        if self._has_job_title(lines):
            score += self.config.title_weight
        score += min(len(self._employment_context_signals(lines)), 3) * self.config.employment_context_weight
        if self._count_phrase_hits(text, REQUIRED_LANGUAGE):
            score += self.config.requirement_language_weight
        if self._count_phrase_hits(text, RESPONSIBILITY_LANGUAGE):
            score += self.config.responsibility_weight
        if self.exp_years_pattern.search(text):
            score += self.config.experience_requirement_weight
        return min(score, self.config.max_score) / self.config.max_score

    def _has_job_title(self, lines: List[str]) -> bool:
        for line in lines[:8]:
            cleaned = clean_jd_item(line)
            if not cleaned or len(cleaned) > 100:
                continue
            if canonical_jd_section(cleaned, JOB_SECTION_ALIASES)[0]:
                continue
            explicit = re.match(r"^(?:job\s+title|position|role)\s*[:\-]\s*(?P<title>.+)$", cleaned, re.I)
            candidate = explicit.group("title").strip() if explicit else cleaned
            if self.job_title_pattern.search(candidate) and not candidate.endswith((".", ";")):
                return True
        return False

    def _has_employment_context(self, lines: List[str]) -> bool:
        return bool(self._employment_context_signals(lines))

    def _employment_context_signals(self, lines: List[str]) -> Set[str]:
        signals: Set[str] = set()
        employment_type_keys = {heading_key(value) for value in EMPLOYMENT_TYPES}
        for line in lines[:12]:
            cleaned = clean_jd_item(line).lower()
            if re.match(r"^(?:company|employer|organization|about)\s*[:\-]", cleaned):
                signals.add("company_metadata")
            if re.match(r"^(?:job\s+id|job\s+number|requisition\s+id|req\s+id|posting\s+id)\s*[:#\-]", cleaned):
                signals.add("job_id_metadata")
            if re.match(r"^(?:location|work\s+location)\s*[:\-]", cleaned):
                signals.add("location_metadata")
            if re.match(r"^(?:job\s+type|employment\s+type|type)\s*[:\-]", cleaned):
                signals.add("employment_type_metadata")
            if heading_key(cleaned) in employment_type_keys:
                signals.add("employment_type_metadata")
            if re.search(r"\b(?:candidate|applicant|trainee|intern|internship|employment|industrial training)\b", cleaned):
                signals.add("candidate_or_employment_context")
        return signals

    def _has_unsectioned_jd_shape(self, text: str, lines: List[str]) -> bool:
        has_title = self._has_job_title(lines)
        has_requirement = bool(self._count_phrase_hits(text, REQUIRED_LANGUAGE))
        has_responsibility = bool(self._count_phrase_hits(text, RESPONSIBILITY_LANGUAGE))
        has_employment = self._has_employment_context(lines)
        return has_title and has_requirement and (has_responsibility or has_employment)

    def _looks_like_resume(self, lines: List[str], sections: Set[str]) -> bool:
        text = "\n".join(lines)
        has_contact = bool(self.email_pattern.search(text) or self.phone_pattern.search(text))
        resume_heading_count = 0
        for line in lines:
            cleaned_key = heading_key(clean_jd_item(line).rstrip(":"))
            if cleaned_key in RESUME_SIGNAL_SECTIONS:
                resume_heading_count += 1
        has_candidate_name = self._looks_like_candidate_name(lines)
        jd_requirement_sections = sections.intersection({"required_qualifications", "responsibilities", "required_skills"})
        return has_contact and has_candidate_name and resume_heading_count >= 1 and not jd_requirement_sections

    def _looks_like_candidate_name(self, lines: List[str]) -> bool:
        for line in lines[:5]:
            cleaned = clean_jd_item(line)
            if len(cleaned) < 3 or len(cleaned) > 40:
                continue
            if re.search(r"(@|www|\.com|http|job|role|position|company|location)", cleaned, re.I):
                continue
            if re.search(r"\d", cleaned):
                continue
            words = cleaned.split()
            if 2 <= len(words) <= 4 and all(word[0].isalpha() for word in words):
                if any(word[0].isupper() for word in words):
                    return True
        return False

    def _looks_like_cover_letter(self, text_lower: str) -> bool:
        return bool(
            re.search(r"\bdear\s+(?:hiring\s+manager|recruiter|team)\b", text_lower)
            or re.search(r"\bi am (?:excited|writing) to apply\b", text_lower)
            or re.search(r"\bsincerely\b|\bbest regards\b", text_lower)
        )

    def _looks_keyword_only(self, text: str, lines: List[str]) -> bool:
        if not lines:
            return True
        sections = self._detected_sections(lines)
        has_jd_language = (
            self._count_phrase_hits(text, REQUIRED_LANGUAGE)
            or self._count_phrase_hits(text, RESPONSIBILITY_LANGUAGE)
            or self._count_phrase_hits(text, PREFERRED_LANGUAGE)
        )
        if sections or has_jd_language:
            return False
        known_skills = extract_matched_skills(text)
        short_lines = [line for line in lines if len(clean_jd_item(line)) <= 40]
        return bool(known_skills) and len(short_lines) == len(lines) and len(lines) <= 20

    def _count_phrase_hits(self, text: str, phrases: Tuple[str, ...]) -> int:
        text_lower = text.lower()
        return sum(1 for phrase in phrases if re.search(rf"\b{re.escape(phrase.lower())}\b", text_lower))

    def _result(
        self,
        valid: bool,
        classification: str,
        confidence: float,
        reason: str,
        positive_signals: List[str],
        negative_signals: List[str],
        sections: Set[str],
    ) -> Dict[str, Any]:
        if classification == VALID_JOB_DESCRIPTION:
            document_type = JOB_DESCRIPTION_DOCUMENT_TYPE
            message = "Job description accepted for parsing."
        elif classification == UNCERTAIN:
            document_type = UNCERTAIN
            message = "We could not confidently identify this document as a job description."
        else:
            document_type = NOT_JOB_DESCRIPTION_DOCUMENT_TYPE
            message = (
                "This document does not appear to be a job description. Please provide a posting "
                "with role responsibilities, requirements, skills, or qualifications."
            )

        return {
            "valid": valid,
            "document_type": document_type,
            "classification": classification,
            "confidence": round(confidence, 2),
            "reason": reason,
            "signals": {
                "positive": positive_signals,
                "negative": negative_signals,
                "sections": sorted(sections),
            },
            "message": message,
        }

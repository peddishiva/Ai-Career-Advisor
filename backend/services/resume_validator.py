"""
Deterministic resume document validation.

This gate classifies extracted document text before parsing/scoring so technical
documentation with resume-adjacent keywords does not enter the career analysis pipeline.
"""

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from utils.normalization import normalize_resume_section_heading


VALID_RESUME = "valid_resume"
NOT_A_RESUME = "not_a_resume"
UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class ResumeValidationConfig:
    """Tunable weights and thresholds for local resume validation."""

    valid_threshold: float = 0.58
    uncertain_threshold: float = 0.38
    strong_negative_threshold: float = 0.48
    minimum_structure_score: float = 0.18
    minimum_identity_or_career_score: float = 0.12
    max_score: float = 10.0

    email_weight: float = 1.2
    phone_weight: float = 0.8
    name_weight: float = 0.7
    section_weight: float = 0.9
    career_weight: float = 0.9
    degree_weight: float = 0.8
    date_weight: float = 0.5
    bullet_weight: float = 0.4
    candidate_language_weight: float = 0.5
    sparse_resume_structure_weight: float = 1.4

    negative_signal_weight: float = 1.0
    command_heavy_weight: float = 1.4


class ResumeValidator:
    """Classify text as valid resume, not a resume, or uncertain using explainable signals."""

    def __init__(self, config: ResumeValidationConfig | None = None):
        self.config = config or ResumeValidationConfig()
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
        self.phone_pattern = re.compile(r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        self.section_patterns = {
            "skills": re.compile(r'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?(?:technical\s+skills|skills\s*&?\s*tools|core\s+competencies|technologies|tech\s+stack|skills)\s*(?::\s*\S.*|[:\-]?\s*)$', re.I),
            "experience": re.compile(r'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?(?:work\s+experience|professional\s+experience|employment\s+history|experience|work\s+history|selected\s+work)\s*(?::\s*\S.*|[:\-]?\s*)$', re.I),
            "projects": re.compile(r'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?(?:technical\s+projects|academic\s+projects|personal\s+projects|selected\s+projects|projects|key\s+projects)\s*(?::\s*\S.*|[:\-]?\s*)$', re.I),
            "education": re.compile(r'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?(?:education|academic\s+background|academics|qualifications|academic\s+history)\s*(?::\s*\S.*|[:\-]?\s*)$', re.I),
            "certifications": re.compile(r'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?(?:certifications\s*&?\s*achievements|certifications|licenses\s*&?\s*certifications|certificates|courses|achievements)\s*(?::\s*\S.*|[:\-]?\s*)$', re.I),
        }
        self.job_title_pattern = re.compile(
            r'\b(?:software|backend|frontend|full\s+stack|data|business\s+intelligence|machine\s+learning|ml|ai|devops|cloud|product)\s+'
            r'(?:engineer|developer|analyst|scientist|consultant|intern|associate|manager)\b',
            re.I
        )
        self.employer_pattern = re.compile(r'\b(?:at|with|for)\s+[A-Z][A-Za-z0-9&.,\-\s]{2,40}\b')
        self.date_range_pattern = re.compile(
            r'\b(?:20\d{2}|19\d{2})\s*(?:-|to|–|—)\s*(?:present|current|20\d{2}|19\d{2})\b',
            re.I
        )
        self.degree_pattern = re.compile(
            r'\b(?:bachelor|master|ph\.?d\.?|doctorate|b\.?\s?s\.?|b\.?\s?a\.?|m\.?\s?s\.?|m\.?\s?a\.?|b\.?\s?tech|m\.?\s?tech|mba)\b',
            re.I
        )
        self.negative_patterns = [
            re.compile(pattern, re.I)
            for pattern in [
                r'\binstallation\s+guide\b',
                r'\bsetup\s+guide\b',
                r'\btutorial\b',
                r'\bdocumentation\b',
                r'\breadme\b',
                r'\buser\s+manual\b',
                r'\bcommand\s+reference\b',
                r'\bconfiguration\s+guide\b',
                r'\btroubleshooting\b',
                r'\brelease\s+notes\b',
                r'\bproduct\s+documentation\b',
                r'\barticle\b',
                r'\bblog\b',
                r'\bchapter\b',
                r'\binvoice\b',
                r'\bresearch\s+paper\b',
                r'\bstep[-\s]by[-\s]step\b',
                r'\bcopy\s+and\s+paste\b',
                r'\brun\s+the\s+following\s+command\b',
            ]
        ]
        self.command_patterns = [
            re.compile(pattern, re.I)
            for pattern in [
                r'^\s*(?:\$|>)\s+\w+',
                r'^\s*(?:npm|npx|pip|python|docker|kubectl|helm|git|curl|wget|choco|winget|powershell|sudo)\b',
                r'^\s*(?:set|export)\s+[A-Z_][A-Z0-9_]*=',
                r'^\s*[A-Z]:\\',
            ]
        ]

    def validate_text(self, text: str) -> Dict[str, Any]:
        """Return a structured local classification result for extracted document text."""
        if not text or not text.strip():
            return self._result(False, NOT_A_RESUME, 0.0, "Document text is empty.", [], ["empty_document"])

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text_lower = text.lower()

        positive_score, positive_signals = self._positive_score(text, lines)
        negative_score, negative_signals = self._negative_score(text_lower, lines)
        confidence = max(0.0, min((positive_score - negative_score) / self.config.max_score, 1.0))
        structure_score = self._structure_score(lines)
        identity_or_career_score = self._identity_or_career_score(text, lines)

        if negative_score >= self.config.strong_negative_threshold * self.config.max_score and confidence < self.config.valid_threshold + 0.15:
            return self._result(
                False,
                NOT_A_RESUME,
                confidence,
                "This document appears to be documentation or setup material rather than a resume.",
                positive_signals,
                negative_signals
            )

        has_minimum_resume_shape = (
            structure_score >= self.config.minimum_structure_score and
            identity_or_career_score >= self.config.minimum_identity_or_career_score
        )

        if confidence >= self.config.valid_threshold and has_minimum_resume_shape:
            return self._result(
                True,
                VALID_RESUME,
                confidence,
                "Resume structure detected.",
                positive_signals,
                negative_signals
            )

        if confidence >= self.config.uncertain_threshold:
            return self._result(
                False,
                UNCERTAIN,
                confidence,
                "We could not confidently identify this document as a resume.",
                positive_signals,
                negative_signals
            )

        return self._result(
            False,
            NOT_A_RESUME,
            confidence,
            "This document does not appear to be a resume.",
            positive_signals,
            negative_signals
        )

    def _positive_score(self, text: str, lines: List[str]) -> tuple[float, List[str]]:
        score = 0.0
        signals: List[str] = []

        if self.email_pattern.search(text):
            score += self.config.email_weight
            signals.append("email")
        if self.phone_pattern.search(text):
            score += self.config.phone_weight
            signals.append("phone")
        if self._looks_like_candidate_name(lines):
            score += self.config.name_weight
            signals.append("candidate_name")

        sections = self._detected_sections(lines)
        if sections:
            section_score = min(len(sections), 5) * self.config.section_weight
            score += section_score
            signals.extend(f"{section}_section" for section in sorted(sections))

        career_hits = len(self.job_title_pattern.findall(text))
        if career_hits:
            score += min(career_hits, 3) * self.config.career_weight
            signals.append("career_titles")
        if self.employer_pattern.search(text):
            score += self.config.career_weight
            signals.append("employer_language")
        if self.date_range_pattern.search(text):
            score += self.config.date_weight
            signals.append("employment_date_range")
        if self.degree_pattern.search(text):
            score += self.config.degree_weight
            signals.append("degree")

        bullet_count = sum(1 for line in lines if re.match(r'^\s*(?:[-*•]|\d+\.)\s+', line))
        if bullet_count >= 2:
            score += self.config.bullet_weight
            signals.append("resume_bullets")

        if re.search(r'\b(?:developed|built|led|managed|implemented|designed|analyzed|created|deployed)\b', text, re.I):
            score += self.config.candidate_language_weight
            signals.append("candidate_action_language")
            
        if self._has_sparse_resume_structure(text, lines, sections):
            score += self.config.sparse_resume_structure_weight
            signals.append("sparse_resume_structure")

        return min(score, self.config.max_score), signals

    def _negative_score(self, text_lower: str, lines: List[str]) -> tuple[float, List[str]]:
        score = 0.0
        signals: List[str] = []

        for pattern in self.negative_patterns:
            if pattern.search(text_lower):
                score += self.config.negative_signal_weight
                signals.append(pattern.pattern)

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

    def _detected_sections(self, lines: List[str]) -> set[str]:
        detected = set()
        for line in lines:
            normalized_line = normalize_resume_section_heading(line)
            for section, pattern in self.section_patterns.items():
                if pattern.match(normalized_line):
                    detected.add(section)
        return detected

    def _structure_score(self, lines: List[str]) -> float:
        return min(len(self._detected_sections(lines)) * self.config.section_weight, self.config.max_score) / self.config.max_score

    def _identity_or_career_score(self, text: str, lines: List[str]) -> float:
        score = 0.0
        if self.email_pattern.search(text):
            score += self.config.email_weight
        if self.phone_pattern.search(text):
            score += self.config.phone_weight
        if self._looks_like_candidate_name(lines):
            score += self.config.name_weight
        if self.job_title_pattern.search(text):
            score += self.config.career_weight
        if self.degree_pattern.search(text):
            score += self.config.degree_weight
        return min(score, self.config.max_score) / self.config.max_score
        
    def _has_sparse_resume_structure(self, text: str, lines: List[str], sections: set[str]) -> bool:
        """Recognize compact fresher resumes with identity plus core resume sections."""
        has_identity = bool(self.email_pattern.search(text)) and self._looks_like_candidate_name(lines)
        has_skills = "skills" in sections
        has_education = "education" in sections or bool(self.degree_pattern.search(text))
        has_project_or_cert = "projects" in sections or "certifications" in sections
        return has_identity and has_skills and (has_education or has_project_or_cert)

    def _looks_like_candidate_name(self, lines: List[str]) -> bool:
        title_terms = re.compile(
            r'\b(?:api|readme|installation|install|setup|guide|documentation|docs|tutorial|'
            r'troubleshooting|manual|report|article|blog|docker|kubernetes|windows|linux|'
            r'python|javascript|node|aws|configuration|command|reference|resume\s+analysis)\b',
            re.I
        )
        for line in lines[:5]:
            if len(line) < 3 or len(line) > 40:
                continue
            if re.search(r'(@|www|\.com|http|curriculum)', line, re.I):
                continue
            if re.search(r'\d', line) or title_terms.search(line):
                continue
            words = line.split()
            if 2 <= len(words) <= 4 and all(word[0].isalpha() for word in words):
                if any(word[0].isupper() for word in words):
                    return True
        return False

    def _result(
        self,
        valid: bool,
        document_type: str,
        confidence: float,
        reason: str,
        positive_signals: List[str],
        negative_signals: List[str]
    ) -> Dict[str, Any]:
        message = None
        if document_type == NOT_A_RESUME:
            message = (
                "This document does not appear to be a resume. Please upload a resume containing "
                "sections such as Skills, Education, Experience, or Projects."
            )
        elif document_type == UNCERTAIN:
            message = (
                "We could not confidently identify this document as a resume. Please upload a clearer "
                "or more complete resume."
            )

        result = {
            "valid": valid,
            "document_type": document_type,
            "confidence": round(confidence, 2),
            "reason": reason,
            "signals": {
                "positive": positive_signals,
                "negative": negative_signals,
            },
            "config": asdict(self.config),
        }
        if message:
            result["message"] = message
        return result

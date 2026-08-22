"""
Central configuration for deterministic resume-to-job matching.
"""

from typing import Dict, Set


JOB_MATCH_WEIGHTS: Dict[str, float] = {
    "required_skills": 0.35,
    "preferred_skills": 0.10,
    "experience": 0.20,
    "projects": 0.15,
    "education": 0.10,
    "certifications": 0.05,
    "responsibilities": 0.05,
}

READINESS_THRESHOLDS = {
    "high_score": 75,
    "moderate_score": 50,
    "high_min_required_skill_coverage": 0.85,
    "moderate_min_required_skill_coverage": 0.50,
    "max_high_critical_gaps": 0,
    "max_moderate_critical_gaps": 4,
}

SKILL_STATUS_SCORES = {
    "matched": 100,
    "partial": 50,
    "missing": 0,
}

MAX_COMPONENT_SCORE = 100
PARTIAL_SKILL_COVERAGE_CREDIT = 0.5

SKILL_EVIDENCE_THRESHOLDS = {
    "matched": 55,
    "partial": 1,
}

EXPERIENCE_ALIGNMENT_WEIGHTS = {
    "years": 0.65,
    "domain": 0.35,
}

PROJECT_ALIGNMENT_WEIGHTS = {
    "skill_coverage": 0.75,
    "project_depth": 0.25,
}
PROJECT_DEPTH_TARGET_COUNT = 2.0

RESPONSIBILITY_ALIGNMENT_WEIGHTS = {
    "skills": 0.60,
    "tokens": 0.40,
}

RESPONSIBILITY_STATUS_THRESHOLDS = {
    "matched": 65,
    "partial": 30,
}

CERTIFICATION_STATUS_SCORES = {
    "matched": 100,
    "missing": 0,
}

EDUCATION_STATUS_SCORES = {
    "aligned": 100,
    "partially_aligned": 60,
    "not_aligned": 0,
    "missing": 0,
}

EXPERIENCE_NO_YEAR_CONTEXT_SCORE = 65
EXPERIENCE_UNKNOWN_YEAR_SCORE = 35
EXPERIENCE_UNMET_YEAR_MAX_SCORE = 70
CERTIFICATION_TOKEN_MATCH_THRESHOLD = 0.50

RELATED_EDUCATION_FIELDS = {
    "artificial intelligence",
    "computer",
    "computer applications",
    "computer engineering",
    "computer science",
    "data",
    "engineering",
    "information systems",
    "information technology",
    "machine learning",
    "mathematics",
    "software",
    "statistics",
}

TEXT_STOP_WORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
    "you",
    "will",
}

RECOMMENDATION_LIMIT = 5

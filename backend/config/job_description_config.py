"""
Central configuration for deterministic job description validation and parsing.
"""

from dataclasses import dataclass
from typing import Dict, Set, Tuple


VALID_JOB_DESCRIPTION = "valid_job_description"
NOT_A_JOB_DESCRIPTION = "not_a_job_description"
UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class JobDescriptionValidationConfig:
    """Tunable weights and thresholds for local JD validation."""

    valid_threshold: float = 0.58
    uncertain_threshold: float = 0.35
    strong_negative_threshold: float = 0.48
    minimum_structure_score: float = 0.16
    minimum_job_context_score: float = 0.16
    max_score: float = 10.0

    title_weight: float = 1.2
    section_weight: float = 0.9
    responsibility_weight: float = 0.9
    requirement_language_weight: float = 1.0
    preferred_language_weight: float = 0.5
    employment_context_weight: float = 0.8
    skill_context_weight: float = 0.8
    experience_requirement_weight: float = 0.7
    education_requirement_weight: float = 0.5
    bullet_weight: float = 0.3

    negative_signal_weight: float = 1.1
    resume_signal_weight: float = 1.2
    command_heavy_weight: float = 1.4


JOB_DESCRIPTION_DOCUMENT_TYPE = "job_description"
NOT_JOB_DESCRIPTION_DOCUMENT_TYPE = "not_job_description"
UNSECTIONED_JD_STRUCTURE_SCORE = 0.22
MAX_JOB_DESCRIPTION_FILE_SIZE_BYTES = 5 * 1024 * 1024


JOB_SECTION_ALIASES: Dict[str, Tuple[str, ...]] = {
    "overview": (
        "about the role",
        "role overview",
        "job overview",
        "job description",
        "description",
        "overview",
        "summary",
    ),
    "responsibilities": (
        "responsibilities",
        "role responsibilities",
        "key responsibilities",
        "key job responsibilities",
        "what you will do",
        "what youll do",
        "what you'll do",
        "what you do",
        "what youll be doing",
        "what you'll be doing",
        "day to day",
        "a day in the life",
    ),
    "required_qualifications": (
        "requirements",
        "required qualifications",
        "basic qualifications",
        "minimum qualifications",
        "must have",
        "must haves",
        "required experience",
        "qualifications",
    ),
    "preferred_qualifications": (
        "preferred",
        "preferred qualifications",
        "nice to have",
        "nice-to-have",
        "desired qualifications",
        "bonus",
        "bonus points",
        "plus",
    ),
    "skills": (
        "skills",
        "technical skills",
        "technologies",
        "technology stack",
        "tech stack",
    ),
    "required_skills": (
        "required skills",
        "must have skills",
        "must-have skills",
        "core skills",
    ),
    "preferred_skills": (
        "preferred skills",
        "nice to have skills",
        "nice-to-have skills",
        "bonus skills",
    ),
    "experience": (
        "experience",
        "experience requirements",
        "work experience",
    ),
    "education": (
        "education",
        "education requirements",
        "academic requirements",
    ),
    "certifications": (
        "certifications",
        "licenses",
        "licenses and certifications",
        "certification requirements",
    ),
    "benefits": (
        "benefits",
        "perks",
        "compensation",
        "salary",
    ),
    "job_details": (
        "job details",
        "job detail",
        "role details",
        "position details",
    ),
    "about_company": (
        "about us",
        "about the company",
        "company overview",
    ),
    "application": (
        "how to apply",
        "application process",
        "equal opportunity",
    ),
}


REQUIRED_SECTION_NAMES: Set[str] = {
    "required_qualifications",
    "required_skills",
    "skills",
    "experience",
    "education",
}

PREFERRED_SECTION_NAMES: Set[str] = {
    "preferred_qualifications",
    "preferred_skills",
}

NON_REQUIREMENT_SECTION_NAMES: Set[str] = {
    "overview",
    "responsibilities",
    "job_details",
    "benefits",
    "about_company",
    "application",
}

JOB_STRUCTURE_SECTION_NAMES: Set[str] = {
    "overview",
    "responsibilities",
    "required_qualifications",
    "preferred_qualifications",
    "required_skills",
    "preferred_skills",
    "skills",
    "experience",
    "education",
    "certifications",
    "job_details",
}


REQUIRED_LANGUAGE = (
    "required",
    "must",
    "minimum",
    "essential",
    "need",
    "needs",
    "proficient in",
    "required experience",
    "hands-on experience",
    "strong knowledge",
    "strong experience",
)

PREFERRED_LANGUAGE = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "bonus",
    "desirable",
    "desired",
    "plus",
    "would be a plus",
)

RESPONSIBILITY_LANGUAGE = (
    "you will",
    "responsible for",
    "responsibilities include",
    "build",
    "design",
    "develop",
    "implement",
    "analyze",
    "manage",
    "collaborate",
    "own",
)

EMPLOYMENT_TYPES = (
    "full-time",
    "full time",
    "part-time",
    "part time",
    "contract",
    "contractor",
    "internship",
    "temporary",
    "remote",
    "hybrid",
    "on-site",
    "onsite",
)

JOB_TITLE_TERMS = (
    "engineer",
    "developer",
    "analyst",
    "scientist",
    "consultant",
    "intern",
    "associate",
    "manager",
    "architect",
    "administrator",
    "specialist",
    "devops",
    "sre",
    "qa",
    "sdet",
)

DEGREE_FIELD_KEYWORDS = (
    "computer science",
    "software engineering",
    "information technology",
    "data science",
    "data analytics",
    "statistics",
    "mathematics",
    "engineering",
    "business",
    "economics",
    "analytics",
)

CAPABILITY_KEYWORDS = (
    "data structures",
    "algorithms",
    "object oriented",
    "object-oriented",
    "oop",
    "system design",
    "problem solving",
    "problem-solving",
    "communication",
    "teamwork",
    "distributed systems",
    "distributed/backend systems",
    "event-driven architecture",
    "high-scale systems",
    "production systems",
    "modern engineering practices",
)

CAPABILITY_CANONICAL_SKILLS = (
    "Data Structures",
    "Algorithms",
    "OOP",
    "System Design",
    "Problem Solving",
    "Communication",
    "Teamwork",
)

CERTIFICATION_KEYWORDS = (
    "certification",
    "certifications",
    "certified",
    "license",
    "licenses",
    "aws certified",
    "azure certified",
    "google cloud certified",
    "pmp",
    "cissp",
    "cka",
    "ckad",
)

ELIGIBILITY_CONTEXT_MARKERS = (
    "pursu",
    "clear",
    "enroll",
    "register",
    "member",
    "membership",
    "eligible",
    "trainee",
    "articleship",
    "industrial training",
    "professional qualification",
    "professional program",
    "professional body",
    "license",
    "licensed",
    "qualification",
)

ELIGIBILITY_STATUS_PATTERNS = (
    r"\bmust\b.{0,100}\b(?:pursu\w*|clear\w*|enroll\w*|register\w*|member\w*|eligible|trainee\w*|articleship|industrial\s+training)\b",
    r"\b(?:currently|actively|active|registered|licensed|eligible|mandatory|only(?:\s+candidates?)?)\b.{0,100}\b(?:pursu\w*|clear\w*|enroll\w*|register\w*|member\w*|trainee\w*|articleship|industrial\s+training|professional\s+(?:qualification|program|body)|license|qualification)\b",
    r"\b(?:pursu\w*|clear\w*|enroll\w*|register\w*|member\w*|eligible|trainee\w*|articleship|industrial\s+training|professional\s+(?:qualification|program|body)|license|qualification)\b.{0,100}\b(?:required|preferred|preferably|must|mandatory)\b",
    r"\b(?:must|candidate\s+must)\b.{0,80}\b(?:hold|have)\b.{0,80}\bprofessional\s+qualification\b",
    r"\brequired\s+professional\s+qualification\b",
)

NEGATIVE_DOCUMENT_PATTERNS = (
    r"\binstallation\s+guide\b",
    r"\bsetup\s+guide\b",
    r"\btutorial\b",
    r"\bdocumentation\b",
    r"\breadme\b",
    r"\buser\s+manual\b",
    r"\bcommand\s+reference\b",
    r"\bconfiguration\s+guide\b",
    r"\btroubleshooting\b",
    r"\brelease\s+notes\b",
    r"\bproduct\s+documentation\b",
    r"\b(?:blog\s+article|news\s+article|this\s+article|article\s+discusses|article\s+explains)\b",
    r"\bblog\b",
    r"\bchapter\b",
    r"\bstep[-\s]by[-\s]step\b",
    r"\bcopy\s+and\s+paste\b",
    r"\brun\s+the\s+following\s+command\b",
)

RESUME_SIGNAL_SECTIONS = {
    "projects",
    "professional experience",
    "work experience",
    "employment history",
    "academic projects",
    "personal projects",
}

PARSING_LIMITS = {
    "max_section_lines": 120,
    "max_responsibilities": 20,
    "max_qualifications": 30,
    "max_experience_requirements": 12,
    "max_education_requirements": 8,
    "max_certifications": 12,
}

"""Configuration for the curated Phase 3B knowledge layer."""

from typing import Dict


KNOWLEDGE_BASE_VERSION = "3.1.0"

DEFAULT_MAX_RESULTS = 5
MAX_RESULTS = 10
MAX_QUERY_CHARS = 400
MAX_QUERY_TERMS = 64
MAX_KNOWLEDGE_CONTENT_CHARS = 4_000

# Lower values sort earlier when relevance scores tie.
CATEGORY_PRIORITY: Dict[str, int] = {
    "skill": 10,
    "role": 20,
    "career_path": 30,
    "learning_guidance": 40,
    "interview_topic": 50,
    "resume_guidance": 60,
    "job_requirement_concept": 70,
}

TRUST_RANK: Dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


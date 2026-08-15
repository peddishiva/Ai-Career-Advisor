"""
Backend configuration package.
"""

from config.skill_aliases import SKILL_ALIASES, ALIAS_TO_CANONICAL, get_canonical_skill, get_all_canonical_skills
from config.roles import ROLE_DEFINITIONS
from config.scoring_config import (
    PROFILE_STRENGTH_WEIGHTS,
    ROLE_MATCH_WEIGHTS,
    SKILL_EVIDENCE_POINTS,
    IMPACT_ACTION_VERBS,
    ALIGNMENT_THRESHOLDS
)

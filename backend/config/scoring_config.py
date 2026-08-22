"""
Scoring Engine Weights & Configuration Constants
Centralizes all evidence multipliers, section weights, and scoring thresholds.
"""

from typing import Dict

# Weights for Overall Profile Strength Score (sums to 100%)
PROFILE_STRENGTH_WEIGHTS: Dict[str, float] = {
    "skills_evidence": 0.35,      # Breadth, depth, and evidence of verified skills
    "experience_evidence": 0.25,  # Professional experience density, relevance & action verbs
    "projects_evidence": 0.20,    # Project descriptions, complexity & technical depth
    "education_credentials": 0.10,# Verified degree level & field alignment
    "best_role_alignment": 0.10   # How cleanly profile maps into at least one career track
}

# Weights for Role Matching Score (sums to 100%)
ROLE_MATCH_WEIGHTS: Dict[str, float] = {
    "required_skills": 0.45,      # Critical required skills match
    "preferred_skills": 0.20,     # Bonus preferred skills match
    "experience_relevance": 0.20, # Relevance of work experience to target role
    "projects_relevance": 0.10,   # Relevance of projects to target role
    "education_relevance": 0.05   # Relevance of educational discipline
}

# Skill Evidence Scoring points per verified occurrence
SKILL_EVIDENCE_POINTS = {
    "mentioned_elsewhere": 10,    # Detected outside a dedicated evidence section
    "in_skills_section": 20,      # Stated in Skills section
    "in_project_entry": 30,       # Applied in at least one project
    "in_multiple_projects": 10,   # Applied across multiple projects
    "in_experience_entry": 35,    # Demonstrated in work experience
    "action_impact_context": 15,  # Associated with impact/action verbs in bullet points
    "max_score": 100
}

# Impact and Action Verbs indicating applied skill proficiency
IMPACT_ACTION_VERBS = [
    "developed", "built", "engineered", "designed", "architected",
    "implemented", "optimized", "scaled", "created", "deployed",
    "managed", "led", "automated", "analyzed", "reduced", "increased",
    "improved", "delivered", "integrated", "refactored", "spearheaded"
]

# Alignment Thresholds
ALIGNMENT_THRESHOLDS = {
    "high": 75,
    "medium": 50,
    "low": 0
}

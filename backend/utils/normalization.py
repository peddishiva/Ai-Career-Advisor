"""
Text & Skill Normalization Utilities
Handles case-insensitive tokenization, canonical skill resolution, and alias normalization.
"""

import re
from typing import List, Set, Dict, Tuple
from config.skill_aliases import ALIAS_TO_CANONICAL, SKILL_ALIASES, get_canonical_skill

def normalize_text(text: str) -> str:
    """Normalize raw text for uniform string matching."""
    if not text:
        return ""
    # Standardize whitespace and quotes
    normalized = re.sub(r'[\r\n\t]+', ' ', text)
    normalized = re.sub(r'[""\'\']', "'", normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()

def extract_matched_skills(text: str) -> Dict[str, int]:
    """
    Extract all known canonical skills present in the given text.
    Returns a dictionary mapping canonical skill names to their occurrence counts.
    Avoids greedy false positives using word boundaries.
    """
    if not text:
        return {}
    
    text_lower = f" {text.lower()} "
    # Replace common punctuation with spaces except those in skill names like c++, c#, .net, node.js, ci/cd
    clean_text = re.sub(r'[,;:|/\\()\[\]{}!?]', ' ', text_lower)
    
    found_skills: Dict[str, int] = {}
    
    for canonical, aliases in SKILL_ALIASES.items():
        all_terms = [canonical.lower()] + [a.lower() for a in aliases]
        count = 0
        for term in all_terms:
            # Construct boundary-safe regex pattern
            escaped_term = re.escape(term)
            # Match term when flanked by non-alphanumeric or start/end
            pattern = rf'(?:^|(?<=[^a-zA-Z0-9_#+-])){escaped_term}(?=[^a-zA-Z0-9_#+-]|$)'
            matches = len(re.findall(pattern, text_lower))
            count += matches
        
        if count > 0:
            found_skills[canonical] = count
            
    return found_skills

def normalize_skill_list(skills: List[str]) -> List[str]:
    """Normalize a list of skill strings into deduplicated canonical skill names."""
    canonical_set: Set[str] = set()
    for s in skills:
        if not s or not s.strip():
            continue
        # Check if multiple skills are comma-separated or slash-separated
        sub_skills = re.split(r'[,/|•\n]', s)
        for sub in sub_skills:
            cleaned = sub.strip()
            if cleaned:
                canonical_name = get_canonical_skill(cleaned)
                canonical_set.add(canonical_name)
                
    return sorted(list(canonical_set))

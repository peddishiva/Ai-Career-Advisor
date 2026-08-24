"""Normalization helpers that reuse the existing canonical skill system."""

import re
from typing import Iterable, List

from config.roles import ROLE_DEFINITIONS
from config.skill_aliases import get_all_canonical_skills, get_canonical_skill
from utils.normalization import normalize_text


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[+#/.\-][a-z0-9+#/.\-]+)*", re.I)


def tokenize(text: str) -> List[str]:
    """Return stable lowercase lexical tokens."""
    return sorted(set(_TOKEN_PATTERN.findall(normalize_text(text).lower())))


def canonical_skill_reference(value: str) -> str:
    """Resolve a skill reference through the existing alias dictionary."""
    canonical = get_canonical_skill(value)
    if canonical not in get_all_canonical_skills():
        raise ValueError(f"Unknown canonical skill reference: {value}")
    return canonical


def canonical_skill_references(values: Iterable[str]) -> List[str]:
    result = {canonical_skill_reference(value) for value in values if str(value).strip()}
    return sorted(result)


def _role_slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def canonical_role_reference(value: str) -> str:
    """Resolve a role title or slug using ROLE_DEFINITIONS, without duplicating it."""
    normalized = normalize_text(value).lower()
    for title in ROLE_DEFINITIONS:
        if normalized == title.lower() or normalized == _role_slug(title):
            return title
    raise ValueError(f"Unknown canonical role reference: {value}")


def canonical_role_references(values: Iterable[str]) -> List[str]:
    result = {canonical_role_reference(value) for value in values if str(value).strip()}
    return sorted(result)


def normalized_content_key(content: str) -> str:
    return normalize_text(content).casefold()


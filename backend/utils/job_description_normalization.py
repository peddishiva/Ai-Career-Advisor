"""
Normalization helpers for deterministic job description parsing.
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple


def strip_list_prefix(line: str) -> str:
    """Remove common markdown, bullet, checkbox, and numbered-list prefixes."""
    if not line:
        return ""
    cleaned = line.strip()
    cleaned = re.sub(r"^\s*(?:[-*+]|\u2022|\u25e6|\u25aa|\u25ab)\s+", "", cleaned)
    cleaned = re.sub(r"^\s*\[[ xX]\]\s+", "", cleaned)
    cleaned = re.sub(r"^\s*(?:\d+|[a-zA-Z])[\.)]\s+", "", cleaned)
    return cleaned.strip()


def clean_jd_item(line: str) -> str:
    """Normalize a JD item while preserving the source wording."""
    cleaned = strip_list_prefix(line)
    cleaned = cleaned.strip(" #*_`>")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def heading_key(text: str) -> str:
    """Normalize heading text for robust alias matching."""
    cleaned = text.lower().replace("&", " and ")
    cleaned = re.sub(r"['`]", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9+#/.]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def canonical_jd_section(
    line: str,
    section_aliases: Dict[str, Iterable[str]],
) -> Tuple[Optional[str], str]:
    """
    Return the canonical JD section and inline content for a section header line.

    Ordinary sentences are not treated as headers: an alias must be the whole
    cleaned line, or be followed by a clear ':' or spaced '-' delimiter.
    """
    if not line:
        return None, ""

    cleaned = strip_list_prefix(line).strip()
    cleaned = cleaned.strip(" #*_`>")
    if not cleaned:
        return None, ""

    candidates: List[Tuple[str, str]] = [(cleaned, "")]

    colon_match = re.match(r"^(?P<header>[^:]{1,80})\s*:\s*(?P<inline>.*)$", cleaned)
    if colon_match:
        candidates.insert(0, (colon_match.group("header").strip(), colon_match.group("inline").strip()))

    dash_match = re.match(r"^(?P<header>.{1,80}?)\s+-\s+(?P<inline>.+)$", cleaned)
    if dash_match:
        candidates.insert(0, (dash_match.group("header").strip(), dash_match.group("inline").strip()))

    alias_keys = {
        section: {heading_key(alias) for alias in aliases}
        for section, aliases in section_aliases.items()
    }
    for header, inline in candidates:
        key = heading_key(header)
        for section, keys in alias_keys.items():
            if key in keys:
                return section, inline

    return None, ""


def dedupe_preserve_order(items: Iterable, key=None) -> List:
    """Deduplicate values without changing first-seen order."""
    seen = set()
    deduped = []
    for item in items:
        marker = key(item) if key else item
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(item)
    return deduped


def requirement_key(text: str) -> str:
    """Canonical key for deduplicating requirement evidence."""
    return re.sub(r"[^a-z0-9+#/.]+", " ", text.lower()).strip()

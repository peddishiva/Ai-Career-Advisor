"""
Deterministic job description parser for Phase 2A.
"""

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config.job_description_config import (
    CERTIFICATION_KEYWORDS,
    DEGREE_FIELD_KEYWORDS,
    EMPLOYMENT_TYPES,
    ELIGIBILITY_CONTEXT_MARKERS,
    ELIGIBILITY_STATUS_PATTERNS,
    JOB_SECTION_ALIASES,
    JOB_TITLE_TERMS,
    NON_REQUIREMENT_SECTION_NAMES,
    PARSING_LIMITS,
    PREFERRED_LANGUAGE,
    PREFERRED_SECTION_NAMES,
    REQUIRED_LANGUAGE,
    REQUIRED_SECTION_NAMES,
)
from services.parser_service import ResumeParser
from utils.job_description_normalization import (
    canonical_jd_section,
    clean_jd_item,
    dedupe_preserve_order,
    heading_key,
    requirement_key,
)
from utils.normalization import extract_matched_skills


class JobDescriptionParser:
    """Parse validated job descriptions into a stable JSON-serializable model."""

    def __init__(self):
        self.file_text_extractor = ResumeParser()
        self.job_title_pattern = re.compile(
            rf"\b(?:entry[-\s]?level|junior|senior|staff|principal|lead)?\s*"
            rf"(?:software|backend|front[-\s]?end|full[-\s]?stack|data|business\s+intelligence|"
            rf"machine\s+learning|ml|ai|devops|cloud|site\s+reliability|platform|security|qa|test|systems|analytics)?\s*"
            rf"(?:{'|'.join(JOB_TITLE_TERMS)})\b",
            re.I,
        )
        self.experience_pattern = re.compile(
            r"\b(?P<years>\d+)\s*(?:\+|-\s*\d+|to\s+\d+)?\s*(?:years?|yrs?)\b"
            r"(?P<tail>[^.\n;]*)",
            re.I,
        )
        self.degree_pattern = re.compile(
            r"\b(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?|doctorate|"
            r"b\.?\s?tech|m\.?\s?tech|b\.?\s?s|m\.?\s?s|mba|associate(?:'s)?|degree)(?=\W|$)",
            re.I,
        )
        self.certification_pattern = re.compile("|".join(re.escape(keyword) for keyword in CERTIFICATION_KEYWORDS), re.I)

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Extract text from a supported file and parse it as a job description."""
        text = self.extract_text(file_path)
        return self.parse_text(text)

    def extract_text(self, file_path: str) -> str:
        """
        Extract text using existing PDF/DOCX project dependencies.

        Legacy binary .doc remains best-effort because the project currently
        routes it through the same extractor used elsewhere.
        """
        return self.file_text_extractor.extract_text(str(Path(file_path)))

    def parse_text(self, text: str) -> Dict[str, Any]:
        """Parse already-extracted JD text into deterministic structured fields."""
        sections = self._segment_sections(text)
        required_qualifications, preferred_qualifications = self._extract_qualifications(sections)
        required_eligibility_requirements = [
            item for item in required_qualifications if item["category"] == "eligibility"
        ]
        preferred_eligibility_requirements = [
            item for item in preferred_qualifications if item["category"] == "eligibility"
        ]
        required_availability_requirements = [
            self._availability_item(item)
            for item in required_qualifications
            if self._is_availability_requirement(item["text"])
        ]
        preferred_availability_requirements = [
            self._availability_item(item)
            for item in preferred_qualifications
            if self._is_availability_requirement(item["text"])
        ]
        required_capability_requirements = [
            item for item in required_qualifications if item["category"] in {"domain_knowledge", "capability"}
        ]
        preferred_capability_requirements = [
            item for item in preferred_qualifications if item["category"] in {"domain_knowledge", "capability"}
        ]

        return {
            "job_title": self._extract_job_title(text, sections),
            "company": self._extract_company(text),
            "location": self._extract_location(text),
            "employment_type": self._extract_employment_type(text),
            "required_skills": self._extract_skills(sections, required=True),
            "preferred_skills": self._extract_skills(sections, required=False),
            "required_qualifications": required_qualifications,
            "preferred_qualifications": preferred_qualifications,
            "required_eligibility_requirements": required_eligibility_requirements,
            "preferred_eligibility_requirements": preferred_eligibility_requirements,
            "required_availability_requirements": required_availability_requirements,
            "preferred_availability_requirements": preferred_availability_requirements,
            "required_capability_requirements": required_capability_requirements,
            "preferred_capability_requirements": preferred_capability_requirements,
            "experience_requirements": self._extract_experience_requirements(sections),
            "education_requirements": self._extract_education_requirements(sections),
            "certifications": self._extract_certifications(sections),
            "responsibilities": self._extract_responsibilities(sections),
            "sections": sections,
            "raw_text": text,
        }

    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Segment raw JD text into canonical sections."""
        sections: Dict[str, List[str]] = {"header": []}
        current_section = "header"

        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue

            section, inline_content = canonical_jd_section(stripped, JOB_SECTION_ALIASES)
            if section:
                current_section = section
                sections.setdefault(current_section, [])
                if inline_content:
                    sections[current_section].append(clean_jd_item(inline_content))
                continue

            sections.setdefault(current_section, []).append(stripped)

        return {
            section: "\n".join(lines[: PARSING_LIMITS["max_section_lines"]]).strip()
            for section, lines in sections.items()
            if "\n".join(lines).strip()
        }

    def _extract_job_title(self, text: str, sections: Dict[str, str]) -> Optional[str]:
        lines = self._all_lines(text)
        for line in lines[:10]:
            cleaned = clean_jd_item(line)
            explicit = re.match(r"^(?:job\s+title|position|role)\s*[:\-]\s*(?P<title>.+)$", cleaned, re.I)
            if not explicit:
                continue
            title = self._clean_metadata_value(explicit.group("title"))
            if self._is_title_candidate(title):
                return title

        header_lines = self._all_lines(sections.get("header", ""))
        for line in header_lines[:6]:
            cleaned = clean_jd_item(line)
            if self._is_title_candidate(cleaned):
                return cleaned

        for line in lines[:8]:
            cleaned = clean_jd_item(line)
            if self._is_title_candidate(cleaned):
                return cleaned
        return None

    def _extract_company(self, text: str) -> Optional[str]:
        for line in self._all_lines(text)[:12]:
            cleaned = clean_jd_item(line)
            match = re.match(r"^(?:company|employer|organization|about)\s*[:\-]\s*(?P<value>.+)$", cleaned, re.I)
            if match:
                return self._clean_metadata_value(match.group("value"))
        return None

    def _extract_location(self, text: str) -> Optional[str]:
        for line in self._all_lines(text)[:12]:
            cleaned = clean_jd_item(line)
            match = re.match(r"^(?:location|work\s+location)\s*[:\-]\s*(?P<value>.+)$", cleaned, re.I)
            if match:
                return self._clean_metadata_value(match.group("value"))
        return None

    def _extract_employment_type(self, text: str) -> Optional[str]:
        type_keys = {heading_key(value): value for value in EMPLOYMENT_TYPES}
        for line in self._all_lines(text)[:15]:
            cleaned = clean_jd_item(line)
            match = re.match(r"^(?:job\s+type|employment\s+type|type)\s*[:\-]\s*(?P<value>.+)$", cleaned, re.I)
            value = self._clean_metadata_value(match.group("value")) if match else cleaned
            key = heading_key(value)
            if key in type_keys:
                return self._format_employment_type(type_keys[key])
        return None

    def _extract_responsibilities(self, sections: Dict[str, str]) -> List[str]:
        responsibilities = []
        for _, line in self._iter_section_lines(sections, ["responsibilities"]):
            if self._is_noise_line(line) or self._is_requirement_line(line):
                continue
            responsibilities.extend(self._responsibility_units(line))
        for section, line in self._iter_all_section_lines(sections):
            if section == "responsibilities" or self._is_noise_line(line):
                continue
            if self._has_responsibility_language(line) and self._requirement_type(section, line) is None:
                responsibilities.extend(self._responsibility_units(line))
        return dedupe_preserve_order(responsibilities, key=requirement_key)[: PARSING_LIMITS["max_responsibilities"]]

    def _extract_qualifications(self, sections: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        required_items: List[Dict[str, Any]] = []
        preferred_items: List[Dict[str, Any]] = []

        for section, line in self._iter_all_section_lines(sections):
            if self._is_noise_line(line):
                continue

            requirement_type = self._requirement_type(section, line)
            if requirement_type in {"required", "preferred"}:
                for fragment in self._qualification_fragments(line):
                    if self._is_exclusion_fragment(fragment):
                        continue
                    item = self._qualification_item(fragment, section, requirement_type)
                    if requirement_type == "preferred":
                        preferred_items.append(item)
                    else:
                        required_items.append(item)

        for section, line in self._iter_section_lines(
            sections,
            ["overview", "responsibilities", "job_details", "header"],
        ):
            for fragment in self._qualification_fragments(line):
                if self._is_exclusion_fragment(fragment) or self._is_promotional_line(fragment) or not self._has_explicit_eligibility_language(fragment):
                    continue
                requirement_type = self._requirement_type(section, fragment)
                if requirement_type is None:
                    requirement_type = "preferred" if re.search(r"\b(?:preferred|preferably)\b", fragment, re.I) else "required"
                item = self._qualification_item(fragment, section, requirement_type)
                if requirement_type == "preferred":
                    preferred_items.append(item)
                else:
                    required_items.append(item)

        required_items = dedupe_preserve_order(required_items, key=lambda item: requirement_key(item["text"]))
        preferred_items = dedupe_preserve_order(preferred_items, key=lambda item: requirement_key(item["text"]))
        return (
            required_items[: PARSING_LIMITS["max_qualifications"]],
            preferred_items[: PARSING_LIMITS["max_qualifications"]],
        )

    def _extract_skills(self, sections: Dict[str, str], required: bool) -> List[str]:
        skills: List[str] = []
        for section, line in self._iter_all_section_lines(sections):
            if self._is_education_requirement(line) or self.certification_pattern.search(line):
                continue
            requirement_type = self._requirement_type(section, line)
            if required and requirement_type != "required":
                continue
            if not required and requirement_type != "preferred":
                continue
            skills.extend(extract_matched_skills(line).keys())
        return dedupe_preserve_order(skills)

    def _extract_experience_requirements(self, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        requirements: List[Dict[str, Any]] = []
        for section, line in self._iter_all_section_lines(sections):
            if self._is_noise_line(line):
                continue
            requirement_type = self._requirement_type(section, line)
            if requirement_type is None and "experience" not in line.lower():
                continue
            if "experience" not in line.lower() and not self.experience_pattern.search(line):
                continue

            match = self.experience_pattern.search(line)
            years = int(match.group("years")) if match else None
            domain = self._extract_experience_domain(line, match.group("tail") if match else "")
            requirements.append(
                {
                    "text": line,
                    "years": years,
                    "domain": domain,
                    "source_section": section,
                    "requirement_type": requirement_type or "required",
                }
            )

        requirements = dedupe_preserve_order(requirements, key=lambda item: requirement_key(item["text"]))
        return requirements[: PARSING_LIMITS["max_experience_requirements"]]

    def _extract_education_requirements(self, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        requirements: List[Dict[str, Any]] = []
        for section, line in self._iter_all_section_lines(sections):
            if self._is_noise_line(line) or not self._is_education_requirement(line):
                continue
            requirement_type = self._requirement_type(section, line) or "required"
            requirements.append(
                {
                    "degree_level": self._degree_levels(line),
                    "fields": self._degree_fields(line),
                    "related_field_allowed": bool(re.search(r"\brelated\s+field\b|\bequivalent\s+experience\b", line, re.I)),
                    "raw_text": line,
                    "source_section": section,
                    "requirement_type": requirement_type,
                }
            )

        requirements = dedupe_preserve_order(requirements, key=lambda item: requirement_key(item["raw_text"]))
        return requirements[: PARSING_LIMITS["max_education_requirements"]]

    def _extract_certifications(self, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        certifications: List[Dict[str, Any]] = []
        for section, line in self._iter_all_section_lines(sections):
            if self._is_noise_line(line):
                continue
            if self._requirement_category(line) == "eligibility":
                continue
            if section != "certifications" and not self.certification_pattern.search(line):
                continue
            requirement_type = self._requirement_type(section, line) or "required"
            certifications.append(
                {
                    "name": self._clean_certification_name(line),
                    "required": requirement_type == "required",
                    "raw_text": line,
                    "source_section": section,
                }
            )

        certifications = dedupe_preserve_order(certifications, key=lambda item: requirement_key(item["name"]))
        return certifications[: PARSING_LIMITS["max_certifications"]]

    def _requirement_type(self, section: str, line: str) -> Optional[str]:
        if section in PREFERRED_SECTION_NAMES or self._has_language(line, PREFERRED_LANGUAGE):
            return "preferred"
        if section in REQUIRED_SECTION_NAMES or self._has_language(line, REQUIRED_LANGUAGE):
            return "required"
        if section == "header" and self._has_language(line, REQUIRED_LANGUAGE):
            return "required"
        return None

    def _qualification_item(self, line: str, section: str, requirement_type: str) -> Dict[str, Any]:
        return {
            "text": line,
            "source_section": section,
            "requirement_type": requirement_type,
            "category": self._requirement_category(line),
        }

    def _requirement_category(self, line: str) -> str:
        """Classify explicit qualification evidence without treating soft text as eligibility."""
        if self._is_education_requirement(line):
            return "education"
        if self._has_explicit_eligibility_language(line):
            return "eligibility"
        if self._is_availability_requirement(line):
            return "availability"
        if self._is_domain_knowledge_requirement(line):
            return "domain_knowledge"
        if self.certification_pattern.search(line):
            return "certification"
        return "general"

    def _has_explicit_eligibility_language(self, line: str) -> bool:
        lowered = line.lower()
        if not any(marker in lowered for marker in ELIGIBILITY_CONTEXT_MARKERS):
            return False
        if any(re.search(pattern, line, re.I) for pattern in ELIGIBILITY_STATUS_PATTERNS):
            return True
        return bool(
            re.search(
                r"\b(?:pursu\w*|clear\w*|eligible|registered|licensed|active|only)\b"
                r".{0,80}\b(?:ca|ipcc|articleship|industrial\s+training|professional\s+qualification|"
                r"professional\s+body|license|membership|member|trainee)\b",
                line,
                re.I,
            )
        )

    def _is_education_requirement(self, line: str) -> bool:
        if not self.degree_pattern.search(line):
            return False
        # Common office-product phrases use degree-like abbreviations but are skills.
        return not bool(re.search(r"\b(?:ms|m\.s\.?)\s+(?:excel|word|office|powerpoint|access)\b", line, re.I))

    def _is_availability_requirement(self, line: str) -> bool:
        return bool(
            re.search(
                r"\b(?:available|availability|commit(?:ted|ment)?|intern|training)\b"
                r".{0,100}\b\d+\s*(?:-|–|to)\s*\d+\s*(?:months?|years?)\b",
                line,
                re.I,
            )
            or re.search(
                r"\b\d+\s*(?:-|–|to)\s*\d+\s*(?:months?|years?)\b"
                r".{0,100}\b(?:available|availability|intern|training|articleship)\b",
                line,
                re.I,
            )
        )

    def _is_domain_knowledge_requirement(self, line: str) -> bool:
        return bool(
            re.search(r"\b(?:knowledge|understanding|familiarity|background)\b", line, re.I)
            and re.search(r"\b(?:accounting|finance|financial|audit|tax|banking)\b", line, re.I)
        )

    def _qualification_fragments(self, line: str) -> List[str]:
        fragments = re.split(r"(?<=[.!?])\s+|;\s*", line.strip())
        result: List[str] = []
        for fragment in fragments:
            fragment = fragment.strip()
            if not fragment:
                continue
            parts = re.split(
                r",\s+(?=(?:cleared|pursuing|available|possess|good|strong|attention|proficiency|"
                r"eligible|registered|licensed|active|must\b))",
                fragment,
                flags=re.I,
            )
            result.extend(part.strip() for part in parts if part.strip())
        return result or [line]

    def _is_exclusion_fragment(self, line: str) -> bool:
        return bool(re.search(r"\b(?:non[-\s]|should not apply|have not yet|already completed)\b", line, re.I))

    def _availability_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        availability_item = dict(item)
        availability_item["category"] = "availability"
        return availability_item

    def _is_requirement_line(self, line: str) -> bool:
        return (
            self._requirement_type("responsibilities", line) is not None
            or self._requirement_category(line) in {"education", "eligibility", "availability", "domain_knowledge", "certification"}
        )

    def _responsibility_units(self, line: str) -> List[str]:
        cleaned_line = re.sub(r"\([^)]*\)", "", line)
        units = re.split(r"(?<=[.!?])\s+|;\s*", cleaned_line)
        return [
            unit.strip()
            for unit in units
            if unit.strip() and not self._is_promotional_line(unit)
        ]

    def _is_promotional_line(self, line: str) -> bool:
        return bool(
            re.search(
                r"\b(?:are you looking for|kick[- ]start|exciting and fast[- ]growing|"
                r"one of the largest|if your answer|we(?:'|’)re hiring|we are hiring|"
                r"are you\b|us-based multinational|headquartered|vision to build|started as an online)\b",
                line,
                re.I,
            )
        )

    def _iter_all_section_lines(self, sections: Dict[str, str]) -> Iterable[Tuple[str, str]]:
        for section, text in sections.items():
            if section in NON_REQUIREMENT_SECTION_NAMES and section != "responsibilities":
                continue
            for _, line in self._iter_section_lines(sections, [section]):
                yield section, line

    def _iter_section_lines(self, sections: Dict[str, str], names: Iterable[str]) -> Iterable[Tuple[str, str]]:
        for name in names:
            for raw_line in sections.get(name, "").splitlines():
                line = clean_jd_item(raw_line)
                if line:
                    yield name, line

    def _extract_experience_domain(self, line: str, tail: str) -> Optional[str]:
        source = tail or line
        source = re.sub(r"^(?:\s+of)?\s*(?:professional|hands-on|relevant)?\s*", "", source, flags=re.I)
        source = re.sub(r"^experience\s*(?:in|with|building|using|as)?\s*", "", source, flags=re.I)
        source = re.sub(r"^(?:in|with|building|using|as)\s+", "", source, flags=re.I)
        source = re.split(r"\bexperience\b", source, maxsplit=1, flags=re.I)[0] or source
        domain = re.split(r",|\band\b|\bor\b", source, maxsplit=1)[0].strip(" .:-")
        return domain or None

    def _degree_levels(self, line: str) -> List[str]:
        levels = []
        checks = [
            ("associate", r"\bassociate"),
            ("bachelor", r"\bbachelor|b\.?\s?s\.?|b\.?\s?tech"),
            ("master", r"\bmaster|m\.?\s?s\.?|m\.?\s?tech|mba"),
            ("phd", r"\bph\.?d\.?|\bdoctorate"),
            ("degree", r"\bdegree\b"),
        ]
        for label, pattern in checks:
            if re.search(pattern, line, re.I):
                levels.append(label)
        if "degree" in levels and len(levels) > 1:
            levels.remove("degree")
        return levels

    def _degree_fields(self, line: str) -> List[str]:
        fields = []
        line_lower = line.lower()
        for field in DEGREE_FIELD_KEYWORDS:
            if field in line_lower:
                fields.append(field.title())
        return dedupe_preserve_order(fields)

    def _clean_certification_name(self, line: str) -> str:
        cleaned = clean_jd_item(line)
        cleaned = re.sub(r"\b(?:is\s+)?(?:required|preferred|nice to have|a plus|would be a plus)\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip(" .:-")

    def _clean_metadata_value(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" .:-")

    def _format_employment_type(self, value: str) -> str:
        normalized = value.lower().replace(" ", "-")
        mapping = {
            "full-time": "Full-time",
            "part-time": "Part-time",
            "contract": "Contract",
            "contractor": "Contract",
            "internship": "Internship",
            "temporary": "Temporary",
            "remote": "Remote",
            "hybrid": "Hybrid",
            "on-site": "On-site",
            "onsite": "On-site",
        }
        return mapping.get(normalized, value.title())

    def _is_title_candidate(self, value: str) -> bool:
        if not value or len(value) > 100:
            return False
        if value.endswith((".", ";", ",")):
            return False
        if canonical_jd_section(value, JOB_SECTION_ALIASES)[0]:
            return False
        return bool(self.job_title_pattern.search(value))

    def _is_noise_line(self, line: str) -> bool:
        if not line:
            return True
        return bool(canonical_jd_section(line, JOB_SECTION_ALIASES)[0])

    def _has_language(self, line: str, phrases: Tuple[str, ...]) -> bool:
        line_lower = line.lower()
        return any(re.search(rf"\b{re.escape(phrase.lower())}\b", line_lower) for phrase in phrases)

    def _has_responsibility_language(self, line: str) -> bool:
        return bool(re.search(r"\b(?:you will|responsible for|build|design|develop|implement|analyze|manage|collaborate|own)\b", line, re.I))

    def _all_lines(self, text: str) -> List[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

"""
Resume Parser Service
Extracts structured sections, evidence, skills, experience, education, and projects from PDF/DOCX resumes.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import pdfplumber
from docx import Document

from utils.normalization import extract_matched_skills, normalize_resume_section_heading


class ResumeParser:
    """Parse resumes and extract structured, evidence-backed information"""
    
    def __init__(self):
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        # Section Header Patterns
        self.section_headers = {
            'skills': r'(?:technical\s+skills|skills\s*&?\s*tools|core\s+competencies|technologies|tech\s+stack|skills)',
            'experience': r'(?:work\s+experience|professional\s+experience|employment\s+history|experience|work\s+history|selected\s+work)',
            'projects': r'(?:technical\s+projects|academic\s+projects|personal\s+projects|selected\s+projects|projects|key\s+projects)',
            'education': r'(?:education|academic\s+background|academics|qualifications|academic\s+history)',
            'certifications': r'(?:certifications\s*&?\s*achievements|certifications|licenses\s*&?\s*certifications|certificates|courses|achievements)'
        }
        
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse resume file and extract rich structured information."""
        text = self.extract_text(file_path)
        return self.parse_text(text)
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from a supported resume file without parsing it."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if file_path.suffix.lower() == '.pdf':
            text = self._extract_pdf_text(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            text = self._extract_docx_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
        return text
        
    def parse_text(self, text: str) -> Dict[str, Any]:
        """Parse already-extracted resume text into structured information."""
        # Extract structured information
        parsed_data = self._extract_information(text)
        parsed_data['raw_text'] = text
        
        return parsed_data
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract clean text from PDF file."""
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract clean text from DOCX file."""
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Segment raw resume text into named sections."""
        lines = text.split('\n')
        sections: Dict[str, List[str]] = {
            'header': [],
            'skills': [],
            'experience': [],
            'projects': [],
            'education': [],
            'certifications': [],
            'other': []
        }
        
        current_section = 'header'
        
        # Compile patterns for section recognition.
        header_patterns = []
        for sec_name, pattern in self.section_headers.items():
            regex = re.compile(
                rf'^\s*[#*_>`\-\s]*(?:\d+[\.)]\s*)?({pattern})\s*(?:[:\-]\s*(.*))?$',
                re.IGNORECASE
            )
            header_patterns.append((sec_name, regex))
            
        for line in lines:
            stripped = line.strip()
            if not stripped:
                sections[current_section].append("")
                continue
                
            # Check if this line is a section header
            matched_header = None
            inline_content = ""
            normalized_header = normalize_resume_section_heading(stripped)
            for sec_name, regex in header_patterns:
                match = regex.match(normalized_header)
                if match:
                    matched_header = sec_name
                    inline_content = (match.group(2) or "").strip(" *#_`>")
                    break
                    
            if matched_header:
                current_section = matched_header
                if inline_content:
                    sections[current_section].append(inline_content)
                continue
                
            sections[current_section].append(stripped)
            
        return {sec: "\n".join(content_lines) for sec, content_lines in sections.items()}
    
    def _extract_information(self, text: str) -> Dict[str, Any]:
        """Extract structured entities, sections, and evidence from resume text."""
        sections = self._segment_sections(text)
        
        # Extract contact information
        emails = re.findall(self.email_pattern, text)
        phones = re.findall(self.phone_pattern, text)
        
        # Extract candidate name
        header_text = sections.get('header', '')
        lines = [line.strip() for line in (header_text or text).split('\n') if line.strip()]
        name = self._extract_name(lines)
        
        # Section-specific skill extraction
        skills_in_skills_sec = extract_matched_skills(sections.get('skills', ''))
        skills_in_exp_sec = extract_matched_skills(sections.get('experience', ''))
        skills_in_proj_sec = extract_matched_skills(sections.get('projects', ''))
        skills_in_all = extract_matched_skills(self._skill_frequency_text(sections))
        
        # Consolidate all canonical skills
        all_skills_list = sorted(list(skills_in_all.keys()))
        
        # Extract detailed subsections
        experience = self._extract_experience(sections.get('experience', ''))
        education = self._extract_education(sections.get('education', ''))
        projects = self._extract_projects(sections.get('projects', ''))
        certifications = self._extract_certifications(sections.get('certifications', ''))
        
        # Build Section Evidence Map for Scoring Engine
        section_evidence = {
            'skills_section': list(skills_in_skills_sec.keys()),
            'experience_skills': list(skills_in_exp_sec.keys()),
            'project_skills': list(skills_in_proj_sec.keys()),
            'all_skill_frequencies': skills_in_all,
            'sections_detected': [k for k, v in sections.items() if v.strip()]
        }
        
        return {
            'name': name,
            'email': emails[0] if emails else None,
            'phone': phones[0] if phones else None,
            'skills': all_skills_list,
            'experience': experience,
            'education': education,
            'projects': projects,
            'certifications': certifications,
            'section_evidence': section_evidence,
            'sections': {
                'skills_text': sections.get('skills', ''),
                'experience_text': sections.get('experience', ''),
                'projects_text': sections.get('projects', ''),
                'education_text': sections.get('education', ''),
                'certifications_text': sections.get('certifications', '')
            }
        }
    
    def _extract_name(self, lines: List[str]) -> str:
        """Extract candidate name with robust filtering."""
        for line in lines[:6]:
            clean_line = line.strip()
            # Skip invalid lines
            if len(clean_line) < 3 or len(clean_line) > 40:
                continue
            if re.search(r'(@|www|\.com|http|\+|resume|curriculum|phone|email|address|profile|objective)', clean_line, re.IGNORECASE):
                continue
            # Must look like a name
            words = clean_line.split()
            if 1 <= len(words) <= 4 and all(w[0].isalpha() for w in words):
                # Ensure it's not all lowercase or all numbers
                if any(w[0].isupper() for w in words):
                    return clean_line
        return "Candidate"
        
    def _skill_frequency_text(self, sections: Dict[str, str]) -> str:
        """Use career-evidence sections for global skill frequency without header artifacts."""
        return "\n".join(
            sections.get(section, '')
            for section in ['skills', 'experience', 'projects', 'education']
            if sections.get(section, '').strip()
        )
        
    def _is_bullet_line(self, line: str) -> bool:
        """Return whether a line is a bullet/list item rather than an entry header."""
        return bool(re.match(r'^\s*(?:[-*•‣▪▫◦]|\d+[\.)])\s+', line))
        
    def _strip_list_prefix(self, line: str) -> str:
        """Remove common bullet/number prefixes and decorative wrappers from a resume line."""
        cleaned = re.sub(r'^\s*(?:[-*•‣▪▫◦]|\d+[\.)])\s*', '', line).strip()
        cleaned = cleaned.strip(" -*•‣▪▫◦\t")
        return cleaned
        
    def _clean_entry_text(self, lines: List[str]) -> str:
        """Normalize a block of resume entry lines while preserving line-level evidence."""
        return "\n".join(line.strip() for line in lines if line.strip()).strip()
        
    def _has_date_signal(self, line: str) -> bool:
        """Detect common resume date/year signals on entry header lines."""
        return bool(re.search(r'\b(?:19|20)\d{2}\b|\bpresent\b|\bcurrent\b', line, re.IGNORECASE))
        
    def _starts_with_action_verb(self, line: str) -> bool:
        """Detect bullet-like achievement lines whose bullet marker may be missing."""
        return bool(re.match(
            r'^\s*(?:led|built|developed|implemented|managed|created|designed|'
            r'improved|optimized|automated|analyzed)\b',
            line,
            re.IGNORECASE
        ))
        
    def _looks_like_experience_header(self, line: str) -> bool:
        """Detect role boundary lines without splitting continuation or bullet lines."""
        stripped = line.strip()
        if not stripped or self._is_bullet_line(stripped) or len(stripped) > 180:
            return False
        if stripped.endswith(('.', ',', ';', ':')):
            return False
            
        has_date = self._has_date_signal(stripped)
        role_terms = re.compile(
            r'\b(?:intern|engineer|developer|analyst|scientist|consultant|manager|lead|'
            r'associate|specialist|administrator|architect|designer|sdet|devops|qa|'
            r'tester|researcher|coordinator)\b',
            re.IGNORECASE
        )
        strong_company_separator = re.search(r'\s(?:at|with)\s|\s[-–—|]\s', stripped, re.IGNORECASE)
        if self._starts_with_action_verb(stripped) and not has_date:
            early_words = " ".join(stripped.split()[:4])
            has_early_role = bool(role_terms.search(early_words))
            if not (has_early_role and strong_company_separator):
                return False
            
        employer_separator = re.search(r'\s(?:at|with|for)\s|\s[-–—|]\s', stripped, re.IGNORECASE)
        return bool(role_terms.search(stripped) and (has_date or employer_separator))
        
    def _split_blocks_on_headers(self, text: str, header_detector) -> List[List[str]]:
        """Split a section into entry blocks using non-bullet header lines as boundaries."""
        lines = [line.strip() for line in text.splitlines()]
        blocks: List[List[str]] = []
        current: List[str] = []
        
        for line in lines:
            if not line:
                if current:
                    current.append("")
                continue
                
            if header_detector(line) and current:
                blocks.append(current)
                current = [line]
            else:
                current.append(line)
                
        if current:
            blocks.append(current)
            
        return [block for block in blocks if self._clean_entry_text(block)]
        
    def _parse_experience_header(self, header: str) -> Dict[str, str]:
        """Extract title/company/date from a common resume experience header."""
        parsed = {"title": "", "company": "", "date": ""}
        date_match = re.search(
            r'\(?\b((?:19|20)\d{2}\s*(?:[-–—]|to)\s*(?:present|current|(?:19|20)\d{2})|(?:19|20)\d{2})\b\)?',
            header,
            re.IGNORECASE
        )
        header_without_date = header
        if date_match:
            parsed["date"] = date_match.group(1).strip()
            header_without_date = (header[:date_match.start()] + header[date_match.end():]).strip(" -–—|()")
            
        at_match = re.match(r'^(?P<title>.+?)\s+(?:at|with|for)\s+(?P<company>.+)$', header_without_date, re.IGNORECASE)
        if at_match:
            parsed["title"] = at_match.group("title").strip(" -–—|")
            parsed["company"] = at_match.group("company").strip(" -–—|")
            return parsed
            
        parts = [part.strip() for part in re.split(r'\s+(?:[-–—|])\s+', header_without_date) if part.strip()]
        if parts:
            parsed["title"] = parts[0]
            if len(parts) >= 2:
                parsed["company"] = parts[-1]
                
        if not parsed["title"]:
            parsed["title"] = header_without_date.strip()
            
        return parsed
    
    def _extract_experience(self, exp_text: str) -> List[Dict[str, Any]]:
        """Extract structured work experience entries."""
        experience = []
        target_text = exp_text.strip()
        
        if not target_text:
            return []
            
        blocks = self._split_blocks_on_headers(target_text, self._looks_like_experience_header)
        for block in blocks:
            cleaned = self._clean_entry_text(block)
            if len(cleaned) < 20:
                continue
            entry_skills = list(extract_matched_skills(cleaned).keys())
            header = next((line.strip() for line in block if line.strip()), "")
            header_data = self._parse_experience_header(header)
            experience.append({
                'title': header_data.get('title', ''),
                'company': header_data.get('company', ''),
                'date': header_data.get('date', ''),
                'description': cleaned[:500],
                'skills_applied': entry_skills
            })
            
        return experience[:6]
    
    def _extract_education(self, edu_text: str) -> List[Dict[str, Any]]:
        """Extract education credentials."""
        education = []
        target_text = edu_text.strip()
        
        if not target_text:
            return []
        
        degree_pattern = re.compile(
            r'(?<![A-Za-z])(?P<degree>'
            r'b\.?\s?tech|btech|b\.?\s?e\.?|b\.?\s?s\.?|b\.?\s?a\.?|'
            r'm\.?\s?tech|mtech|m\.?\s?s\.?|m\.?\s?a\.?|m\.?\s?b\.?\s?a\.?|'
            r'bachelor(?:\'s)?(?:\s+of\s+(?:science|technology|engineering|arts))?|'
            r'master(?:\'s)?(?:\s+of\s+(?:science|technology|engineering|arts|business\s+administration))?|'
            r'ph\.?d\.?|doctorate|doctor\s+of\s+philosophy|associate(?:\'s)?\s+degree'
            r')(?![A-Za-z])',
            re.IGNORECASE
        )
        
        for raw_line in target_text.splitlines():
            line = self._strip_list_prefix(raw_line)
            if not line or re.match(r'^(?:cgpa|gpa|percentage|grade|score)\b', line, re.IGNORECASE):
                continue
            match = degree_pattern.search(line)
            if not match:
                continue
                
            degree = re.sub(r'\s+', ' ', match.group('degree')).strip()
            field_source = line[match.end():].strip(" ,:-–—|")
            field_source = re.sub(r'^(?:of|in)\s+', '', field_source, flags=re.IGNORECASE).strip()
            field = re.split(r'\s[-–—|]\s|\b(?:19|20)\d{2}\b', field_source, maxsplit=1)[0].strip(" ,:-–—|")
            education.append({
                'degree': degree[:100],
                'field': field[:80]
            })
                
        return education[:3]
        
    def _looks_like_project_header(self, line: str, next_line: str = "") -> bool:
        """Detect project title boundary lines without splitting wrapped bullet text."""
        stripped = line.strip()
        if not stripped or self._is_bullet_line(stripped) or len(stripped) > 140:
            return False
        if stripped.endswith(('.', ',', ';')):
            return False
        if re.match(r'^(?:built|developed|designed|engineered|implemented|integrated|automated|processed|trained|created)\b', stripped, re.IGNORECASE):
            return False
            
        word_count = len(stripped.split())
        has_title_signal = bool(re.search(
            r'\b(?:project|dashboard|portal|app|application|platform|system|tool|bot|assistant|'
            r'auditor|advisor|detector|classifier|analyzer|github|link)\b',
            stripped,
            re.IGNORECASE
        ))
        next_is_bullet = bool(next_line and self._is_bullet_line(next_line))
        starts_like_title = stripped[0].isupper() or stripped[0].isdigit()
        return word_count <= 12 and starts_like_title and (has_title_signal or next_is_bullet)
        
    def _split_project_blocks(self, text: str) -> List[List[str]]:
        """Split project section into title-led project blocks."""
        lines = [line.strip() for line in text.splitlines()]
        blocks: List[List[str]] = []
        current: List[str] = []
        
        for index, line in enumerate(lines):
            if not line:
                if current:
                    current.append("")
                continue
                
            next_line = ""
            for future_line in lines[index + 1:]:
                if future_line.strip():
                    next_line = future_line.strip()
                    break
                    
            if self._looks_like_project_header(line, next_line) and current:
                blocks.append(current)
                current = [line]
            else:
                current.append(line)
                
        if current:
            blocks.append(current)
            
        return [block for block in blocks if self._clean_entry_text(block)]
    
    def _extract_projects(self, proj_text: str) -> List[Dict[str, Any]]:
        """Extract project entries with detected technologies."""
        projects = []
        target_text = proj_text.strip()
        
        if not target_text:
            return []
            
        blocks = self._split_project_blocks(target_text)
        for block in blocks:
            cleaned = self._clean_entry_text(block)
            if len(cleaned) < 15:
                continue
            entry_skills = list(extract_matched_skills(cleaned).keys())
            first_line = next((line.strip() for line in block if line.strip()), "")
            title = self._clean_project_title(first_line) if self._looks_like_project_header(first_line) else ""
            projects.append({
                'title': title,
                'description': cleaned[:500],
                'technologies': entry_skills
            })
            
        return projects[:6]
        
    def _clean_project_title(self, title: str) -> str:
        """Remove repository/link markers from a parsed project title."""
        cleaned = self._strip_list_prefix(title)
        cleaned = re.sub(r'\s*(?:[-–—|:]\s*)?(?:github\s*)?link\b.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(?:[-–—|:]\s*)?github\b.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip(" -–—|:")
        
    def _clean_certification_name(self, line: str) -> str:
        """Clean a certification/achievement line while preserving the credential name."""
        cleaned = self._strip_list_prefix(line)
        cleaned = re.sub(r'\s+-?\s*link\b.*$', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip(" -–—|")
    
    def _extract_certifications(self, cert_text: str) -> List[Dict[str, Any]]:
        """Extract professional certifications."""
        certifications = []
        target_text = cert_text.strip()
        
        if not target_text:
            return []
        
        for raw_line in target_text.splitlines():
            cleaned = self._clean_certification_name(raw_line)
            if not cleaned:
                continue
            if re.match(r'^(?:certifications?|achievements?|licenses?|courses?|languages?)\b', cleaned, re.IGNORECASE):
                continue
                
            parts = [part.strip() for part in re.split(r'\s*;\s*', cleaned) if part.strip()]
            if len(parts) > 1 and re.search(r'\s[-–—]\s', parts[0]):
                provider = re.split(r'\s[-–—]\s', parts[0], maxsplit=1)[0].strip()
                expanded_parts = [parts[0]] + [
                    f"{provider} - {part}" if not re.search(r'\s[-–—]\s', part) else part
                    for part in parts[1:]
                ]
            else:
                expanded_parts = parts
                
            for name in expanded_parts:
                name = self._clean_certification_name(name)
                if len(name) < 3:
                    continue
                certifications.append({'name': name[:120]})
                
        return certifications

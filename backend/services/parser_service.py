"""
Resume Parser Service
Extracts structured sections, evidence, skills, experience, education, and projects from PDF/DOCX resumes.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import pdfplumber
from docx import Document

from utils.normalization import normalize_text, extract_matched_skills, normalize_skill_list, normalize_resume_section_heading
from config.skill_aliases import get_canonical_skill


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
        skills_in_all = extract_matched_skills(text)
        
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
    
    def _extract_experience(self, exp_text: str) -> List[Dict[str, Any]]:
        """Extract structured work experience entries."""
        experience = []
        target_text = exp_text.strip()
        
        if not target_text:
            return []
            
        # Break into blocks by blank lines or job headers
        blocks = [b.strip() for b in re.split(r'\n\s*\n', target_text) if len(b.strip()) >= 20]
        
        if len(blocks) <= 1 and '\n' in target_text:
            # Fallback: split on common role header lines
            blocks = []
            lines = target_text.split('\n')
            current_block = []
            role_header_re = re.compile(r'^(?:senior|junior|lead|principal|staff|full\s*stack|software|backend|frontend|data|ml|ai|devops|cloud|product|engineer|developer|analyst|manager|consultant)\b', re.IGNORECASE)
            
            for line in lines:
                if role_header_re.search(line.strip()) and current_block:
                    blocks.append("\n".join(current_block))
                    current_block = [line]
                else:
                    current_block.append(line)
            if current_block:
                blocks.append("\n".join(current_block))

        for block in blocks:
            cleaned = block.strip()
            if len(cleaned) < 20:
                continue
            entry_skills = list(extract_matched_skills(cleaned).keys())
            experience.append({
                'description': cleaned[:300],
                'skills_applied': entry_skills
            })
            
        return experience[:6]
    
    def _extract_education(self, edu_text: str) -> List[Dict[str, Any]]:
        """Extract education credentials."""
        education = []
        target_text = edu_text.strip()
        
        if not target_text:
            return []
        
        degree_patterns = [
            r'(?:bachelor(?:\'s)?|b\.?\s?s\.?|b\.?\s?a\.?|b\.?\s?tech|b\.?\s?e\.?|undergraduate)\s*(?:of|in)?\s*([^\n,;]+)?',
            r'(?:master(?:\'s)?|m\.?\s?s\.?|m\.?\s?a\.?|m\.?\s?tech|m\.?\s?b\.?\s?a\.?|graduate)\s*(?:of|in)?\s*([^\n,;]+)?',
            r'(?:ph\.?d\.?|doctorate|doctor\s+of\s+philosophy)\s*(?:in)?\s*([^\n,;]+)?',
            r'(?:associate(?:\'s)?\s+degree)\s*(?:in)?\s*([^\n,;]+)?'
        ]
        
        for pat in degree_patterns:
            matches = re.finditer(pat, target_text, re.IGNORECASE)
            for m in matches:
                degree_full = m.group(0).strip()
                major = m.group(1).strip() if m.group(1) else ""
                education.append({
                    'degree': degree_full[:100],
                    'field': major[:60]
                })
                
        return education[:3]
    
    def _extract_projects(self, proj_text: str) -> List[Dict[str, Any]]:
        """Extract project entries with detected technologies."""
        projects = []
        target_text = proj_text.strip()
        
        if not target_text:
            return []
            
        blocks = [b.strip() for b in re.split(r'\n\s*\n', target_text) if len(b.strip()) >= 15]
        for block in blocks:
            cleaned = block.strip()
            if len(cleaned) < 15:
                continue
            entry_skills = list(extract_matched_skills(cleaned).keys())
            projects.append({
                'description': cleaned[:300],
                'technologies': entry_skills
            })
            
        return projects[:6]
    
    def _extract_certifications(self, cert_text: str) -> List[Dict[str, Any]]:
        """Extract professional certifications."""
        certifications = []
        target_text = cert_text.strip()
        
        if not target_text:
            return []
        
        cert_keywords = [
            "aws certified", "azure certified", "gcp certified", "pmp",
            "scrum master", "cisco", "ccna", "comptia", "tensorflow developer",
            "cka", "ckad", "cissp", "ceh"
        ]
        
        for cert in cert_keywords:
            if cert in target_text.lower():
                certifications.append({'name': cert.upper()})
                
        return certifications

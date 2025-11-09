"""
Resume Parser Service
Extracts information from PDF and DOCX files
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
import pdfplumber
from docx import Document


class ResumeParser:
    """Parse resumes and extract structured information"""
    
    def __init__(self):
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
    def parse_file(self, file_path: str) -> Dict:
        """Parse resume file and extract information"""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            text = self._extract_pdf_text(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            text = self._extract_docx_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Extract structured information
        parsed_data = self._extract_information(text)
        parsed_data['raw_text'] = text
        
        return parsed_data
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text from DOCX file"""
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    def _extract_information(self, text: str) -> Dict:
        """Extract structured information from resume text"""
        
        # Extract contact information
        emails = re.findall(self.email_pattern, text)
        phones = re.findall(self.phone_pattern, text)
        
        # Extract name (usually first line or near top)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        name = self._extract_name(lines)
        
        # Extract sections
        skills = self._extract_skills(text)
        experience = self._extract_experience(text)
        education = self._extract_education(text)
        projects = self._extract_projects(text)
        
        return {
            'name': name,
            'email': emails[0] if emails else None,
            'phone': phones[0] if phones else None,
            'skills': skills,
            'experience': experience,
            'education': education,
            'projects': projects
        }
    
    def _extract_name(self, lines: List[str]) -> Optional[str]:
        """Extract candidate name from resume"""
        # Name is typically in the first few lines
        for line in lines[:5]:
            # Skip lines that are too long or contain common keywords
            if len(line) < 50 and not any(keyword in line.lower() for keyword in 
                ['resume', 'cv', 'curriculum', 'email', 'phone', 'address']):
                # Check if it looks like a name (2-4 words, capitalized)
                words = line.split()
                if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
                    return line
        return "Candidate"
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume"""
        skills = []
        
        # Common technical skills
        skill_keywords = [
            'python', 'java', 'javascript', 'sql', 'r', 'c++', 'c#',
            'react', 'angular', 'vue', 'node', 'django', 'flask',
            'machine learning', 'deep learning', 'data analysis', 'data science',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'git', 'agile', 'scrum', 'leadership', 'communication',
            'project management', 'problem solving', 'teamwork',
            'excel', 'powerpoint', 'tableau', 'power bi', 'looker',
            'statistics', 'analytics', 'visualization', 'reporting'
        ]
        
        text_lower = text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                skills.append(skill.title())
        
        # Remove duplicates and return
        return list(set(skills))
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience from resume"""
        experience = []
        
        # Look for experience section
        exp_pattern = r'(?:experience|work history|employment)(.*?)(?:education|skills|projects|$)'
        match = re.search(exp_pattern, text.lower(), re.DOTALL)
        
        if match:
            exp_text = match.group(1)
            # Split by common delimiters
            entries = re.split(r'\n\s*\n', exp_text)
            
            for entry in entries[:5]:  # Limit to 5 most recent
                if len(entry.strip()) > 20:
                    experience.append({
                        'description': entry.strip()[:200]
                    })
        
        return experience
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education from resume"""
        education = []
        
        # Look for education section
        edu_pattern = r'(?:education|academic)(.*?)(?:experience|skills|projects|$)'
        match = re.search(edu_pattern, text.lower(), re.DOTALL)
        
        if match:
            edu_text = match.group(1)
            # Common degree patterns
            degrees = re.findall(r'(bachelor|master|phd|doctorate|b\.s\.|m\.s\.|b\.a\.|m\.a\.)[^\n]*', 
                                edu_text, re.IGNORECASE)
            
            for degree in degrees[:3]:
                education.append({
                    'degree': degree.strip()
                })
        
        return education
    
    def _extract_projects(self, text: str) -> List[Dict]:
        """Extract projects from resume"""
        projects = []
        
        # Look for projects section
        proj_pattern = r'(?:projects?|portfolio)(.*?)(?:experience|education|skills|$)'
        match = re.search(proj_pattern, text.lower(), re.DOTALL)
        
        if match:
            proj_text = match.group(1)
            entries = re.split(r'\n\s*\n', proj_text)
            
            for entry in entries[:5]:
                if len(entry.strip()) > 20:
                    projects.append({
                        'description': entry.strip()[:200]
                    })
        
        return projects

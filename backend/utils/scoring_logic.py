"""
Deterministic Evidence-Based Scoring Engine
Calculates profile strength, skill proficiency levels, role matches, and gap-driven actions with zero randomness.
"""

from typing import Dict, List, Tuple, Any, Optional, Set
import re

from config.roles import ROLE_DEFINITIONS
from config.skill_aliases import satisfies_skill
from config.scoring_config import (
    PROFILE_STRENGTH_WEIGHTS,
    ROLE_MATCH_WEIGHTS,
    SKILL_EVIDENCE_POINTS,
    IMPACT_ACTION_VERBS,
    ALIGNMENT_THRESHOLDS
)
from utils.normalization import normalize_skill_list


class ScoringEngine:
    """Deterministic, evidence-based resume scoring engine."""
    
    def __init__(self):
        self.role_definitions = ROLE_DEFINITIONS
        self.profile_weights = PROFILE_STRENGTH_WEIGHTS
        self.role_weights = ROLE_MATCH_WEIGHTS
        self.evidence_points = SKILL_EVIDENCE_POINTS
        self.action_verbs = IMPACT_ACTION_VERBS
        
    def _get_section_text(self, parsed_data: Dict[str, Any], section_name: str) -> str:
        """Return text for a specific evidence section, falling back only to structured entries from that section."""
        sections = parsed_data.get('sections', {})
        section_key = f'{section_name}_text'
        section_text = sections.get(section_key, '')
        if section_text:
            return section_text
            
        if section_name == 'experience':
            return "\n".join(entry.get('description', '') for entry in parsed_data.get('experience', []))
        if section_name == 'projects':
            return "\n".join(project.get('description', '') for project in parsed_data.get('projects', []))
        if section_name == 'education':
            return "\n".join(
                f"{edu.get('degree', '')} {edu.get('field', '')}"
                for edu in parsed_data.get('education', [])
            )
        if section_name == 'certifications':
            return "\n".join(cert.get('name', '') for cert in parsed_data.get('certifications', []))
        return ""
        
    def calculate_skill_evidence_score(self, skill_name: str, parsed_data: Dict[str, Any]) -> int:
        """
        Calculate an individual skill's evidence score (0-100) based on contextual occurrence across resume sections.
        """
        score = 0
        skill_lower = skill_name.lower()
        
        section_evidence = parsed_data.get('section_evidence', {})
        skills_sec = [s.lower() for s in section_evidence.get('skills_section', [])]
        exp_skills = [s.lower() for s in section_evidence.get('experience_skills', [])]
        proj_skills = [s.lower() for s in section_evidence.get('project_skills', [])]
        freq_map = section_evidence.get('all_skill_frequencies', {})
        
        # 1. Listed in dedicated Skills section
        if skill_lower in skills_sec or any(skill_lower in s for s in skills_sec):
            score += self.evidence_points['in_skills_section']
            
        # 2. Applied in Work Experience
        if skill_lower in exp_skills:
            score += self.evidence_points['in_experience_entry']
            
        # 3. Demonstrated in Projects
        proj_occurrences = sum(
            1 for p in parsed_data.get('projects', []) 
            if skill_lower in [t.lower() for t in p.get('technologies', [])] or skill_lower in p.get('description', '').lower()
        )
        if proj_occurrences >= 1:
            score += self.evidence_points['in_project_entry']
        if proj_occurrences >= 2:
            score += self.evidence_points['in_multiple_projects']
            
        # 4. Contextual Impact / Action Verbs nearby in evidence-bearing sections
        applied_text = "\n".join([
            self._get_section_text(parsed_data, 'experience'),
            self._get_section_text(parsed_data, 'projects')
        ]).lower()
        has_impact = False
        for verb in self.action_verbs:
            if verb in applied_text and skill_lower in applied_text:
                # Check rough proximity (within ~150 characters)
                for sentence in re.split(r'[.\n•]', applied_text):
                    if verb in sentence and skill_lower in sentence:
                        has_impact = True
                        break
            if has_impact:
                break
                
        if has_impact:
            score += self.evidence_points['action_impact_context']
            
        # Frequency bonus for high repetition (up to +10)
        total_freq = freq_map.get(skill_name, 0)
        if total_freq > 3:
            score += min((total_freq - 3) * 3, 10)
            
        # Conservative minimum for a detected skill outside stronger evidence sections
        if score == 0 and skill_name in parsed_data.get('skills', []):
            score = self.evidence_points['mentioned_elsewhere']
            
        return min(max(score, 0), self.evidence_points['max_score'])
    
    def calculate_skill_strengths(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate individual evidence scores for the candidate's actual detected skills.
        Returns top skills ranked by verified evidence level.
        """
        extracted_skills = parsed_data.get('skills', [])
        
        if not extracted_skills:
            return []
            
        evaluated_skills = []
        for skill in extracted_skills:
            score = self.calculate_skill_evidence_score(skill, parsed_data)
            evaluated_skills.append({
                'name': skill,
                'level': score
            })
            
        # Sort descending by evidence score, then alphabetically
        evaluated_skills.sort(key=lambda x: (-x['level'], x['name']))
        
        # Return top 6 most prominent skills for the candidate
        return evaluated_skills[:6]
    
    def calculate_role_matches(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate deterministic role matches against all configured role definitions.
        Returns top 3 matched roles sorted by match percentage with full explainability.
        """
        candidate_skills = set(parsed_data.get('skills', []))
        candidate_skills_lower = {s.lower() for s in candidate_skills}
        
        experience = parsed_data.get('experience', [])
        projects = parsed_data.get('projects', [])
        education = parsed_data.get('education', [])
        experience_text_lower = self._get_section_text(parsed_data, 'experience').lower()
        
        role_matches = []
        
        for role_name, role_data in self.role_definitions.items():
            req_skills = role_data.get('required_skills', [])
            pref_skills = role_data.get('preferred_skills', [])
            relevant_degrees = role_data.get('relevant_degrees', [])
            exp_keywords = role_data.get('experience_keywords', [])
            
            # 1. Required Skills Score (45%)
            matched_req = []
            req_evidence_sum = 0
            for skill in req_skills:
                if satisfies_skill(skill, candidate_skills):
                    matched_req.append(skill)
                    req_evidence_sum += self.calculate_skill_evidence_score(skill, parsed_data)
                    
            req_coverage = len(matched_req) / len(req_skills) if req_skills else 1.0
            avg_req_quality = (req_evidence_sum / (len(matched_req) * 100)) if matched_req else 0.0
            # Blend coverage with depth of evidence
            required_score = (req_coverage * 0.7 + req_coverage * avg_req_quality * 0.3) * 100
            
            # 2. Preferred Skills Score (20%)
            matched_pref = []
            for skill in pref_skills:
                if satisfies_skill(skill, candidate_skills):
                    matched_pref.append(skill)
            pref_coverage = len(matched_pref) / len(pref_skills) if pref_skills else 0.0
            preferred_score = min(pref_coverage * 1.25, 1.0) * 100
            
            # 3. Experience Relevance Score (20%)
            exp_score = 0.0
            if experience:
                keyword_hits = sum(1 for kw in exp_keywords if kw in experience_text_lower)
                exp_length_factor = min(len(experience) * 0.4, 1.0)
                kw_factor = min(keyword_hits * 0.35, 1.0)
                exp_score = (exp_length_factor * 0.5 + kw_factor * 0.5) * 100
            
            # 4. Projects Relevance Score (10%)
            proj_score = 0.0
            if projects:
                role_relevant_projects = 0
                for p in projects:
                    p_techs = [t.lower() for t in p.get('technologies', [])]
                    if any(s.lower() in p_techs for s in req_skills + pref_skills):
                        role_relevant_projects += 1
                proj_score = min((role_relevant_projects / max(len(projects), 1)) * 1.5, 1.0) * 100
                
            # 5. Education Relevance Score (5%)
            edu_score = 0.0
            for edu in education:
                edu_str = f"{edu.get('degree', '')} {edu.get('field', '')}".lower()
                if any(deg in edu_str for deg in relevant_degrees):
                    edu_score = 100.0
                    break
                    
            # Compute total weighted match score
            total_match = (
                (required_score * self.role_weights['required_skills']) +
                (preferred_score * self.role_weights['preferred_skills']) +
                (exp_score * self.role_weights['experience_relevance']) +
                (proj_score * self.role_weights['projects_relevance']) +
                (edu_score * self.role_weights['education_relevance'])
            )
            
            final_match_pct = int(round(min(max(total_match, 0), 98)))
            
            missing_req = [s for s in req_skills if s not in matched_req]
            missing_pref = [s for s in pref_skills if s not in matched_pref]
            
            role_matches.append({
                'title': role_name,
                'match': final_match_pct,
                'summary': role_data.get('summary', f"Alignment based on verified skill profile and projects."),
                'matched_required_skills': matched_req,
                'matched_preferred_skills': matched_pref,
                'missing_required_skills': missing_req,
                'missing_preferred_skills': missing_pref,
                'breakdown': {
                    'required_skills_pct': int(round(required_score)),
                    'preferred_skills_pct': int(round(preferred_score)),
                    'experience_pct': int(round(exp_score)),
                    'projects_pct': int(round(proj_score)),
                    'education_pct': int(round(edu_score))
                }
            })
            
        # Sort descending by match percentage
        role_matches.sort(key=lambda x: -x['match'])
        return role_matches[:3]
    
    def calculate_overall_fit_score(self, parsed_data: Dict[str, Any], top_role_match: Optional[int] = None) -> int:
        """
        Calculate deterministic overall Profile Strength score (0-100).
        """
        skills = parsed_data.get('skills', [])
        experience = parsed_data.get('experience', [])
        projects = parsed_data.get('projects', [])
        education = parsed_data.get('education', [])
        experience_text = self._get_section_text(parsed_data, 'experience').lower()
        
        # 1. Skills Evidence Component (35%)
        # Evaluates both skill count and their evidence scores
        if skills:
            evidence_scores = [self.calculate_skill_evidence_score(s, parsed_data) for s in skills]
            avg_evidence = sum(evidence_scores) / len(evidence_scores)
            count_factor = min(len(skills) / 10.0, 1.0) # 10 skills = max breadth
            skills_component = (avg_evidence * 0.6 + count_factor * 100 * 0.4)
        else:
            skills_component = 0.0
            
        # 2. Experience Quality Component (25%)
        if experience:
            exp_count_factor = min(len(experience) / 3.0, 1.0)
            verb_hits = sum(1 for v in self.action_verbs if v in experience_text)
            action_factor = min(verb_hits / 5.0, 1.0)
            experience_component = (exp_count_factor * 60 + action_factor * 40)
        else:
            experience_component = 0.0
            
        # 3. Projects Quality Component (20%)
        if projects:
            proj_count_factor = min(len(projects) / 3.0, 1.0)
            tech_count = sum(len(p.get('technologies', [])) for p in projects)
            tech_factor = min(tech_count / 6.0, 1.0)
            projects_component = (proj_count_factor * 60 + tech_factor * 40)
        else:
            projects_component = 0.0
            
        # 4. Education Component (10%)
        education_component = min(len(education) * 50, 100) if education else 0.0
        
        # 5. Role Alignment Component (10%)
        role_component = float(top_role_match) if top_role_match is not None else 0.0
        
        overall = (
            (skills_component * self.profile_weights['skills_evidence']) +
            (experience_component * self.profile_weights['experience_evidence']) +
            (projects_component * self.profile_weights['projects_evidence']) +
            (education_component * self.profile_weights['education_credentials']) +
            (role_component * self.profile_weights['best_role_alignment'])
        )
        
        return int(round(min(max(overall, 0), 100)))
    
    def calculate_role_alignment(self, fit_score: int) -> str:
        """Determine deterministic role alignment tier."""
        if fit_score >= ALIGNMENT_THRESHOLDS['high']:
            return "High"
        elif fit_score >= ALIGNMENT_THRESHOLDS['medium']:
            return "Medium"
        else:
            return "Low"
            
    def calculate_skill_coverage(self, parsed_data: Dict[str, Any]) -> int:
        """
        Calculate current Skill Coverage (0-100) from verified breadth and section evidence.
        """
        skills = parsed_data.get('skills', [])
        if not skills:
            return 0
            
        section_evidence = parsed_data.get('section_evidence', {})
        skills_section = set(section_evidence.get('skills_section', []))
        project_skills = set(section_evidence.get('project_skills', []))
        experience_skills = set(section_evidence.get('experience_skills', []))
        evidence_scores = [self.calculate_skill_evidence_score(skill, parsed_data) for skill in skills]
        
        breadth_component = min(len(skills) / 10.0, 1.0) * 30
        listed_component = (len(skills_section) / len(skills)) * 20
        project_component = (len(project_skills) / len(skills)) * 20
        experience_component = (len(experience_skills) / len(skills)) * 20
        depth_component = (sum(evidence_scores) / len(evidence_scores)) * 0.10
        
        coverage = breadth_component + listed_component + project_component + experience_component + depth_component
        return int(round(min(max(coverage, 0), 100)))
        
    def calculate_skill_momentum(self, parsed_data: Dict[str, Any]) -> int:
        """
        Deprecated compatibility alias for Skill Coverage.
        This is not historical momentum and must not be presented as growth.
        """
        return self.calculate_skill_coverage(parsed_data)
    
    def generate_next_actions(self, parsed_data: Dict[str, Any], role_matches: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Generate targeted next actions directly mapped to the skill gaps of the top matched role.
        """
        actions = []
        
        if not role_matches:
            return [
                {
                    'title': 'Add Technical Skills & Projects',
                    'description': 'Include specific programming languages, frameworks, and practical projects to your resume.'
                }
            ]
            
        top_role = role_matches[0]
        role_title = top_role['title']
        missing_req = top_role.get('missing_required_skills', [])
        missing_pref = top_role.get('missing_preferred_skills', [])
        matched_req = top_role.get('matched_required_skills', [])
        
        # Action 1: Address #1 Missing Required Skill
        if missing_req:
            target_skill = missing_req[0]
            actions.append({
                'title': f'Master {target_skill}',
                'description': f'Essential for {role_title}. Build a dedicated project or complete coursework to demonstrate hands-on competence.'
            })
        elif missing_pref:
            target_skill = missing_pref[0]
            actions.append({
                'title': f'Learn {target_skill}',
                'description': f'Expand your {role_title} competitiveness by adding {target_skill} to your technical toolkit.'
            })
        else:
            actions.append({
                'title': f'Deepen Advanced {matched_req[0] if matched_req else "Architecture"}',
                'description': f'Solidify your profile for senior {role_title} opportunities through advanced system design and optimization.'
            })
            
        # Action 2: Address Secondary Gap or Project Demonstration
        if len(missing_req) > 1:
            target_skill_2 = missing_req[1]
            actions.append({
                'title': f'Integrate {target_skill_2} into Portfolio',
                'description': f'Create an end-to-end portfolio case study showcasing practical implementation of {target_skill_2}.'
            })
        elif missing_pref and len(actions) < 2:
            target_pref = missing_pref[0] if not missing_req else missing_pref[0]
            actions.append({
                'title': f'Showcase {target_pref} Applications',
                'description': f'Highlight real-world applications of {target_pref} in your projects and work history.'
            })
        else:
            actions.append({
                'title': 'Quantify Work Impact & Metrics',
                'description': 'Enhance resume bullet points with measurable metrics (e.g., latency reduced, users served, efficiency gains).'
            })
            
        # Action 3: Professional Breadth / Cloud / System Readiness
        candidate_skills_lower = {s.lower() for s in parsed_data.get('skills', [])}
        if not any(cloud in candidate_skills_lower for cloud in ['aws', 'azure', 'gcp', 'docker', 'ci/cd']):
            actions.append({
                'title': 'Adopt Modern Cloud & DevOps Workflows',
                'description': 'Add containerization (Docker) and cloud deployments (AWS/GCP) to demonstrate production readiness.'
            })
        elif 'git' not in candidate_skills_lower:
            actions.append({
                'title': 'Emphasize Version Control & Collaboration',
                'description': 'Highlight Git workflows, code reviews, and cross-functional team delivery.'
            })
        else:
            actions.append({
                'title': 'Publish Case Studies & GitHub Repositories',
                'description': 'Ensure public repositories have detailed READMEs, architectural diagrams, and live demos.'
            })
            
        return actions[:3]
    
    def generate_insights(self, parsed_data: Dict[str, Any], fit_score: int, top_role: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate deterministic, evidence-backed highlights and insights.
        """
        insights = []
        skills_count = len(parsed_data.get('skills', []))
        exp_count = len(parsed_data.get('experience', []))
        proj_count = len(parsed_data.get('projects', []))
        
        # 1. Overall Profile Depth
        if fit_score >= 80:
            insights.append(f"Resume demonstrates strong multi-section evidence across {skills_count} verified technical competencies.")
        elif fit_score >= 60:
            insights.append(f"Solid foundational profile with {skills_count} verified skills and room to deepen applied evidence.")
        else:
            insights.append("Profile would benefit from more concrete project descriptions and explicit skill references.")
            
        # 2. Role Fit Insight
        if top_role:
            role_name = top_role['title']
            match_pct = top_role['match']
            matched_skills = top_role.get('matched_required_skills', [])
            if matched_skills:
                skills_str = ", ".join(matched_skills[:3])
                insights.append(f"Highest alignment with {role_name} ({match_pct}% match) supported by resume evidence for {skills_str}.")
            else:
                insights.append(f"Identified {role_name} as top potential trajectory ({match_pct}% match).")
                
        # 3. Practical Evidence Insight
        if proj_count >= 2 and exp_count >= 1:
            insights.append("Strong balance of practical project implementations alongside professional experience.")
        elif proj_count >= 1:
            insights.append("Practical portfolio projects provide tangible verification of applied technical skills.")
        else:
            insights.append("Adding dedicated project repositories will significantly boost technical evidence scores.")
            
        return insights

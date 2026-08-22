"""
Analysis Service
Generates comprehensive deterministic career analysis from parsed resume data.
"""

from typing import Dict, Any, Optional
from utils.scoring_logic import ScoringEngine


class AnalysisService:
    """Generate deterministic, evidence-based career analysis and recommendations"""
    
    def __init__(self):
        self.scoring_engine = ScoringEngine()
    
    def generate_analysis(self, parsed_data: Dict[str, Any], previous_fit_score: Optional[int] = None) -> Dict[str, Any]:
        """Generate complete deterministic analysis from parsed resume data."""
        
        # Calculate skill strengths based on verified evidence
        skill_strengths = self.scoring_engine.calculate_skill_strengths(parsed_data)
        
        # Calculate explainable role matches
        role_matches = self.scoring_engine.calculate_role_matches(parsed_data)
        top_role = role_matches[0] if role_matches else None
        top_role_match = top_role['match'] if top_role else None
        
        # Calculate overall profile fit score
        fit_score = self.scoring_engine.calculate_overall_fit_score(
            parsed_data,
            top_role_match,
            top_role['title'] if top_role else None
        )
        
        # Calculate role alignment tier
        role_alignment = self.scoring_engine.calculate_role_alignment(fit_score)
        
        # Calculate current skill coverage from resume evidence.
        skill_coverage = self.scoring_engine.calculate_skill_coverage(parsed_data)
        
        # Generate targeted next actions driven by top role gaps
        next_actions = self.scoring_engine.generate_next_actions(parsed_data, role_matches)
        
        # Generate evidence-backed insights
        insights = self.scoring_engine.generate_insights(parsed_data, fit_score, top_role)
        
        # Compute change vs previous review if historical score provided
        week_change = None
        if previous_fit_score is not None:
            week_change = fit_score - previous_fit_score
            
        # Compile complete analysis payload adhering to API contracts
        analysis = {
            'overall_insights': {
                'fit_score': fit_score,
                'week_change': week_change,
                'highlights': insights
            },
            'metrics': {
                'role_alignment': role_alignment,
                'skill_coverage': skill_coverage,
                # Deprecated compatibility alias: this is coverage, not historical growth.
                'skill_momentum': skill_coverage,
                'readiness_actions_count': len(next_actions)
            },
            'skill_strengths': skill_strengths,
            'role_matches': role_matches,
            'next_actions': next_actions,
            'candidate_info': {
                'name': parsed_data.get('name', 'Candidate'),
                'email': parsed_data.get('email'),
                'phone': parsed_data.get('phone'),
                'skills_count': len(parsed_data.get('skills', [])),
                'experience_count': len(parsed_data.get('experience', [])),
                'education_count': len(parsed_data.get('education', [])),
                'projects_count': len(parsed_data.get('projects', []))
            }
        }
        
        return analysis

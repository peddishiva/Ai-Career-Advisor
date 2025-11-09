"""
Analysis Service
Generates comprehensive career analysis from parsed resume data
"""

from typing import Dict
from utils.scoring_logic import ScoringEngine


class AnalysisService:
    """Generate career analysis and recommendations"""
    
    def __init__(self):
        self.scoring_engine = ScoringEngine()
    
    def generate_analysis(self, parsed_data: Dict) -> Dict:
        """Generate complete analysis from parsed resume data"""
        
        # Calculate overall fit score
        fit_score = self.scoring_engine.calculate_overall_fit_score(parsed_data)
        
        # Calculate role alignment
        role_alignment = self.scoring_engine.calculate_role_alignment(fit_score)
        
        # Calculate skill momentum
        skill_momentum = self.scoring_engine.calculate_skill_momentum(parsed_data)
        
        # Calculate skill strengths
        skill_strengths = self.scoring_engine.calculate_skill_strengths(parsed_data)
        
        # Calculate role matches
        role_matches = self.scoring_engine.calculate_role_matches(parsed_data)
        
        # Generate next actions
        next_actions = self.scoring_engine.generate_next_actions(parsed_data, role_matches)
        
        # Generate insights
        insights = self.scoring_engine.generate_insights(parsed_data, fit_score)
        
        # Compile complete analysis
        analysis = {
            'overall_insights': {
                'fit_score': fit_score,
                'week_change': 5,  # Could be calculated from historical data
                'highlights': insights
            },
            'metrics': {
                'role_alignment': role_alignment,
                'skill_momentum': skill_momentum,
                'readiness_actions_count': len(next_actions)
            },
            'skill_strengths': skill_strengths,
            'role_matches': role_matches,
            'next_actions': next_actions,
            'candidate_info': {
                'name': parsed_data.get('name', 'Candidate'),
                'email': parsed_data.get('email'),
                'skills_count': len(parsed_data.get('skills', [])),
                'experience_count': len(parsed_data.get('experience', [])),
                'education_count': len(parsed_data.get('education', []))
            }
        }
        
        return analysis

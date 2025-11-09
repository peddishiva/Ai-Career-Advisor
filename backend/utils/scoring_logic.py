"""
Scoring Logic for Resume Analysis
Calculates fit scores, skill levels, and role matches
"""

import random
from typing import Dict, List, Tuple


class ScoringEngine:
    """Calculate various scores and metrics for resume analysis"""
    
    # Skill categories and their weights
    SKILL_CATEGORIES = {
        'technical': ['python', 'java', 'javascript', 'sql', 'r', 'c++', 'c#', 
                     'machine learning', 'deep learning', 'data science'],
        'analytical': ['data analysis', 'statistics', 'analytics', 'excel', 
                      'tableau', 'power bi', 'looker', 'reporting'],
        'soft_skills': ['leadership', 'communication', 'teamwork', 'problem solving',
                       'project management', 'agile', 'scrum'],
        'tools': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git']
    }
    
    # Role definitions with required skills
    ROLE_DEFINITIONS = {
        'Data Analyst': {
            'required_skills': ['sql', 'data analysis', 'excel', 'python'],
            'preferred_skills': ['tableau', 'power bi', 'statistics', 'reporting'],
            'base_score': 75
        },
        'Product Analyst': {
            'required_skills': ['data analysis', 'sql', 'communication'],
            'preferred_skills': ['a/b testing', 'product strategy', 'storytelling'],
            'base_score': 70
        },
        'Business Intelligence Analyst': {
            'required_skills': ['sql', 'tableau', 'data analysis'],
            'preferred_skills': ['power bi', 'reporting', 'leadership'],
            'base_score': 72
        },
        'Data Scientist': {
            'required_skills': ['python', 'machine learning', 'statistics'],
            'preferred_skills': ['deep learning', 'r', 'data science'],
            'base_score': 68
        },
        'Software Engineer': {
            'required_skills': ['python', 'javascript', 'git'],
            'preferred_skills': ['react', 'node', 'docker', 'aws'],
            'base_score': 65
        }
    }
    
    def calculate_overall_fit_score(self, parsed_data: Dict) -> int:
        """Calculate overall fit score (0-100)"""
        score = 50  # Base score
        
        # Skills contribution (up to 30 points)
        skills = [s.lower() for s in parsed_data.get('skills', [])]
        skill_score = min(len(skills) * 2, 30)
        score += skill_score
        
        # Experience contribution (up to 15 points)
        experience = parsed_data.get('experience', [])
        exp_score = min(len(experience) * 3, 15)
        score += exp_score
        
        # Education contribution (up to 10 points)
        education = parsed_data.get('education', [])
        edu_score = min(len(education) * 5, 10)
        score += edu_score
        
        # Projects contribution (up to 10 points)
        projects = parsed_data.get('projects', [])
        proj_score = min(len(projects) * 2, 10)
        score += proj_score
        
        # Add some randomness for variation (±5 points)
        score += random.randint(-5, 5)
        
        return min(max(score, 0), 100)
    
    def calculate_role_alignment(self, fit_score: int) -> str:
        """Determine role alignment level"""
        if fit_score >= 80:
            return "High"
        elif fit_score >= 60:
            return "Medium"
        else:
            return "Low"
    
    def calculate_skill_momentum(self, parsed_data: Dict) -> int:
        """Calculate skill momentum percentage"""
        # Base momentum on number of skills and recent projects
        skills_count = len(parsed_data.get('skills', []))
        projects_count = len(parsed_data.get('projects', []))
        
        momentum = 5 + (skills_count // 3) + (projects_count * 2)
        momentum += random.randint(-3, 3)
        
        return min(max(momentum, 0), 25)
    
    def calculate_skill_strengths(self, parsed_data: Dict) -> List[Dict[str, any]]:
        """Calculate individual skill strength percentages"""
        skills = [s.lower() for s in parsed_data.get('skills', [])]
        
        # Predefined skill categories to analyze
        skill_analysis = {
            'Python': 0,
            'Data Analysis': 0,
            'Communication': 0,
            'Leadership': 0
        }
        
        # Calculate scores based on presence and context
        if 'python' in skills:
            skill_analysis['Python'] = random.randint(75, 90)
        else:
            skill_analysis['Python'] = random.randint(40, 65)
        
        if any(s in skills for s in ['data analysis', 'analytics', 'statistics']):
            skill_analysis['Data Analysis'] = random.randint(70, 85)
        else:
            skill_analysis['Data Analysis'] = random.randint(35, 60)
        
        if 'communication' in skills or 'leadership' in skills:
            skill_analysis['Communication'] = random.randint(65, 80)
        else:
            skill_analysis['Communication'] = random.randint(45, 65)
        
        if 'leadership' in skills or 'project management' in skills:
            skill_analysis['Leadership'] = random.randint(55, 75)
        else:
            skill_analysis['Leadership'] = random.randint(35, 60)
        
        return [
            {'name': name, 'level': level}
            for name, level in skill_analysis.items()
        ]
    
    def calculate_role_matches(self, parsed_data: Dict) -> List[Dict[str, any]]:
        """Calculate top role matches with percentages"""
        skills = [s.lower() for s in parsed_data.get('skills', [])]
        role_matches = []
        
        for role_name, role_data in self.ROLE_DEFINITIONS.items():
            score = role_data['base_score']
            
            # Check required skills
            required_matches = sum(1 for skill in role_data['required_skills'] 
                                  if skill in skills)
            score += required_matches * 5
            
            # Check preferred skills
            preferred_matches = sum(1 for skill in role_data['preferred_skills'] 
                                   if skill in skills)
            score += preferred_matches * 2
            
            # Add variation
            score += random.randint(-3, 3)
            
            role_matches.append({
                'title': role_name,
                'match': min(score, 95),
                'summary': self._generate_role_summary(role_name, score)
            })
        
        # Sort by match percentage and return top 3
        role_matches.sort(key=lambda x: x['match'], reverse=True)
        return role_matches[:3]
    
    def _generate_role_summary(self, role_name: str, score: int) -> str:
        """Generate a summary for role match"""
        summaries = {
            'Data Analyst': "Strong alignment with analytical strengths and project experience.",
            'Product Analyst': "Great fit for cross-functional collaboration and insight generation.",
            'Business Intelligence Analyst': "Solid foundation in reporting with opportunity to deepen leadership skills.",
            'Data Scientist': "Good technical foundation with room to grow in advanced ML techniques.",
            'Software Engineer': "Technical skills align well with modern development practices."
        }
        return summaries.get(role_name, "Good potential for this role based on your profile.")
    
    def generate_next_actions(self, parsed_data: Dict, role_matches: List[Dict]) -> List[Dict[str, str]]:
        """Generate personalized next best actions"""
        skills = [s.lower() for s in parsed_data.get('skills', [])]
        
        actions = []
        
        # Action 1: Based on missing skills
        if 'storytelling' not in skills and 'communication' not in skills:
            actions.append({
                'title': 'Strengthen Storytelling',
                'description': 'Create a portfolio case study that highlights impact-driven narratives.'
            })
        else:
            actions.append({
                'title': 'Expand Technical Toolkit',
                'description': 'Learn a new data visualization tool like Tableau or Power BI.'
            })
        
        # Action 2: Leadership development
        if 'leadership' not in skills:
            actions.append({
                'title': 'Grow Leadership Exposure',
                'description': 'Volunteer to lead a cross-team initiative to build people-management skills.'
            })
        else:
            actions.append({
                'title': 'Mentor Others',
                'description': 'Share your expertise by mentoring junior team members.'
            })
        
        # Action 3: Technical depth
        if 'sql' in skills:
            actions.append({
                'title': 'Deepen SQL Expertise',
                'description': 'Complete an advanced SQL project focusing on query optimization.'
            })
        else:
            actions.append({
                'title': 'Build SQL Foundation',
                'description': 'Complete a SQL fundamentals course and practice with real datasets.'
            })
        
        return actions
    
    def generate_insights(self, parsed_data: Dict, fit_score: int) -> List[str]:
        """Generate key insights about the resume"""
        insights = []
        
        skills_count = len(parsed_data.get('skills', []))
        experience_count = len(parsed_data.get('experience', []))
        
        # Insight 1: Overall strength
        if fit_score >= 80:
            insights.append("Resume showcases measurable impact across key projects.")
        else:
            insights.append("Resume demonstrates solid foundation with room for growth.")
        
        # Insight 2: Skill alignment
        if skills_count >= 8:
            insights.append("Skill profile strongly maps to analytical and strategy-focused roles.")
        else:
            insights.append("Consider highlighting additional technical and soft skills.")
        
        # Insight 3: Development areas
        if experience_count >= 3:
            insights.append("Opportunities exist to amplify leadership and stakeholder storytelling.")
        else:
            insights.append("Building more project experience will strengthen your profile.")
        
        return insights

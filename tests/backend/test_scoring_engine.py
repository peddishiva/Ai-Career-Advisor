"""
Comprehensive Tests for Deterministic Scoring Engine & Parser
Validates mathematical determinism, profile discrimination, alias normalization, and boundary constraints.
"""

import sys
from pathlib import Path
import unittest

# Ensure backend root is in sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from utils.scoring_logic import ScoringEngine
from utils.normalization import normalize_skill_list, get_canonical_skill
from services.analysis_service import AnalysisService


class TestDeterministicScoringEngine(unittest.TestCase):
    """Test suite for the deterministic scoring engine."""

    def setUp(self):
        self.scoring_engine = ScoringEngine()
        self.analysis_service = AnalysisService()

        # Sample Data Analyst Profile
        self.data_analyst_profile = {
            'name': 'Jane Doe',
            'email': 'jane.doe@example.com',
            'skills': ['Python', 'SQL', 'Tableau', 'Excel', 'Data Analysis', 'Statistics', 'Pandas'],
            'raw_text': (
                "Jane Doe\njane.doe@example.com\n\n"
                "TECHNICAL SKILLS\nPython, SQL, Tableau, Excel, Data Analysis, Statistics, Pandas\n\n"
                "WORK EXPERIENCE\nData Analyst at Acme Corp\n"
                "Developed optimized SQL queries and built Tableau dashboards for executive leadership. "
                "Analyzed customer behavior datasets using Python and Pandas to increase retention by 15%.\n\n"
                "PROJECTS\nSales Analytics Platform\n"
                "Engineered statistical regression models in Python and visualized KPI reports in Excel.\n\n"
                "EDUCATION\nBachelor of Science in Statistics"
            ),
            'section_evidence': {
                'skills_section': ['Python', 'SQL', 'Tableau', 'Excel', 'Data Analysis', 'Statistics', 'Pandas'],
                'experience_skills': ['SQL', 'Tableau', 'Python', 'Pandas', 'Data Analysis'],
                'project_skills': ['Python', 'Excel', 'Statistics'],
                'all_skill_frequencies': {'Python': 3, 'SQL': 2, 'Tableau': 2, 'Excel': 2, 'Data Analysis': 2, 'Statistics': 2, 'Pandas': 2},
                'sections_detected': ['skills', 'experience', 'projects', 'education']
            },
            'experience': [
                {
                    'description': 'Data Analyst at Acme Corp. Developed optimized SQL queries and built Tableau dashboards.',
                    'skills_applied': ['SQL', 'Tableau', 'Python', 'Pandas']
                }
            ],
            'projects': [
                {
                    'description': 'Sales Analytics Platform in Python and Excel.',
                    'technologies': ['Python', 'Excel', 'Statistics']
                }
            ],
            'education': [
                {'degree': 'Bachelor of Science', 'field': 'Statistics'}
            ]
        }

        # Sample Full Stack Developer Profile
        self.swe_profile = {
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'skills': ['JavaScript', 'TypeScript', 'React', 'Node.js', 'PostgreSQL', 'Docker', 'Git', 'REST APIs'],
            'raw_text': (
                "John Smith\njohn.smith@example.com\n\n"
                "SKILLS\nJavaScript, TypeScript, React, Node.js, PostgreSQL, Docker, Git, REST APIs\n\n"
                "EXPERIENCE\nFull Stack Developer at TechCo\n"
                "Architected scalable REST APIs in Node.js and TypeScript. Built responsive frontend in React. "
                "Deployed containerized microservices using Docker and managed Git CI/CD workflows.\n\n"
                "PROJECTS\nE-Commerce Web Application\n"
                "Implemented full stack solution with React, PostgreSQL, and Node.js.\n\n"
                "EDUCATION\nBachelor of Science in Computer Science"
            ),
            'section_evidence': {
                'skills_section': ['JavaScript', 'TypeScript', 'React', 'Node.js', 'PostgreSQL', 'Docker', 'Git', 'REST APIs'],
                'experience_skills': ['Node.js', 'TypeScript', 'React', 'Docker', 'Git', 'REST APIs'],
                'project_skills': ['React', 'PostgreSQL', 'Node.js'],
                'all_skill_frequencies': {'JavaScript': 2, 'TypeScript': 2, 'React': 3, 'Node.js': 3, 'PostgreSQL': 2, 'Docker': 2, 'Git': 2, 'REST APIs': 2},
                'sections_detected': ['skills', 'experience', 'projects', 'education']
            },
            'experience': [
                {
                    'description': 'Full Stack Developer at TechCo. Architected REST APIs in Node.js.',
                    'skills_applied': ['Node.js', 'TypeScript', 'React', 'Docker', 'Git', 'REST APIs']
                }
            ],
            'projects': [
                {
                    'description': 'E-Commerce Web Application in React and PostgreSQL.',
                    'technologies': ['React', 'PostgreSQL', 'Node.js']
                }
            ],
            'education': [
                {'degree': 'Bachelor of Science', 'field': 'Computer Science'}
            ]
        }

    def test_1_strict_mathematical_determinism(self):
        """Verify that running analysis 5 consecutive times produces mathematically identical results."""
        results = [self.analysis_service.generate_analysis(self.data_analyst_profile) for _ in range(5)]
        
        first_result = results[0]
        for i, res in enumerate(results[1:], start=2):
            self.assertEqual(res['overall_insights']['fit_score'], first_result['overall_insights']['fit_score'], f"Fit score differed on run {i}")
            self.assertEqual(res['metrics'], first_result['metrics'], f"Metrics differed on run {i}")
            self.assertEqual(res['skill_strengths'], first_result['skill_strengths'], f"Skill strengths differed on run {i}")
            self.assertEqual(res['role_matches'], first_result['role_matches'], f"Role matches differed on run {i}")
            self.assertEqual(res['next_actions'], first_result['next_actions'], f"Next actions differed on run {i}")
            self.assertEqual(res['overall_insights']['highlights'], first_result['overall_insights']['highlights'], f"Highlights differed on run {i}")

    def test_2_profile_discrimination(self):
        """Verify that Data profile ranks Data Analyst/Scientist top, and SWE profile ranks Full Stack/SWE top."""
        data_analysis = self.analysis_service.generate_analysis(self.data_analyst_profile)
        swe_analysis = self.analysis_service.generate_analysis(self.swe_profile)

        top_data_role = data_analysis['role_matches'][0]['title']
        top_swe_role = swe_analysis['role_matches'][0]['title']

        self.assertIn(top_data_role, ['Data Analyst', 'Data Scientist', 'Business Intelligence Analyst'])
        self.assertIn(top_swe_role, ['Full Stack Developer', 'Software Engineer'])
        
        # Verify match score of top role for strong candidate is >= 75
        self.assertGreaterEqual(data_analysis['role_matches'][0]['match'], 75)
        self.assertGreaterEqual(swe_analysis['role_matches'][0]['match'], 75)

    def test_3_skill_normalization_and_aliases(self):
        """Verify that skill aliases resolve to canonical names."""
        self.assertEqual(get_canonical_skill('react.js'), 'React')
        self.assertEqual(get_canonical_skill('REACTJS'), 'React')
        self.assertEqual(get_canonical_skill('k8s'), 'Kubernetes')
        self.assertEqual(get_canonical_skill('js'), 'JavaScript')
        self.assertEqual(get_canonical_skill('py'), 'Python')
        self.assertEqual(get_canonical_skill('postgres'), 'PostgreSQL')
        self.assertEqual(get_canonical_skill('powerbi'), 'Power BI')
        self.assertEqual(get_canonical_skill('sklearn'), 'Scikit-Learn')

        normalized = normalize_skill_list(['react.js', 'k8s', 'React', 'JS', 'python3'])
        self.assertEqual(normalized, ['JavaScript', 'Kubernetes', 'Python', 'React'])

    def test_4_boundaries_and_empty_profile(self):
        """Verify that empty/minimal profiles return valid bounded scores without errors."""
        empty_profile = {
            'name': 'Unknown',
            'skills': [],
            'experience': [],
            'projects': [],
            'education': [],
            'raw_text': '',
            'section_evidence': {}
        }
        res = self.analysis_service.generate_analysis(empty_profile)

        fit_score = res['overall_insights']['fit_score']
        self.assertGreaterEqual(fit_score, 0)
        self.assertLessEqual(fit_score, 100)
        self.assertIsNone(res['overall_insights']['week_change'])
        self.assertEqual(res['metrics']['role_alignment'], 'Low')
        self.assertIsInstance(res['next_actions'], list)
        self.assertGreater(len(res['next_actions']), 0)

    def test_5_no_random_import_in_scoring(self):
        """Verify that random is not imported in scoring_logic or analysis_service."""
        import utils.scoring_logic as sl
        import services.analysis_service as asrv
        
        self.assertFalse(hasattr(sl, 'random'), "scoring_logic should NOT import or use random")
        self.assertFalse(hasattr(asrv, 'random'), "analysis_service should NOT import or use random")
        
    def test_6_skill_coverage_is_deterministic(self):
        """Verify Skill Coverage is a stable current-evidence metric."""
        results = [self.analysis_service.generate_analysis(self.data_analyst_profile) for _ in range(5)]
        first = results[0]
        
        for res in results[1:]:
            self.assertEqual(res['metrics']['skill_coverage'], first['metrics']['skill_coverage'])
            self.assertEqual(res['metrics']['skill_momentum'], first['metrics']['skill_coverage'])
            self.assertEqual(res['skill_strengths'], first['skill_strengths'])
            self.assertEqual(res['role_matches'], first['role_matches'])
            self.assertEqual(res['next_actions'], first['next_actions'])
            
    def test_7_project_role_keywords_do_not_increase_experience_relevance(self):
        """Role keywords in Projects must not count as Experience relevance."""
        profile = {
            'name': 'Project Only Candidate',
            'skills': ['Python', 'SQL', 'Excel', 'Data Analysis'],
            'raw_text': (
                "SKILLS\nPython, SQL, Excel, Data Analysis\n\n"
                "PROJECTS\nBuilt a Data Analyst dashboard using Python and SQL."
            ),
            'sections': {
                'skills_text': 'Python, SQL, Excel, Data Analysis',
                'experience_text': '',
                'projects_text': 'Built a Data Analyst dashboard using Python and SQL.',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': ['Python', 'SQL', 'Excel', 'Data Analysis'],
                'experience_skills': [],
                'project_skills': ['Python', 'SQL', 'Data Analysis'],
                'all_skill_frequencies': {'Python': 2, 'SQL': 2, 'Excel': 1, 'Data Analysis': 2}
            },
            'experience': [],
            'projects': [{'description': 'Built a Data Analyst dashboard using Python and SQL.', 'technologies': ['Python', 'SQL', 'Data Analysis']}],
            'education': []
        }
        
        role_matches = self.scoring_engine.calculate_role_matches(profile)
        data_analyst = next(role for role in role_matches if role['title'] == 'Data Analyst')
        self.assertEqual(data_analyst['breakdown']['experience_pct'], 0)
        
    def test_8_applied_skill_evidence_beats_interest_only(self):
        """Applied evidence should score higher than interest-only mentions."""
        docker_interest = {
            'skills': ['Docker'],
            'raw_text': 'Interested in learning Docker.',
            'sections': {
                'skills_text': '',
                'experience_text': '',
                'projects_text': '',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': [],
                'experience_skills': [],
                'project_skills': [],
                'all_skill_frequencies': {'Docker': 1}
            },
            'experience': [],
            'projects': [],
            'education': []
        }
        docker_applied = {
            'skills': ['Docker'],
            'raw_text': 'PROJECTS\nDeployed production services using Docker.',
            'sections': {
                'skills_text': '',
                'experience_text': '',
                'projects_text': 'Deployed production services using Docker.',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': [],
                'experience_skills': [],
                'project_skills': ['Docker'],
                'all_skill_frequencies': {'Docker': 1}
            },
            'experience': [],
            'projects': [{'description': 'Deployed production services using Docker.', 'technologies': ['Docker']}],
            'education': []
        }
        ml_interest = {
            'skills': ['Machine Learning'],
            'raw_text': 'Interested in Machine Learning.',
            'sections': {
                'skills_text': '',
                'experience_text': '',
                'projects_text': '',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': [],
                'experience_skills': [],
                'project_skills': [],
                'all_skill_frequencies': {'Machine Learning': 1}
            },
            'experience': [],
            'projects': [],
            'education': []
        }
        ml_applied = {
            'skills': ['Machine Learning'],
            'raw_text': 'PROJECTS\nDeveloped and evaluated a Machine Learning model.',
            'sections': {
                'skills_text': '',
                'experience_text': '',
                'projects_text': 'Developed and evaluated a Machine Learning model.',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': [],
                'experience_skills': [],
                'project_skills': ['Machine Learning'],
                'all_skill_frequencies': {'Machine Learning': 1}
            },
            'experience': [],
            'projects': [{'description': 'Developed and evaluated a Machine Learning model.', 'technologies': ['Machine Learning']}],
            'education': []
        }
        
        self.assertGreater(
            self.scoring_engine.calculate_skill_evidence_score('Docker', docker_applied),
            self.scoring_engine.calculate_skill_evidence_score('Docker', docker_interest)
        )
        self.assertGreater(
            self.scoring_engine.calculate_skill_evidence_score('Machine Learning', ml_applied),
            self.scoring_engine.calculate_skill_evidence_score('Machine Learning', ml_interest)
        )
        
    def test_9_education_relevance_is_evidence_based(self):
        """Relevant education scores fully; unrelated and missing education score zero."""
        base_profile = {
            'name': 'Education Candidate',
            'skills': ['Python', 'SQL', 'Excel', 'Data Analysis'],
            'raw_text': '',
            'sections': {
                'skills_text': 'Python, SQL, Excel, Data Analysis',
                'experience_text': '',
                'projects_text': '',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': ['Python', 'SQL', 'Excel', 'Data Analysis'],
                'experience_skills': [],
                'project_skills': [],
                'all_skill_frequencies': {'Python': 1, 'SQL': 1, 'Excel': 1, 'Data Analysis': 1}
            },
            'experience': [],
            'projects': []
        }
        
        relevant = {**base_profile, 'education': [{'degree': 'Bachelor of Science', 'field': 'Data Analytics'}]}
        unrelated = {**base_profile, 'education': [{'degree': 'Bachelor of Arts', 'field': 'English Literature'}]}
        missing = {**base_profile, 'education': []}
        
        relevant_role = next(role for role in self.scoring_engine.calculate_role_matches(relevant) if role['title'] == 'Data Analyst')
        unrelated_role = next(role for role in self.scoring_engine.calculate_role_matches(unrelated) if role['title'] == 'Data Analyst')
        missing_role = next(role for role in self.scoring_engine.calculate_role_matches(missing) if role['title'] == 'Data Analyst')
        
        self.assertEqual(relevant_role['breakdown']['education_pct'], 100)
        self.assertEqual(unrelated_role['breakdown']['education_pct'], 0)
        self.assertEqual(missing_role['breakdown']['education_pct'], 0)
        
    def test_10_overall_education_component_uses_strongest_role_relevance(self):
        """Overall education contribution should not reward unrelated education entries."""
        base_profile = {
            'name': 'Overall Education Candidate',
            'skills': ['Python', 'SQL', 'Excel', 'Data Analysis'],
            'raw_text': '',
            'sections': {
                'skills_text': 'Python, SQL, Excel, Data Analysis',
                'experience_text': '',
                'projects_text': '',
                'education_text': '',
                'certifications_text': ''
            },
            'section_evidence': {
                'skills_section': ['Python', 'SQL', 'Excel', 'Data Analysis'],
                'experience_skills': [],
                'project_skills': [],
                'all_skill_frequencies': {'Python': 1, 'SQL': 1, 'Excel': 1, 'Data Analysis': 1}
            },
            'experience': [],
            'projects': []
        }
        
        relevant = {**base_profile, 'education': [{'degree': 'Bachelor of Science', 'field': 'Data Analytics'}]}
        unrelated = {**base_profile, 'education': [{'degree': 'Bachelor of Arts', 'field': 'English Literature'}]}
        missing = {**base_profile, 'education': []}
        
        relevant_score = self.scoring_engine.calculate_overall_fit_score(relevant, 0, 'Data Analyst')
        unrelated_score = self.scoring_engine.calculate_overall_fit_score(unrelated, 0, 'Data Analyst')
        missing_score = self.scoring_engine.calculate_overall_fit_score(missing, 0, 'Data Analyst')
        
        self.assertGreater(relevant_score, unrelated_score)
        self.assertEqual(unrelated_score, missing_score)


if __name__ == '__main__':
    unittest.main()

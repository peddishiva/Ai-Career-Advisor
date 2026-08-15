"""
Phase 1.5 Scoring Engine Validation Battery
Conducts comprehensive empirical validation of the deterministic, evidence-based resume scoring engine.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import json

# Set up backend module path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from services.parser_service import ResumeParser
from services.analysis_service import AnalysisService
from utils.scoring_logic import ScoringEngine
from utils.normalization import normalize_skill_list, get_canonical_skill


def create_synthetic_profiles() -> Dict[str, str]:
    """Generate 5 materially distinct synthetic resume profiles."""
    return {
        "Software Engineer": """
DAVID CHEN
david.chen@example.com | +1 (555) 101-2020 | San Francisco, CA

TECHNICAL SKILLS
Languages: Python, JavaScript, C++, C#, SQL
Core Concepts: REST APIs, System Design, Data Structures, Algorithms, Unit Testing, Git, Linux
Frameworks: FastAPI, Django, Flask, PyTest

PROFESSIONAL EXPERIENCE
Software Engineer | Scalable Systems Corp (2021 - Present)
- Architected high-performance backend microservices in Python and FastAPI serving 10M daily requests.
- Designed distributed caching with Redis, reducing database latency by 35%.
- Implemented robust unit testing and integration testing with PyTest achieving 92% code coverage.
- Managed code reviews and version control workflows across 15 engineers using Git.

Junior Developer | Nexus Software (2019 - 2021)
- Developed RESTful API endpoints and integrated relational database schemas in PostgreSQL.
- Optimized query execution plans and refactored legacy C++ services.

TECHNICAL PROJECTS
Distributed Task Orchestrator (Python, Redis, Git)
- Engineered an asynchronous distributed job queue with Python and Redis supporting 50,000 tasks/min.

Microservice API Gateway (FastAPI, Docker, Linux)
- Built an edge authentication gateway with rate limiting and automated routing.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley (2019)
""",

        "Full Stack Developer": """
SARAH JENKINS
sarah.jenkins@example.com | +1 (555) 202-3030 | New York, NY

TECHNICAL SKILLS
Frontend: JavaScript, TypeScript, React.js, Next.js, HTML, CSS, Tailwind CSS, Redux
Backend & Databases: Node.js, Express, PostgreSQL, MongoDB, REST APIs, GraphQL
Tools & Platforms: Docker, Git, CI/CD, Agile, Jest

PROFESSIONAL EXPERIENCE
Senior Full Stack Developer | Apex Digital Products (2021 - Present)
- Engineered responsive client interfaces using React, Next.js, and Tailwind CSS.
- Developed scalable backend services in Node.js and Express with PostgreSQL database storage.
- Integrated automated CI/CD deployment pipelines and containerized environments with Docker.
- Collaborated in cross-functional Agile sprints with UX designers and product managers.

Frontend Engineer | WebCraft Solutions (2019 - 2021)
- Built interactive single-page web applications with React, TypeScript, and Redux.
- Improved frontend Core Web Vitals and reduced bundle size by 40%.

KEY PROJECTS
E-Commerce Marketplace Platform (Next.js, TypeScript, PostgreSQL, Docker)
- Built full stack online store with product search, cart management, and payment checkout.

Collaborative Canvas App (React, Node.js, MongoDB)
- Developed real-time collaborative workspace with WebSockets and React components.

EDUCATION
Bachelor of Science in Software Engineering | University of Washington (2019)
""",

        "Data Analyst": """
MARCUS VANCE
marcus.vance@example.com | +1 (555) 303-4040 | Chicago, IL

TECHNICAL SKILLS
Analytics & Querying: SQL, Data Analysis, Data Visualization, Excel, Advanced Excel, Statistics
BI Tools: Tableau, Power BI, Looker, Reporting
Scripting: Python, Pandas, NumPy

PROFESSIONAL EXPERIENCE
Lead Data Analyst | Metro Insights Group (2020 - Present)
- Developed enterprise Tableau dashboards and executive Power BI KPI scorecards for Fortune 500 clients.
- Executed complex SQL analytical queries aggregating millions of customer transactions.
- Automated monthly financial variance reporting with Python, Pandas, and Advanced Excel formulas.
- Presented statistical cohort analyses and actionable churn reduction insights to C-suite leadership.

Data & Reporting Analyst | Horizon Retail (2018 - 2020)
- Analyzed regional sales performance data using Excel pivot tables, VLOOKUP, and SQL.
- Built interactive BI reporting dashboards tracking daily store inventory metrics.

KEY PROJECTS
Customer Retention Analytics Dashboard (Tableau, SQL, Data Analysis)
- Engineered customer lifecycle dashboard visualizing churn risks and retention drivers.

Financial Forecasting Model (Excel, Python, Statistics)
- Developed statistical forecasting regression model analyzing seasonal revenue patterns.

EDUCATION
Bachelor of Science in Data Analytics | University of Illinois at Urbana-Champaign (2018)
""",

        "Data Scientist / ML Engineer": """
DR. ELENA ROSTOVA
elena.rostova@example.com | +1 (555) 404-5050 | Boston, MA

TECHNICAL SKILLS
Machine Learning & AI: Machine Learning, Deep Learning, Artificial Intelligence, Natural Language Processing, Computer Vision
Frameworks & Libraries: PyTorch, TensorFlow, Scikit-Learn, Keras, Pandas, NumPy, SciPy
Languages & Systems: Python, R, SQL, Git, Docker, Linux, Statistics

PROFESSIONAL EXPERIENCE
Senior Machine Learning Scientist | NeuralTech Labs (2020 - Present)
- Researched, designed, and deployed deep learning transformers using PyTorch and Hugging Face.
- Trained predictive machine learning models in Scikit-Learn and TensorFlow with 94.8% accuracy.
- Conducted rigorous statistical hypothesis testing and feature engineering on multimodal datasets.
- Scaled distributed ML training pipelines on GPU clusters using Docker and Linux.

Machine Learning Engineer | DataVision AI (2018 - 2020)
- Built computer vision convolutional neural networks (CNNs) for real-time object detection in PyTorch.
- Optimized model inference latency using ONNX runtime and containerized microservices.

PROJECTS
Multimodal Document Understanding Transformer (PyTorch, Deep Learning, NLP)
- Built fine-tuned LLM transformer for semantic document classification and entity extraction.

Automated Defect Detection System (TensorFlow, Computer Vision, Python)
- Engineered end-to-end computer vision pipeline detecting manufacturing defects.

EDUCATION
Ph.D. in Computer Science (Machine Learning Focus) | Massachusetts Institute of Technology (2018)
Master of Science in Statistics | Columbia University (2014)
""",

        "DevOps / Cloud Engineer": """
ALEXANDER WRIGHT
alex.wright@example.com | +1 (555) 505-6060 | Seattle, WA

TECHNICAL SKILLS
Cloud Infrastructure: AWS, Azure, GCP, CloudFormation
Containers & Orchestration: Docker, Kubernetes, Helm, Microservices
Automation & CI/CD: Terraform, CI/CD, Jenkins, GitHub Actions, Linux, Shell, Git
Monitoring & Security: Prometheus, Grafana, Nginx, System Design

PROFESSIONAL EXPERIENCE
Senior DevOps & Infrastructure Engineer | CloudSphere Solutions (2020 - Present)
- Architected multi-region AWS cloud infrastructure using Terraform Infrastructure as Code (IaC).
- Deployed and managed production Kubernetes (EKS) clusters hosting 200+ containerized microservices.
- Built automated CI/CD deployment pipelines with GitHub Actions and Docker, reducing release cycles from days to minutes.
- Maintained 99.99% system uptime through Linux kernel tuning and Prometheus/Grafana monitoring.

Cloud Systems Administrator | Enterprise Hosting (2017 - 2020)
- Automated cloud server provisioning across AWS and Linux environments using Bash/Shell scripts.
- Implemented zero-downtime Nginx reverse proxy configurations and security hardening.

KEY PROJECTS
Automated Kubernetes GitOps Platform (Kubernetes, Terraform, AWS, Docker)
- Engineered declarative cloud deployment infrastructure managed via GitOps and Helm charts.

Enterprise Observability Stack (Prometheus, Grafana, Linux)
- Deployed unified monitoring and alerting pipeline tracking latency, memory, and error rates.

EDUCATION
Bachelor of Science in Cloud Computing & Information Technology | Purdue University (2017)
CERTIFICATIONS: AWS CERTIFIED
"""
    }


def run_phase_1_5_validation():
    """Execute complete Phase 1.5 validation suite."""
    parser = ResumeParser()
    analyzer = AnalysisService()
    scoring_engine = ScoringEngine()

    print("=" * 85)
    print("  PHASE 1.5 SCORING ENGINE VALIDATION BATTERY")
    print("=" * 85)
    print()

    # -------------------------------------------------------------
    # STEP 1: PARSING & COMPILATION OF 5 SYNTHETIC PROFILES
    # -------------------------------------------------------------
    profiles = create_synthetic_profiles()
    parsed_profiles: Dict[str, Dict[str, Any]] = {}
    analysis_results: Dict[str, Dict[str, Any]] = {}

    for name, text in profiles.items():
        parsed = parser._extract_information(text)
        parsed['raw_text'] = text
        parsed_profiles[name] = parsed
        analysis_results[name] = analyzer.generate_analysis(parsed)

    # -------------------------------------------------------------
    # STEP 2: PROFILE COMPARISON TABLE
    # -------------------------------------------------------------
    print("-" * 85)
    print("  1. PROFILE COMPARISON & DISCRIMINATION TABLE")
    print("-" * 85)
    header = f"{'Profile':<28} | {'Overall':<7} | {'Top Role (#1)':<24} | {'Match':<6} | {'#2 Role':<20} | {'Match':<6}"
    print(header)
    print("-" * len(header))

    discrimination_checks = []

    for name, res in analysis_results.items():
        overall = res['overall_insights']['fit_score']
        roles = res['role_matches']
        r1 = roles[0]['title'] if len(roles) > 0 else "N/A"
        m1 = f"{roles[0]['match']}%" if len(roles) > 0 else "0%"
        r2 = roles[1]['title'] if len(roles) > 1 else "N/A"
        m2 = f"{roles[1]['match']}%" if len(roles) > 1 else "0%"
        
        print(f"{name:<28} | {overall:<7} | {r1:<24} | {m1:<6} | {r2:<20} | {m2:<6}")

    print()
    print("-" * 85)
    print("  DETAILED PROFILE BREAKDOWN: TOP SKILLS & GAPS")
    print("-" * 85)
    for name, res in analysis_results.items():
        top_skills = ", ".join([f"{s['name']} ({s['level']}%)" for s in res['skill_strengths'][:4]])
        top_role = res['role_matches'][0]
        missing_req = top_role.get('missing_required_skills', [])
        missing_pref = top_role.get('missing_preferred_skills', [])
        gaps_str = f"Missing Req: {missing_req}" if missing_req else f"Missing Pref: {missing_pref[:2]}"
        
        print(f"Profile: {name}")
        print(f"  Top Evaluated Skills : {top_skills}")
        print(f"  #1 Role Alignment    : {top_role['title']} ({top_role['match']}%)")
        print(f"  Identified Gaps      : {gaps_str}")
        print(f"  Action #1            : {res['next_actions'][0]['title']}")
        print()

    # -------------------------------------------------------------
    # STEP 3: DISCRIMINATION ASSERTIONS
    # -------------------------------------------------------------
    swe_top = analysis_results["Software Engineer"]['role_matches'][0]['title']
    fullstack_top = analysis_results["Full Stack Developer"]['role_matches'][0]['title']
    data_top = analysis_results["Data Analyst"]['role_matches'][0]['title']
    ds_top = analysis_results["Data Scientist / ML Engineer"]['role_matches'][0]['title']
    devops_top = analysis_results["DevOps / Cloud Engineer"]['role_matches'][0]['title']

    pass_discrimination = (
        swe_top in ["Software Engineer", "Full Stack Developer"] and
        fullstack_top in ["Full Stack Developer", "Software Engineer"] and
        data_top in ["Data Analyst", "Business Intelligence Analyst"] and
        ds_top in ["Data Scientist", "Machine Learning Engineer"] and
        devops_top in ["DevOps / Cloud Engineer"]
    )

    print(f"Profile Discrimination Check: {'PASS' if pass_discrimination else 'FAIL'}")
    print()

    # -------------------------------------------------------------
    # STEP 4: 10X REPRODUCIBILITY / VALUE-EQUIVALENCE TEST
    # -------------------------------------------------------------
    print("-" * 85)
    print("  2. REPEATABILITY & VALUE-EQUIVALENCE (10 CONSECUTIVE RUNS)")
    print("-" * 85)
    determinism_failures = 0
    test_profile = parsed_profiles["Software Engineer"]
    baseline_analysis = analyzer.generate_analysis(test_profile)
    baseline_json = json.dumps(baseline_analysis, sort_keys=True)

    for i in range(1, 11):
        run_analysis = analyzer.generate_analysis(test_profile)
        run_json = json.dumps(run_analysis, sort_keys=True)
        if run_json != baseline_json:
            determinism_failures += 1
            print(f"  Run {i:02d}: MISMATCH detected!")
        else:
            print(f"  Run {i:02d}: Value-equivalent (0 deviation)")

    pass_determinism = (determinism_failures == 0)
    print(f"Determinism Check: {'PASS' if pass_determinism else 'FAIL'}")
    print()

    # -------------------------------------------------------------
    # STEP 5: EVIDENCE SENSITIVITY TESTS (A < B < C FOR 4 SKILLS)
    # -------------------------------------------------------------
    print("-" * 85)
    print("  3. EVIDENCE SENSITIVITY GRADIENT TESTS (A < B < C)")
    print("-" * 85)
    
    test_skills = ["Python", "React", "Docker", "SQL"]
    sensitivity_results = {}

    for skill in test_skills:
        # Case A: Stated only in Skills section
        case_a = {
            'name': 'Candidate A',
            'skills': [skill],
            'raw_text': f"SKILLS\n{skill}",
            'section_evidence': {
                'skills_section': [skill],
                'experience_skills': [],
                'project_skills': [],
                'all_skill_frequencies': {skill: 1}
            },
            'experience': [],
            'projects': []
        }
        score_a = scoring_engine.calculate_skill_evidence_score(skill, case_a)

        # Case B: Stated in Skills + 1 Project
        case_b = {
            'name': 'Candidate B',
            'skills': [skill],
            'raw_text': f"SKILLS\n{skill}\n\nPROJECTS\nBuilt application with {skill}.",
            'section_evidence': {
                'skills_section': [skill],
                'experience_skills': [],
                'project_skills': [skill],
                'all_skill_frequencies': {skill: 2}
            },
            'experience': [],
            'projects': [{'description': f'Built application with {skill}', 'technologies': [skill]}]
        }
        score_b = scoring_engine.calculate_skill_evidence_score(skill, case_b)

        # Case C: Stated in Skills + Multiple Projects + Work Experience + Impact Verb
        case_c = {
            'name': 'Candidate C',
            'skills': [skill],
            'raw_text': (
                f"SKILLS\n{skill}\n\n"
                f"EXPERIENCE\nSenior Engineer. Developed and optimized scalable services with {skill}.\n\n"
                f"PROJECTS\nProject 1 in {skill}.\nProject 2 with {skill}."
            ),
            'section_evidence': {
                'skills_section': [skill],
                'experience_skills': [skill],
                'project_skills': [skill],
                'all_skill_frequencies': {skill: 4}
            },
            'experience': [{'description': f'Developed and optimized scalable services with {skill}.', 'skills_applied': [skill]}],
            'projects': [
                {'description': f'Project 1 in {skill}', 'technologies': [skill]},
                {'description': f'Project 2 in {skill}', 'technologies': [skill]}
            ]
        }
        score_c = scoring_engine.calculate_skill_evidence_score(skill, case_c)

        is_monotonic = (score_a < score_b < score_c)
        sensitivity_results[skill] = {
            'A': score_a,
            'B': score_b,
            'C': score_c,
            'Monotonic': is_monotonic
        }
        print(f"  Skill: {skill:<10} | Level A: {score_a:2d}%  <  Level B: {score_b:2d}%  <  Level C: {score_c:2d}% | {'PASS' if is_monotonic else 'FAIL'}")

    pass_sensitivity = all(r['Monotonic'] for r in sensitivity_results.values())
    print(f"Evidence Sensitivity Check: {'PASS' if pass_sensitivity else 'FAIL'}")
    print()

    # -------------------------------------------------------------
    # STEP 6: MISSING-DATA & BOUNDARY ROBUSTNESS
    # -------------------------------------------------------------
    print("-" * 85)
    print("  4. MISSING-DATA & EDGE-CASE ROBUSTNESS")
    print("-" * 85)

    edge_cases = {
        "Empty Resume": {
            'name': 'Candidate',
            'skills': [],
            'experience': [],
            'projects': [],
            'education': [],
            'raw_text': '',
            'section_evidence': {}
        },
        "Skills Only": {
            'name': 'Candidate',
            'skills': ['Python', 'SQL'],
            'experience': [],
            'projects': [],
            'education': [],
            'raw_text': 'Python, SQL',
            'section_evidence': {'skills_section': ['Python', 'SQL'], 'all_skill_frequencies': {'Python': 1, 'SQL': 1}}
        },
        "Education Only": {
            'name': 'Candidate',
            'skills': [],
            'experience': [],
            'projects': [],
            'education': [{'degree': 'Bachelor of Science in Computer Science'}],
            'raw_text': 'Bachelor of Science in Computer Science',
            'section_evidence': {}
        },
        "Projects Only": {
            'name': 'Candidate',
            'skills': ['Python'],
            'experience': [],
            'projects': [{'description': 'Built an analytics dashboard in Python.', 'technologies': ['Python']}],
            'education': [],
            'raw_text': 'Built an analytics dashboard in Python.',
            'section_evidence': {'project_skills': ['Python'], 'all_skill_frequencies': {'Python': 1}}
        },
        "Experience Only": {
            'name': 'Candidate',
            'skills': ['Java'],
            'experience': [{'description': 'Worked as Java Developer for 2 years.', 'skills_applied': ['Java']}],
            'projects': [],
            'education': [],
            'raw_text': 'Worked as Java Developer for 2 years.',
            'section_evidence': {'experience_skills': ['Java'], 'all_skill_frequencies': {'Java': 1}}
        }
    }

    edge_case_passes = 0
    for cname, cdata in edge_cases.items():
        try:
            res = analyzer.generate_analysis(cdata)
            score = res['overall_insights']['fit_score']
            roles = res['role_matches']
            actions = res['next_actions']
            
            assert 0 <= score <= 100, f"Score out of range: {score}"
            assert isinstance(roles, list) and len(roles) > 0, "Role matches missing"
            assert isinstance(actions, list) and len(actions) > 0, "Actions missing"
            assert res['overall_insights']['week_change'] is None, "Week change should be None"
            
            print(f"  {cname:<20}: Handled cleanly | Score: {score:2d}% | Top Role: {roles[0]['title']} ({roles[0]['match']}%)")
            edge_case_passes += 1
        except Exception as e:
            print(f"  {cname:<20}: CRASHED with error: {e}")

    pass_missing_data = (edge_case_passes == len(edge_cases))
    print(f"Missing-Data Handling Check: {'PASS' if pass_missing_data else 'FAIL'}")
    print()

    # -------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------
    print("=" * 85)
    print("  PHASE 1.5 VALIDATION SUMMARY")
    print("=" * 85)
    print(f"A. Determinism           : {'PASS' if pass_determinism else 'FAIL'}")
    print(f"B. Profile Discrimination: {'PASS' if pass_discrimination else 'FAIL'}")
    print(f"C. Evidence Sensitivity  : {'PASS' if pass_sensitivity else 'FAIL'}")
    print(f"D. Missing-Data Handling : {'PASS' if pass_missing_data else 'FAIL'}")
    print("=" * 85)


if __name__ == '__main__':
    run_phase_1_5_validation()

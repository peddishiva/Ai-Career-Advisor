"""
Centralized Career Role Definitions
Defines target roles, required skills, preferred skills, relevant degree keywords, and summaries.
"""

from typing import Dict, List, Any

# Centralized role requirements and criteria
ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Software Engineer": {
        "title": "Software Engineer",
        "category": "Engineering",
        "required_skills": ["Python", "JavaScript", "Git", "REST APIs"],
        "preferred_skills": ["TypeScript", "React", "Node.js", "Docker", "AWS", "SQL", "Testing", "CI/CD"],
        "relevant_degrees": ["computer science", "software engineering", "computer engineering", "information technology", "electrical engineering"],
        "experience_keywords": ["software engineer", "developer", "backend", "frontend", "full stack", "web developer", "programmer"],
        "summary": "Technical capabilities align well with modern software design, version control, and system architecture."
    },
    "Full Stack Developer": {
        "title": "Full Stack Developer",
        "category": "Engineering",
        "required_skills": ["JavaScript", "React", "Node.js", "SQL", "Git"],
        "preferred_skills": ["TypeScript", "Next.js", "PostgreSQL", "MongoDB", "REST APIs", "Docker", "Tailwind CSS"],
        "relevant_degrees": ["computer science", "software engineering", "information technology", "computer applications"],
        "experience_keywords": ["full stack", "web developer", "frontend developer", "backend developer", "software developer"],
        "summary": "Strong balanced experience bridging interactive client interfaces and scalable backend server logic."
    },
    "Data Analyst": {
        "title": "Data Analyst",
        "category": "Data",
        "required_skills": ["SQL", "Data Analysis", "Excel", "Python"],
        "preferred_skills": ["Tableau", "Power BI", "Statistics", "Data Visualization", "Pandas", "Reporting"],
        "relevant_degrees": ["data analytics", "statistics", "mathematics", "computer science", "economics", "finance", "business analytics"],
        "experience_keywords": ["data analyst", "business analyst", "analytics", "reporting", "bi analyst", "insights"],
        "summary": "Strong alignment with analytical workflows, quantitative querying, reporting, and dashboard visualization."
    },
    "Data Scientist": {
        "title": "Data Scientist",
        "category": "Data",
        "required_skills": ["Python", "Machine Learning", "Statistics", "SQL"],
        "preferred_skills": ["Pandas", "NumPy", "Scikit-Learn", "Deep Learning", "Data Visualization", "R", "Data Science"],
        "relevant_degrees": ["data science", "machine learning", "statistics", "computer science", "mathematics", "physics"],
        "experience_keywords": ["data scientist", "machine learning engineer", "researcher", "statistician", "ai engineer"],
        "summary": "Deep foundation in mathematical modeling, machine learning algorithms, and predictive data solutions."
    },
    "Machine Learning Engineer": {
        "title": "Machine Learning Engineer",
        "category": "AI/ML",
        "required_skills": ["Python", "Machine Learning", "Deep Learning", "TensorFlow"],
        "preferred_skills": ["PyTorch", "Docker", "AWS", "Git", "Scikit-Learn", "Computer Vision", "Natural Language Processing"],
        "relevant_degrees": ["computer science", "artificial intelligence", "machine learning", "data science", "computational engineering"],
        "experience_keywords": ["machine learning engineer", "ml engineer", "ai engineer", "deep learning engineer", "research scientist"],
        "summary": "High technical proficiency in training, evaluating, optimizing, and deploying deep intelligence pipelines."
    },
    "Business Intelligence Analyst": {
        "title": "Business Intelligence Analyst",
        "category": "Data",
        "required_skills": ["SQL", "Tableau", "Data Analysis"],
        "preferred_skills": ["Power BI", "Excel", "Data Visualization", "Reporting", "Communication", "Leadership"],
        "relevant_degrees": ["business intelligence", "information systems", "business analytics", "data analytics", "management"],
        "experience_keywords": ["bi analyst", "business intelligence", "reporting analyst", "data visualization", "analytics consultant"],
        "summary": "Solid foundation in enterprise reporting, dashboard KPIs, and translating data into strategic decisions."
    },
    "Product Analyst": {
        "title": "Product Analyst",
        "category": "Product",
        "required_skills": ["Data Analysis", "SQL", "Communication"],
        "preferred_skills": ["Statistics", "Project Management", "Agile", "Tableau", "Problem Solving"],
        "relevant_degrees": ["business", "management", "economics", "computer science", "data analytics", "industrial engineering"],
        "experience_keywords": ["product analyst", "growth analyst", "product manager", "associate product manager", "business analyst"],
        "summary": "Great fit for cross-functional collaboration, customer metrics analysis, and product insight delivery."
    },
    "DevOps / Cloud Engineer": {
        "title": "DevOps / Cloud Engineer",
        "category": "Infrastructure",
        "required_skills": ["Docker", "Linux", "Git", "AWS"],
        "preferred_skills": ["Kubernetes", "CI/CD", "Terraform", "Python", "GCP", "Azure", "Shell"],
        "relevant_degrees": ["computer science", "information technology", "cloud computing", "systems engineering"],
        "experience_keywords": ["devops engineer", "cloud engineer", "infrastructure engineer", "site reliability engineer", "sre"],
        "summary": "Exceptional capability in infrastructure automation, container orchestration, and cloud deployment pipelines."
    }
}

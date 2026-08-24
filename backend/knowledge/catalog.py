"""Small, version-controlled seed catalog for Phase 3B."""

from datetime import date
from typing import Dict, Iterable, List

from config.roles import ROLE_DEFINITIONS
from config.skill_aliases import SKILL_ALIASES, get_all_canonical_skills, get_canonical_skill

from .models import (
    KnowledgeCategory,
    KnowledgeDifficulty,
    KnowledgeItem,
    KnowledgeSource,
    SourceType,
    TrustLevel,
)


KNOWLEDGE_BASE_VERSION = "3.1.0"
_CURATED_DATE = date(2026, 8, 24)


def _official_source(source_id: str, title: str, publisher: str, url: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        source_type=SourceType.OFFICIAL_DOCUMENTATION,
        title=title,
        publisher=publisher,
        url=url,
        version="1.0.0",
        curated_date=_CURATED_DATE,
        trust_level=TrustLevel.HIGH,
    )


def _curated_source(source_id: str, title: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        source_type=SourceType.CURATED_INTERNAL_GUIDANCE,
        title=title,
        publisher="AI Career Advisor project",
        version="1.0.0",
        curated_date=_CURATED_DATE,
        trust_level=TrustLevel.HIGH,
    )


SKILL_SOURCES: Dict[str, KnowledgeSource] = {
    "Python": _official_source("PYTHON-OFFICIAL", "Python Documentation", "Python Software Foundation", "https://docs.python.org/3/"),
    "Java": _official_source("JAVA-ORACLE", "Java Documentation", "Oracle", "https://docs.oracle.com/en/java/"),
    "JavaScript": _official_source("JAVASCRIPT-MDN", "JavaScript Guide", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
    "TypeScript": _official_source("TYPESCRIPT-OFFICIAL", "TypeScript Documentation", "TypeScript", "https://www.typescriptlang.org/docs/"),
    "FastAPI": _official_source("FASTAPI-OFFICIAL", "FastAPI Documentation", "FastAPI", "https://fastapi.tiangolo.com/"),
    "React": _official_source("REACT-OFFICIAL", "React Documentation", "React", "https://react.dev/"),
    "Docker": _official_source("DOCKER-OFFICIAL", "Docker Documentation", "Docker", "https://docs.docker.com/"),
    "Kubernetes": _official_source("KUBERNETES-OFFICIAL", "Kubernetes Documentation", "Kubernetes", "https://kubernetes.io/docs/"),
    "AWS": _official_source("AWS-OFFICIAL", "AWS Documentation", "Amazon Web Services", "https://docs.aws.amazon.com/"),
    "Azure": _official_source("AZURE-OFFICIAL", "Azure Documentation", "Microsoft", "https://learn.microsoft.com/azure/"),
    "GCP": _official_source("GCP-OFFICIAL", "Google Cloud Documentation", "Google Cloud", "https://cloud.google.com/docs"),
    "Git": _official_source("GIT-OFFICIAL", "Git Documentation", "Git", "https://git-scm.com/doc"),
}
_ENGINEERING_SOURCE = _curated_source("CURATED-ENGINEERING-GUIDANCE", "Curated Engineering Guidance")


SKILL_SEEDS = [
    ("Python", "programming-language", "Python is a general-purpose language commonly used for backend services, automation, and data work.", ["backend", "automation"], ["FastAPI", "REST APIs", "SQL"]),
    ("Java", "programming-language", "Java is a general-purpose language used for application and backend development.", ["backend", "application development"], ["SQL", "REST APIs"]),
    ("JavaScript", "programming-language", "JavaScript is a programming language used extensively for interactive web applications and server-side development.", ["web", "frontend", "backend"], ["React", "TypeScript", "REST APIs"]),
    ("TypeScript", "programming-language", "TypeScript adds static type-checking and tooling to JavaScript projects.", ["web", "typed javascript"], ["JavaScript", "React", "Node.js"]),
    ("SQL", "data-querying", "SQL is used to define, query, and transform data in relational database systems.", ["database", "querying", "analytics"], ["PostgreSQL", "Data Analysis", "Excel"]),
    ("Git", "version-control", "Git records source changes and supports collaborative version-control workflows.", ["version control", "collaboration"], ["CI/CD", "Agile"]),
    ("REST APIs", "web-architecture", "REST APIs expose application resources through web protocols and stable request/response contracts.", ["backend", "web services", "api design", "development"], ["FastAPI", "JavaScript", "Python"]),
    ("FastAPI", "backend-framework", "FastAPI is a Python framework for building typed HTTP APIs.", ["python", "backend", "web services"], ["Python", "REST APIs", "Docker"]),
    ("React", "frontend-library", "React is a library for composing user interfaces from reusable components.", ["frontend", "web", "components"], ["JavaScript", "TypeScript"]),
    ("Docker", "containerization", "Docker packages applications and their runtime dependencies into reproducible containers.", ["containers", "deployment", "backend"], ["Kubernetes", "CI/CD", "AWS"]),
    ("Kubernetes", "container-orchestration", "Kubernetes coordinates containerized workloads across a cluster.", ["containers", "orchestration", "deployment"], ["Docker", "AWS", "Azure"]),
    ("AWS", "cloud-platform", "AWS is a cloud platform that provides infrastructure and managed application services.", ["cloud", "infrastructure", "deployment"], ["Docker", "Kubernetes", "CI/CD"]),
    ("Azure", "cloud-platform", "Azure is a cloud platform that provides infrastructure and managed application services.", ["cloud", "infrastructure", "deployment"], ["Docker", "Kubernetes", "CI/CD"]),
    ("GCP", "cloud-platform", "Google Cloud provides infrastructure and managed services for applications and data workloads.", ["cloud", "data", "deployment"], ["Kubernetes", "Python", "SQL"]),
    ("Data Structures", "computer-science", "Data structures organize information so software can store, access, and transform it effectively.", ["dsa", "interview", "problem solving"], ["Algorithms", "OOP"]),
    ("Algorithms", "computer-science", "Algorithms are repeatable procedures for solving computational problems.", ["dsa", "interview", "problem solving"], ["Data Structures", "Python"]),
    ("OOP", "software-design", "Object-oriented programming organizes software around objects, state, behavior, and defined interfaces.", ["object oriented", "design", "interview"], ["Java", "Python", "System Design"]),
    ("System Design", "software-architecture", "System design considers components, interfaces, data flow, reliability, and operational trade-offs.", ["architecture", "scalability", "interview"], ["REST APIs", "Docker", "Kubernetes"]),
    ("CI/CD", "delivery-practice", "CI/CD automates stages of building, testing, and delivering software changes.", ["automation", "delivery", "deployment"], ["Git", "Docker", "Kubernetes"]),
    ("Excel", "data-analysis", "Excel supports tabular analysis, formulas, summaries, and practical reporting workflows.", ["data analyst", "reporting", "spreadsheets"], ["SQL", "Data Analysis", "Data Visualization"]),
    ("Pandas", "data-analysis", "Pandas provides Python data structures and operations for tabular data analysis.", ["python", "data analyst", "dataframes"], ["Python", "Data Analysis", "SQL"]),
    ("Tableau", "data-visualization", "Tableau supports interactive visual analysis and dashboard-based reporting.", ["data analyst", "reporting", "dashboard"], ["SQL", "Data Analysis", "Data Visualization"]),
    ("Statistics", "quantitative-analysis", "Statistics provides methods for describing data and reasoning about uncertainty.", ["data analyst", "data science", "analysis"], ["Data Analysis", "Python", "SQL"]),
]


def _roles_for_skill(skill: str) -> List[str]:
    roles = []
    for title, definition in ROLE_DEFINITIONS.items():
        configured_skills = {
            get_canonical_skill(value)
            for value in definition.get("required_skills", []) + definition.get("preferred_skills", [])
            if get_canonical_skill(value) in get_all_canonical_skills()
        }
        if skill in configured_skills:
            roles.append(title)
    return sorted(roles)


def _skill_item(
    index: int,
    name: str,
    subcategory: str,
    content: str,
    extra_keywords: Iterable[str],
    related_skills: Iterable[str],
) -> KnowledgeItem:
    keywords = [name, *SKILL_ALIASES.get(name, []), *extra_keywords]
    source = SKILL_SOURCES.get(name, _ENGINEERING_SOURCE)
    return KnowledgeItem(
        knowledge_id=f"SKILL-{name.upper().replace(' ', '-').replace('/', '-')}-{index:03d}",
        title=name,
        category=KnowledgeCategory.SKILL,
        subcategory=subcategory,
        content=content,
        keywords=keywords,
        related_skills=list(related_skills),
        roles=_roles_for_skill(name),
        difficulty=KnowledgeDifficulty.INTERMEDIATE,
        source=source,
        version="1.0.0",
    )


def _role_item(index: int, title: str, definition: Dict[str, object]) -> KnowledgeItem:
    configured_skills = [
        get_canonical_skill(value)
        for value in definition.get("required_skills", []) + definition.get("preferred_skills", [])
        if get_canonical_skill(value) in get_all_canonical_skills()
    ]
    experience_keywords = definition.get("experience_keywords", [])
    return KnowledgeItem(
        knowledge_id=f"ROLE-{title.upper().replace(' ', '-').replace('/', '-')}-{index:03d}",
        title=title,
        category=KnowledgeCategory.ROLE,
        subcategory=str(definition.get("category", "career")).casefold(),
        content=str(definition.get("summary", "")),
        keywords=[title, str(definition.get("category", "")), *experience_keywords],
        related_skills=configured_skills,
        roles=[title],
        source=_curated_source("CURATED-ROLE-GUIDANCE", "Curated Role Guidance"),
        version="1.0.0",
    )


INTERVIEW_SEEDS = [
    ("INTERVIEW-DSA-001", "Data Structures and Algorithms Interview Preparation", "interview", "Practice explaining data structures, algorithm choices, complexity trade-offs, and edge cases with small examples.", ["dsa", "interview"], ["Data Structures", "Algorithms"], ["Software Engineer", "Full Stack Developer", "Data Scientist", "Machine Learning Engineer"]),
    ("INTERVIEW-OOP-001", "Object-Oriented Programming Interview Preparation", "design", "Prepare to explain object responsibilities, interfaces, composition, inheritance, and maintainability trade-offs.", ["oop", "object oriented", "interview"], ["OOP"], ["Software Engineer", "Full Stack Developer"]),
    ("INTERVIEW-SQL-001", "SQL Interview Preparation", "data", "Prepare queries that demonstrate filtering, joins, aggregation, and clear reasoning about relational data.", ["sql", "database", "interview"], ["SQL"], ["Data Analyst", "Data Scientist", "Business Intelligence Analyst"]),
    ("INTERVIEW-REST-001", "REST API Interview Preparation", "backend", "Prepare to discuss resource modeling, HTTP contracts, validation, error handling, and versioning.", ["rest", "api", "backend", "interview"], ["REST APIs"], ["Software Engineer", "Full Stack Developer", "Machine Learning Engineer"]),
    ("INTERVIEW-SYSTEM-DESIGN-001", "System Design Interview Preparation", "architecture", "Prepare to describe components, interfaces, data flow, reliability considerations, and explicit trade-offs.", ["system design", "architecture", "interview"], ["System Design"], ["Software Engineer", "Full Stack Developer", "DevOps / Cloud Engineer"]),
]


GUIDANCE_SEEDS = [
    ("RESUME-GUIDANCE-EVIDENCE-001", "Evidence-Based Resume Bullets", "resume", "Describe an action, the technical context, and the observable result using only evidence present in the candidate's work.", ["resume", "bullets", "evidence", "impact"], ["Software Engineer", "Data Analyst"]),
    ("RESUME-GUIDANCE-SKILLS-001", "Skills Evidence", "resume", "A skill is more useful to a reviewer when its application is visible in experience or project evidence, not only in a skills list.", ["resume", "skills", "evidence"], ["Software Engineer", "Data Analyst", "Data Scientist"]),
    ("RESUME-GUIDANCE-PROJECTS-001", "Project Evidence", "resume", "Project entries should identify the problem, the candidate's contribution, the technologies used, and the result that can be verified.", ["resume", "projects", "evidence"], ["Software Engineer", "Full Stack Developer", "Machine Learning Engineer"]),
    ("RESUME-GUIDANCE-IMPACT-001", "Measurable Impact", "resume", "Use measurable impact only when the underlying metric is supported by the candidate's actual evidence.", ["resume", "impact", "metrics"], ["Software Engineer", "Data Analyst"]),
    ("RESUME-GUIDANCE-ATS-001", "ATS-Oriented Terminology", "resume", "Use clear role and skill terminology that matches the candidate's verified experience without adding unsupported keywords.", ["resume", "ats", "keywords"], list(ROLE_DEFINITIONS.keys())),
    ("LEARNING-GUIDANCE-BACKEND-001", "Backend Development Learning Path", "learning", "A practical backend path can connect Python, REST APIs, SQL, testing, containers, and deployment through progressively richer projects.", ["learning", "backend", "python", "rest", "sql"], ["Software Engineer", "Full Stack Developer"]),
    ("LEARNING-GUIDANCE-DATA-001", "Data Analytics Learning Path", "learning", "A practical analytics path can connect SQL, spreadsheets, data preparation, statistics, and visual reporting through evidence-backed exercises.", ["learning", "data analyst", "sql", "excel"], ["Data Analyst", "Business Intelligence Analyst"]),
]


def _guidance_item(
    knowledge_id: str,
    title: str,
    category: KnowledgeCategory,
    subcategory: str,
    content: str,
    keywords: Iterable[str],
    roles: Iterable[str],
    related_skills: Iterable[str] = (),
    source_id: str = "CURATED-RESUME-GUIDANCE",
    source_title: str = "Curated Resume Guidance",
) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        title=title,
        category=category,
        subcategory=subcategory,
        content=content,
        keywords=list(keywords),
        roles=list(roles),
        related_skills=list(related_skills),
        source=_curated_source(source_id, source_title),
        version="1.0.0",
    )


def _build_seed_items() -> List[KnowledgeItem]:
    items: List[KnowledgeItem] = [
        _skill_item(index, name, subcategory, content, keywords, related)
        for index, (name, subcategory, content, keywords, related) in enumerate(SKILL_SEEDS, start=1)
    ]
    items.extend(
        _role_item(index, title, definition)
        for index, (title, definition) in enumerate(ROLE_DEFINITIONS.items(), start=1)
    )
    items.extend(
        _guidance_item(
            knowledge_id,
            title,
            KnowledgeCategory.INTERVIEW_TOPIC,
            subcategory,
            content,
            keywords,
            roles,
            related_skills,
            source_id="CURATED-INTERVIEW-GUIDANCE",
            source_title="Curated Interview Guidance",
        )
        for knowledge_id, title, subcategory, content, keywords, related_skills, roles in INTERVIEW_SEEDS
    )
    items.extend(
        _guidance_item(
            knowledge_id,
            title,
            KnowledgeCategory.RESUME_GUIDANCE if knowledge_id.startswith("RESUME-") else KnowledgeCategory.LEARNING_GUIDANCE,
            subcategory,
            content,
            keywords,
            roles,
            related_skills=[get_canonical_skill(value) for value in keywords if get_canonical_skill(value) in get_all_canonical_skills()],
            source_id="CURATED-RESUME-GUIDANCE" if knowledge_id.startswith("RESUME-") else "CURATED-LEARNING-GUIDANCE",
            source_title="Curated Resume Guidance" if knowledge_id.startswith("RESUME-") else "Curated Learning Guidance",
        )
        for knowledge_id, title, subcategory, content, keywords, roles in GUIDANCE_SEEDS
    )
    items.append(
        _guidance_item(
            "REQUIREMENT-REQUIRED-PREFERRED-001",
            "Required and Preferred Skill Evidence",
            KnowledgeCategory.JOB_REQUIREMENT_CONCEPT,
            "matching",
            "Required and preferred requirements should remain separate so deterministic matching can preserve the job's stated priority.",
            ["required", "preferred", "must have", "nice to have", "job description"],
            list(ROLE_DEFINITIONS.keys()),
        )
    )
    return items


SEED_KNOWLEDGE_ITEMS = tuple(_build_seed_items())


def build_default_repository():
    from .repository import InMemoryKnowledgeRepository

    return InMemoryKnowledgeRepository(SEED_KNOWLEDGE_ITEMS, KNOWLEDGE_BASE_VERSION)

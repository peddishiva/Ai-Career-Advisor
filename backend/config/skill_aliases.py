"""
Comprehensive Skill Normalization & Alias Dictionary
Maps variations, acronyms, and aliases to canonical skill names.
"""

from typing import Dict, List, Set

# Canonical skill name -> list of aliases / variants (lowercase)
SKILL_ALIASES: Dict[str, List[str]] = {
    # Programming Languages
    "Python": ["python", "python3", "py", "python2", "cpython"],
    "JavaScript": ["javascript", "js", "ecmascript", "es6", "es2015", "es2020"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java", "jdk", "jvm", "j2ee"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", "c-sharp", ".net"],
    "C": ["c language", "ansi c", "c programming"],
    "Go": ["golang", "go language", "go lang"],
    "Rust": ["rust", "rustlang"],
    "Ruby": ["ruby", "ruby on rails", "rails"],
    "PHP": ["php", "php7", "php8"],
    "Swift": ["swift", "swiftui"],
    "Kotlin": ["kotlin", "android kotlin"],
    "R": ["r language", "r programming", "r-project"],
    "Scala": ["scala"],
    "SQL": ["sql", "structured query language", "plsql", "t-sql", "tsql"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3", "sass", "scss", "less"],
    "Shell": ["bash", "shell", "sh", "zsh", "powershell"],

    # Frontend Frameworks & Libraries
    "React": ["react", "react.js", "reactjs", "react native"],
    "Next.js": ["next.js", "nextjs", "next"],
    "Vue.js": ["vue", "vue.js", "vuejs", "vue3", "nuxt", "nuxtjs"],
    "Angular": ["angular", "angular.js", "angularjs", "angular 2+"],
    "Svelte": ["svelte", "sveltekit"],
    "Tailwind CSS": ["tailwind", "tailwindcss", "tailwind css"],
    "Bootstrap": ["bootstrap", "bootstrap5"],
    "Redux": ["redux", "redux toolkit", "rtk"],
    "GraphQL": ["graphql", "apollo", "relay"],

    # Backend & Web Frameworks
    "Node.js": ["node", "node.js", "nodejs"],
    "Express": ["express", "express.js", "expressjs"],
    "FastAPI": ["fastapi", "fast-api"],
    "Django": ["django", "django rest framework", "drf"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "spring", "spring framework", "springboot"],
    "ASP.NET": ["asp.net", "asp.net core", "dotnet core"],
    "NestJS": ["nestjs", "nest.js"],

    # Databases & Caching
    "PostgreSQL": ["postgresql", "postgres", "psql"],
    "MySQL": ["mysql", "mariadb"],
    "MongoDB": ["mongodb", "mongo", "nosql mongodb"],
    "Redis": ["redis", "redis cache"],
    "SQLite": ["sqlite", "sqlite3"],
    "Oracle Database": ["oracle db", "oracle database", "pl/sql"],
    "Microsoft SQL Server": ["mssql", "sql server", "microsoft sql"],
    "Elasticsearch": ["elasticsearch", "elastic search", "elk", "elk stack"],
    "DynamoDB": ["dynamodb", "aws dynamodb"],
    "Firebase": ["firebase", "firestore", "firebase auth", "cloud firestore"],
    "Cassandra": ["cassandra", "apache cassandra"],
    "Supabase": ["supabase"],

    # Data Science, ML & AI
    "Machine Learning": ["machine learning", "ml", "statistical learning", "supervised learning", "unsupervised learning"],
    "Deep Learning": ["deep learning", "dl", "neural networks", "artificial neural networks"],
    "Artificial Intelligence": ["artificial intelligence", "ai", "genai", "generative ai", "llm", "large language models"],
    "Data Science": ["data science", "data scientist"],
    "Data Analysis": ["data analysis", "data analytics", "exploratory data analysis", "eda"],
    "Natural Language Processing": ["natural language processing", "nlp", "transformers", "bert", "gpt"],
    "Computer Vision": ["computer vision", "cv", "image processing", "opencv"],
    "Statistics": ["statistics", "statistical analysis", "probability", "hypothesis testing", "regression"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Scikit-Learn": ["scikit-learn", "sklearn"],
    "TensorFlow": ["tensorflow", "tf"],
    "PyTorch": ["pytorch", "torch"],
    "Keras": ["keras"],
    "Data Visualization": ["data visualization", "visualization", "matplotlib", "seaborn", "plotly"],
    "Tableau": ["tableau", "tableau desktop", "tableau server"],
    "Power BI": ["power bi", "powerbi", "dax"],
    "Looker": ["looker", "lookml", "looker studio", "google data studio"],
    "Excel": ["excel", "microsoft excel", "advanced excel", "vlookup", "pivot tables", "spreadsheets"],
    "Apache Spark": ["spark", "apache spark", "pyspark"],
    "Hadoop": ["hadoop", "apache hadoop", "mapreduce"],

    # Cloud, DevOps & Infrastructure
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda", "cloudformation", "iam", "route53", "rds"],
    "Azure": ["azure", "microsoft azure", "azure devops", "azure functions"],
    "GCP": ["gcp", "google cloud", "google cloud platform", "bigquery", "google cloud storage"],
    "Docker": ["docker", "containerization", "dockerfile", "docker-compose"],
    "Kubernetes": ["kubernetes", "k8s", "helm"],
    "Git": ["git", "github", "gitlab", "version control", "bitbucket"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous deployment", "jenkins", "github actions", "gitlab ci"],
    "Terraform": ["terraform", "iac", "infrastructure as code"],
    "Linux": ["linux", "unix", "ubuntu", "debian", "centos", "redhat"],
    "Nginx": ["nginx"],
    "Kafka": ["kafka", "apache kafka"],
    "Microservices": ["microservices", "microservice architecture", "distributed systems"],
    "REST APIs": ["rest", "rest api", "restful", "rest apis", "api design", "web services", "endpoints"],

    # Engineering Practices & Soft Skills
    "Agile": ["agile", "scrum", "kanban", "sprint planning", "jira"],
    "Project Management": ["project management", "pmp", "project delivery", "roadmap planning"],
    "Leadership": ["leadership", "team leadership", "tech lead", "leading teams", "mentoring", "coaching"],
    "Communication": ["communication", "stakeholder management", "technical writing", "presentation", "cross-functional collaboration"],
    "Problem Solving": ["problem solving", "critical thinking", "troubleshooting", "analytical thinking", "debugging"],
    "Teamwork": ["teamwork", "collaboration", "cross-functional", "interpersonal skills"],
    "System Design": ["system design", "software architecture", "high level design", "low level design"],
    "Testing": ["unit testing", "integration testing", "test automation", "pytest", "jest", "cypress", "selenium", "tdd", "qa"],
    "Data Structures": ["data structures", "dsa"],
    "Algorithms": ["algorithm", "algorithms", "dsa"],
    "OOP": ["oop", "object oriented programming", "object-oriented programming"],
}

# Skill domain equivalence / sub-skill mapping
# If a role requires key skill K, possessing any sub-skill in the set satisfies K.
SKILL_RELATIONS: Dict[str, Set[str]] = {
    "SQL": {"SQL", "PostgreSQL", "MySQL", "SQLite", "Oracle Database", "Microsoft SQL Server"},
    "JavaScript": {"JavaScript", "TypeScript"},
    "TypeScript": {"TypeScript", "JavaScript"},
    "Machine Learning": {"Machine Learning", "Deep Learning", "Scikit-Learn", "TensorFlow", "PyTorch", "Keras"},
    "Deep Learning": {"Deep Learning", "TensorFlow", "PyTorch", "Keras"},
    "Data Analysis": {"Data Analysis", "Pandas", "NumPy", "Statistics", "Data Science"},
    "Data Science": {"Data Science", "Machine Learning", "Pandas", "Scikit-Learn", "Statistics"},
    "REST APIs": {"REST APIs", "FastAPI", "Express", "Django", "Flask", "Spring Boot", "NestJS"},
}

def satisfies_skill(target_skill: str, candidate_skills: Set[str]) -> bool:
    """Check if candidate skills contain target skill directly or via domain relationship."""
    if target_skill in candidate_skills:
        return True
    target_lower = target_skill.lower()
    if any(s.lower() == target_lower for s in candidate_skills):
        return True
    if target_skill in SKILL_RELATIONS:
        return any(s in candidate_skills for s in SKILL_RELATIONS[target_skill])
    return False

# Reverse lookup: alias string -> canonical skill name
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    # Also map the lowercase canonical name itself
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical

def get_canonical_skill(raw_skill: str) -> str:
    """Resolve a raw skill text to its canonical name if mapped, or return cleaned title-cased string."""
    cleaned = raw_skill.strip().lower()
    return ALIAS_TO_CANONICAL.get(cleaned, raw_skill.strip().title())

def get_all_canonical_skills() -> Set[str]:
    """Get the set of all known canonical skills."""
    return set(SKILL_ALIASES.keys())



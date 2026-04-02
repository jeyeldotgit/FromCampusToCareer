"""Taxonomy seed script — required Stage 1 deliverable.

Run once against a fresh database (safe to rerun; all operations are idempotent):
    python -m modules.taxonomy_admin.seed_taxonomy

Covers:
- 100+ canonical skills derived from unified_job_postings + ict_postings_2020_2025 datasets
- Alias variants for common misspellings, abbreviations, and alternate spellings
- Course-to-skill mappings for a representative BSIT / BSCS / BSIS curriculum
- PH grade-to-depth rules (1.00–3.00 scale)
- 22 active ICT target roles sourced directly from the dataset's role_normalized column
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.database import SessionLocal
from modules.taxonomy_admin.models import (
    CourseSkillMap,
    GradeDepthRule,
    RoleCatalog,
    Skill,
    SkillAlias,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

# Skills are grouped by domain for readability.
# All names match the canonical form used in the dataset's `skills` column.
SKILLS: list[dict[str, str]] = [

    # ── PROGRAMMING LANGUAGES ─────────────────────────────────────────────
    {"name": "Python",          "description": "General-purpose programming language; top skill across dataset"},
    {"name": "Java",            "description": "Object-oriented language for enterprise and Android development"},
    {"name": "JavaScript",      "description": "Web scripting language for frontend and backend (Node.js)"},
    {"name": "TypeScript",      "description": "Typed superset of JavaScript"},
    {"name": "PHP",             "description": "Server-side scripting language"},
    {"name": "C++",             "description": "Systems and embedded programming language"},
    {"name": "C#",              "description": ".NET ecosystem programming language"},
    {"name": "C",               "description": "Low-level systems programming language"},
    {"name": "Scala",           "description": "JVM language used in big data (Spark)"},
    {"name": "Rust",            "description": "Systems language emphasising memory safety"},
    {"name": "Kotlin",          "description": "JVM language for Android development"},
    {"name": "Swift",           "description": "Apple platform programming language"},
    {"name": "Dart",            "description": "Language used with the Flutter framework"},
    {"name": "R",               "description": "Statistical computing and data analysis language"},

    # ── WEB FRONTEND ──────────────────────────────────────────────────────
    {"name": "HTML",            "description": "Web markup language"},
    {"name": "CSS",             "description": "Web styling language"},
    {"name": "React",           "description": "JavaScript UI library by Meta"},
    {"name": "Vue.js",          "description": "Progressive JavaScript framework"},
    {"name": "Angular",         "description": "TypeScript-based web application framework"},
    {"name": "Bootstrap",       "description": "CSS component framework"},
    {"name": "SCSS",            "description": "CSS preprocessor syntax (Sass)"},
    {"name": "Webpack",         "description": "JavaScript module bundler"},
    {"name": "Figma",           "description": "Collaborative UI/UX design tool"},

    # ── WEB BACKEND & FRAMEWORKS ──────────────────────────────────────────
    {"name": "Node.js",         "description": "JavaScript runtime for server-side development"},
    {"name": "Spring Boot",     "description": "Java enterprise application framework"},
    {"name": "REST API",        "description": "RESTful API design and consumption"},
    {"name": "GraphQL",         "description": "API query language and runtime"},
    {"name": "Microservices",   "description": "Architectural pattern for distributed services"},
    {"name": "Laravel",         "description": "PHP web application framework"},
    {"name": "Django",          "description": "Python web framework"},
    {"name": "FastAPI",         "description": "Python async web framework"},

    # ── DATABASES ─────────────────────────────────────────────────────────
    {"name": "SQL",             "description": "Relational database query language"},
    {"name": "PostgreSQL",      "description": "Open-source relational database system"},
    {"name": "MySQL",           "description": "Widely used open-source relational database"},
    {"name": "MongoDB",         "description": "NoSQL document database"},
    {"name": "Redis",           "description": "In-memory key-value data store"},
    {"name": "Oracle",          "description": "Enterprise relational database platform"},
    {"name": "Snowflake",       "description": "Cloud data warehouse platform"},
    {"name": "BigQuery",        "description": "Google serverless data warehouse"},
    {"name": "Database Design", "description": "Relational schema modelling and normalisation"},

    # ── DATA ENGINEERING & ANALYTICS ─────────────────────────────────────
    {"name": "ETL",             "description": "Extract, Transform, Load data pipeline processes"},
    {"name": "Spark",           "description": "Distributed data processing engine (Apache Spark)"},
    {"name": "Hadoop",          "description": "Distributed storage and processing framework"},
    {"name": "Kafka",           "description": "Distributed event streaming platform"},
    {"name": "Airflow",         "description": "Workflow orchestration platform (Apache Airflow)"},
    {"name": "dbt",             "description": "SQL-based data transformation tool"},
    {"name": "pandas",          "description": "Python data analysis library"},
    {"name": "NumPy",           "description": "Python numerical computing library"},
    {"name": "Power BI",        "description": "Microsoft business intelligence and visualisation tool"},
    {"name": "Tableau",         "description": "Data visualisation and analytics platform"},
    {"name": "Looker",          "description": "Business intelligence and data exploration tool"},
    {"name": "DAX",             "description": "Data Analysis Expressions language for Power BI"},
    {"name": "Excel",           "description": "Microsoft spreadsheet and data analysis application"},
    {"name": "Data Visualization", "description": "Graphical representation of data insights"},
    {"name": "Data Analysis",   "description": "Statistical examination of datasets"},

    # ── MACHINE LEARNING & AI ─────────────────────────────────────────────
    {"name": "Machine Learning",    "description": "Statistical learning algorithms and model training"},
    {"name": "Deep Learning",       "description": "Neural network-based machine learning"},
    {"name": "NLP",                 "description": "Natural Language Processing techniques"},
    {"name": "TensorFlow",          "description": "Google open-source ML framework"},
    {"name": "PyTorch",             "description": "Meta open-source deep learning framework"},
    {"name": "Scikit-learn",        "description": "Python ML library for classical algorithms"},
    {"name": "MLflow",              "description": "ML lifecycle management platform"},
    {"name": "Hugging Face",        "description": "Hub and library for pre-trained transformer models"},
    {"name": "LLM",                 "description": "Large Language Model concepts and usage"},
    {"name": "Generative AI",       "description": "AI systems that generate content (text, images, code)"},
    {"name": "Prompt Engineering",  "description": "Designing effective inputs for LLM systems"},
    {"name": "RAG",                 "description": "Retrieval-Augmented Generation architecture"},
    {"name": "LangChain",           "description": "Framework for building LLM-powered applications"},
    {"name": "OpenAI API",          "description": "API access to OpenAI models (GPT-4, etc.)"},
    {"name": "Vector Databases",    "description": "Databases optimised for embedding/similarity search"},
    {"name": "Statistics",          "description": "Mathematical foundations of data analysis"},

    # ── AI GOVERNANCE ─────────────────────────────────────────────────────
    {"name": "AI Ethics",               "description": "Principles for responsible AI development"},
    {"name": "Responsible AI",          "description": "Frameworks ensuring fair and accountable AI"},
    {"name": "AI Governance Frameworks","description": "Policies and standards governing AI systems"},
    {"name": "Regulatory Compliance",   "description": "Adherence to legal and regulatory requirements"},
    {"name": "Data Governance",         "description": "Managing data availability, integrity, and security"},

    # ── DEVOPS & INFRASTRUCTURE ───────────────────────────────────────────
    {"name": "Docker",          "description": "Containerisation platform"},
    {"name": "Kubernetes",      "description": "Container orchestration system"},
    {"name": "Jenkins",         "description": "Open-source CI/CD automation server"},
    {"name": "Ansible",         "description": "IT automation and configuration management tool"},
    {"name": "Terraform",       "description": "Infrastructure-as-Code provisioning tool"},
    {"name": "CI/CD",           "description": "Continuous Integration and Continuous Delivery practices"},
    {"name": "Helm",            "description": "Kubernetes package manager"},
    {"name": "Grafana",         "description": "Observability and metrics visualisation platform"},
    {"name": "Prometheus",      "description": "Metrics collection and alerting toolkit"},
    {"name": "Bash",            "description": "Unix shell scripting language"},
    {"name": "Linux",           "description": "Open-source operating system"},
    {"name": "Git",             "description": "Distributed version control system"},
    {"name": "GitHub",          "description": "Git repository hosting and collaboration platform"},
    {"name": "Azure DevOps",    "description": "Microsoft DevOps services (pipelines, repos, boards)"},
    {"name": "CloudFormation",  "description": "AWS infrastructure-as-code service"},

    # ── CLOUD PLATFORMS ───────────────────────────────────────────────────
    {"name": "AWS",             "description": "Amazon Web Services cloud platform"},
    {"name": "Microsoft Azure", "description": "Microsoft cloud computing platform"},
    {"name": "Google Cloud",    "description": "Google Cloud Platform (GCP)"},
    {"name": "Cloud Computing", "description": "On-demand computing resources over the internet"},

    # ── CYBERSECURITY ─────────────────────────────────────────────────────
    {"name": "Cybersecurity",           "description": "Protecting digital systems and networks from threats"},
    {"name": "SIEM",                    "description": "Security Information and Event Management"},
    {"name": "Splunk",                  "description": "Log management and security analytics platform"},
    {"name": "Penetration Testing",     "description": "Authorised simulated cyberattacks on systems"},
    {"name": "OWASP",                   "description": "Open Web Application Security Project standards"},
    {"name": "Firewalls",               "description": "Network security devices controlling traffic"},
    {"name": "IDS/IPS",                 "description": "Intrusion Detection/Prevention Systems"},
    {"name": "Network Security",        "description": "Protecting network infrastructure and data"},
    {"name": "Zero Trust",              "description": "Security model requiring continuous verification"},
    {"name": "Incident Response",       "description": "Procedures for managing security incidents"},
    {"name": "Vulnerability Assessment","description": "Identifying and evaluating security weaknesses"},
    {"name": "CISSP",                   "description": "Certified Information Systems Security Professional"},

    # ── NETWORKING ────────────────────────────────────────────────────────
    {"name": "Network Administration",  "description": "Managing and maintaining computer networks"},
    {"name": "Cisco",                   "description": "Cisco networking hardware and IOS configuration"},
    {"name": "CCNA",                    "description": "Cisco Certified Network Associate certification"},
    {"name": "BGP",                     "description": "Border Gateway Protocol for internet routing"},
    {"name": "OSPF",                    "description": "Open Shortest Path First routing protocol"},
    {"name": "TCP/IP",                  "description": "Core internet communication protocols"},
    {"name": "VPN",                     "description": "Virtual Private Network configuration"},
    {"name": "Wireshark",               "description": "Network protocol analyser"},

    # ── IT OPERATIONS & SUPPORT ───────────────────────────────────────────
    {"name": "Active Directory",        "description": "Microsoft directory service for identity management"},
    {"name": "Windows Server",          "description": "Microsoft server operating system"},
    {"name": "VMware",                  "description": "Virtualisation platform"},
    {"name": "Office 365",              "description": "Microsoft cloud productivity suite"},
    {"name": "ITIL",                    "description": "IT Infrastructure Library service management framework"},
    {"name": "Ticketing Systems",       "description": "Help desk and IT service request management tools"},
    {"name": "PowerShell",              "description": "Microsoft task automation scripting language"},
    {"name": "Customer Service",        "description": "User-facing support and communication skills"},
    {"name": "Hardware Troubleshooting","description": "Diagnosing and resolving physical IT equipment issues"},

    # ── PROJECT & PRODUCT MANAGEMENT ─────────────────────────────────────
    {"name": "Agile",                   "description": "Iterative software development methodology"},
    {"name": "Scrum",                   "description": "Agile framework for team-based delivery"},
    {"name": "JIRA",                    "description": "Atlassian issue tracking and project management tool"},
    {"name": "Confluence",              "description": "Atlassian team collaboration and wiki platform"},
    {"name": "Project Management",      "description": "Planning, executing, and closing projects"},
    {"name": "Risk Management",         "description": "Identifying and mitigating project or business risks"},
    {"name": "Stakeholder Management",  "description": "Engaging and aligning project stakeholders"},
    {"name": "PMP",                     "description": "Project Management Professional certification"},
    {"name": "Waterfall",               "description": "Sequential software development methodology"},

    # ── SYSTEMS & BUSINESS ANALYSIS ──────────────────────────────────────
    {"name": "System Analysis",         "description": "Evaluating and specifying system requirements"},
    {"name": "Business Analysis",       "description": "Identifying business needs and solutions"},
    {"name": "Requirements Gathering",  "description": "Eliciting and documenting stakeholder requirements"},
    {"name": "UML",                     "description": "Unified Modelling Language for system design"},

    # ── QA & TESTING ─────────────────────────────────────────────────────
    {"name": "Selenium",                "description": "Web browser automation framework for testing"},
    {"name": "Postman",                 "description": "API testing and development tool"},
    {"name": "TestNG",                  "description": "Java testing framework"},
    {"name": "Cucumber",                "description": "Behaviour-Driven Development testing framework"},
    {"name": "Unit Testing",            "description": "Automated testing of individual code units"},

    # ── MOBILE DEVELOPMENT ────────────────────────────────────────────────
    {"name": "React Native",            "description": "Cross-platform mobile development framework"},
    {"name": "Flutter",                 "description": "Google cross-platform UI toolkit"},
    {"name": "Android Studio",          "description": "Official IDE for Android development"},

    # ── EMBEDDED & HARDWARE ───────────────────────────────────────────────
    {"name": "MATLAB",                  "description": "Numerical computing and simulation environment"},
    {"name": "Simulink",                "description": "MATLAB-based model-based design tool"},
    {"name": "FPGA",                    "description": "Field-Programmable Gate Array hardware"},
    {"name": "ARM",                     "description": "ARM processor architecture for embedded systems"},
    {"name": "RTOS",                    "description": "Real-Time Operating System for embedded devices"},
    {"name": "Embedded C",              "description": "C programming for microcontroller environments"},
    {"name": "Microcontrollers",        "description": "Integrated circuits for embedded control tasks"},

    # ── BLOCKCHAIN / WEB3 ─────────────────────────────────────────────────
    {"name": "Solidity",                "description": "Smart contract programming language for Ethereum"},
    {"name": "Ethereum",                "description": "Decentralised blockchain platform"},
    {"name": "Smart Contracts",         "description": "Self-executing code deployed on a blockchain"},
    {"name": "Web3.js",                 "description": "JavaScript library for Ethereum interaction"},

    # ── UX / DESIGN ───────────────────────────────────────────────────────
    {"name": "UI/UX Design",            "description": "User interface and experience design practice"},
    {"name": "Prototyping",             "description": "Creating interactive mockups for user testing"},
    {"name": "User Research",           "description": "Gathering insights about user needs and behaviours"},
    {"name": "Wireframing",             "description": "Low-fidelity layout sketching for UI design"},

    # ── GENERAL PROFESSIONAL ──────────────────────────────────────────────
    {"name": "Technical Documentation", "description": "Writing clear system and API documentation"},
    {"name": "Object-Oriented Programming", "description": "OOP design paradigm (encapsulation, inheritance, polymorphism)"},
    {"name": "Data Structures",         "description": "Algorithmic data organisation (arrays, trees, graphs)"},
    {"name": "Algorithms",              "description": "Computational problem-solving methods and complexity"},
    {"name": "SAP",                     "description": "SAP enterprise resource planning software"},
]


ALIASES: list[dict[str, str]] = [
    # Python
    {"alias": "py",                         "skill": "Python"},
    {"alias": "python3",                    "skill": "Python"},
    # JavaScript / TypeScript
    {"alias": "js",                         "skill": "JavaScript"},
    {"alias": "javascript",                 "skill": "JavaScript"},
    {"alias": "ts",                         "skill": "TypeScript"},
    # Frontend frameworks
    {"alias": "reactjs",                    "skill": "React"},
    {"alias": "react.js",                   "skill": "React"},
    {"alias": "vuejs",                      "skill": "Vue.js"},
    {"alias": "vue",                        "skill": "Vue.js"},
    {"alias": "angularjs",                  "skill": "Angular"},
    # Node / backend
    {"alias": "nodejs",                     "skill": "Node.js"},
    {"alias": "node",                       "skill": "Node.js"},
    # Databases
    {"alias": "postgres",                   "skill": "PostgreSQL"},
    {"alias": "postgresql",                 "skill": "PostgreSQL"},
    {"alias": "ms sql",                     "skill": "SQL"},
    {"alias": "mysql",                      "skill": "MySQL"},
    {"alias": "mongo",                      "skill": "MongoDB"},
    {"alias": "oracle database",            "skill": "Oracle"},
    # Cloud
    {"alias": "amazon web services",        "skill": "AWS"},
    {"alias": "aws cloud",                  "skill": "AWS"},
    {"alias": "azure",                      "skill": "Microsoft Azure"},
    {"alias": "microsoft azure",            "skill": "Microsoft Azure"},
    {"alias": "gcp",                        "skill": "Google Cloud"},
    {"alias": "google cloud platform",      "skill": "Google Cloud"},
    # DevOps / Infra
    {"alias": "docker container",           "skill": "Docker"},
    {"alias": "k8s",                        "skill": "Kubernetes"},
    {"alias": "kubectl",                    "skill": "Kubernetes"},
    {"alias": "ci/cd pipeline",             "skill": "CI/CD"},
    {"alias": "continuous integration",     "skill": "CI/CD"},
    {"alias": "git version control",        "skill": "Git"},
    {"alias": "github actions",             "skill": "GitHub"},
    {"alias": "atlassian jira",             "skill": "JIRA"},
    {"alias": "atlassian confluence",       "skill": "Confluence"},
    # AI / ML
    {"alias": "ml",                         "skill": "Machine Learning"},
    {"alias": "machine learning",           "skill": "Machine Learning"},
    {"alias": "gen ai",                     "skill": "Generative AI"},
    {"alias": "genai",                      "skill": "Generative AI"},
    {"alias": "gpt-4",                      "skill": "OpenAI API"},
    {"alias": "openai",                     "skill": "OpenAI API"},
    {"alias": "claude api",                 "skill": "LLM"},
    {"alias": "langchain",                  "skill": "LangChain"},
    {"alias": "rag pipeline",               "skill": "RAG"},
    {"alias": "vector db",                  "skill": "Vector Databases"},
    {"alias": "huggingface",                "skill": "Hugging Face"},
    {"alias": "scikit learn",               "skill": "Scikit-learn"},
    {"alias": "sklearn",                    "skill": "Scikit-learn"},
    {"alias": "pytorch",                    "skill": "PyTorch"},
    {"alias": "tensorflow",                 "skill": "TensorFlow"},
    # Data
    {"alias": "ms excel",                   "skill": "Excel"},
    {"alias": "microsoft excel",            "skill": "Excel"},
    {"alias": "powerbi",                    "skill": "Power BI"},
    {"alias": "microsoft power bi",         "skill": "Power BI"},
    {"alias": "apache spark",               "skill": "Spark"},
    {"alias": "apache kafka",               "skill": "Kafka"},
    {"alias": "apache airflow",             "skill": "Airflow"},
    {"alias": "dbt core",                   "skill": "dbt"},
    # Programming
    {"alias": "oop",                        "skill": "Object-Oriented Programming"},
    {"alias": "dsa",                        "skill": "Data Structures"},
    {"alias": "data structures and algorithms", "skill": "Algorithms"},
    # Networking
    {"alias": "ccnp",                       "skill": "CCNA"},
    {"alias": "cisco ccna",                 "skill": "CCNA"},
    # Testing
    {"alias": "selenium webdriver",         "skill": "Selenium"},
    {"alias": "rest assured",               "skill": "Postman"},
    # Mobile
    {"alias": "react-native",               "skill": "React Native"},
    {"alias": "flutter framework",          "skill": "Flutter"},
    # Agile
    {"alias": "scrum methodology",          "skill": "Scrum"},
    {"alias": "agile methodology",          "skill": "Agile"},
    # Embedded
    {"alias": "embedded systems",           "skill": "Embedded C"},
    {"alias": "simulink matlab",            "skill": "MATLAB"},
    # Blockchain
    {"alias": "smart contract",             "skill": "Smart Contracts"},
    {"alias": "web3",                       "skill": "Ethereum"},
    # UX
    {"alias": "ui/ux",                      "skill": "UI/UX Design"},
    {"alias": "ux design",                  "skill": "UI/UX Design"},
    # Security
    {"alias": "pentest",                    "skill": "Penetration Testing"},
    {"alias": "infosec",                    "skill": "Cybersecurity"},
    {"alias": "network security",           "skill": "Network Security"},
    {"alias": "responsible ai implementation", "skill": "Responsible AI"},
    {"alias": "ai governance",              "skill": "AI Governance Frameworks"},
    {"alias": "rest",                       "skill": "REST API"},
    {"alias": "restful api",                "skill": "REST API"},
    {"alias": "restful",                    "skill": "REST API"},
]


# course_code -> list of (skill_name, min_depth)
# Curriculum reflects BSIT / BSCS / BSIS typical course sequence.
# Depth levels: Foundational → Intermediate → Proficient → Advanced
COURSE_SKILL_MAPS: list[dict[str, str]] = [
    # Year 1 — Foundations
    {"course_code": "CC101", "skill": "Python",                      "min_depth": "Foundational"},
    {"course_code": "CC101", "skill": "Data Structures",             "min_depth": "Foundational"},
    {"course_code": "CC102", "skill": "Java",                        "min_depth": "Intermediate"},
    {"course_code": "CC102", "skill": "Object-Oriented Programming", "min_depth": "Intermediate"},
    {"course_code": "CC103", "skill": "Data Structures",             "min_depth": "Intermediate"},
    {"course_code": "CC103", "skill": "Algorithms",                  "min_depth": "Intermediate"},
    {"course_code": "CC104", "skill": "SQL",                         "min_depth": "Intermediate"},
    {"course_code": "CC104", "skill": "Database Design",             "min_depth": "Intermediate"},
    {"course_code": "CC105", "skill": "HTML",                        "min_depth": "Proficient"},
    {"course_code": "CC105", "skill": "CSS",                         "min_depth": "Proficient"},
    {"course_code": "CC105", "skill": "JavaScript",                  "min_depth": "Foundational"},
    # Year 2 — Core technical
    {"course_code": "CC106", "skill": "Python",                      "min_depth": "Proficient"},
    {"course_code": "CC106", "skill": "pandas",                      "min_depth": "Intermediate"},
    {"course_code": "CC106", "skill": "NumPy",                       "min_depth": "Intermediate"},
    {"course_code": "CC107", "skill": "Machine Learning",            "min_depth": "Foundational"},
    {"course_code": "CC107", "skill": "Data Analysis",               "min_depth": "Intermediate"},
    {"course_code": "CC107", "skill": "Statistics",                  "min_depth": "Intermediate"},
    {"course_code": "CC108", "skill": "Network Administration",      "min_depth": "Intermediate"},
    {"course_code": "CC108", "skill": "Linux",                       "min_depth": "Foundational"},
    {"course_code": "CC108", "skill": "TCP/IP",                      "min_depth": "Foundational"},
    {"course_code": "CC109", "skill": "Cybersecurity",               "min_depth": "Foundational"},
    {"course_code": "CC109", "skill": "Network Security",            "min_depth": "Foundational"},
    {"course_code": "CC110", "skill": "Project Management",          "min_depth": "Foundational"},
    {"course_code": "CC110", "skill": "Agile",                       "min_depth": "Foundational"},
    {"course_code": "CC110", "skill": "Scrum",                       "min_depth": "Foundational"},
    # Year 3 — Specialisation tracks
    {"course_code": "CC111", "skill": "System Analysis",             "min_depth": "Intermediate"},
    {"course_code": "CC111", "skill": "Requirements Gathering",      "min_depth": "Intermediate"},
    {"course_code": "CC111", "skill": "UML",                         "min_depth": "Foundational"},
    {"course_code": "CC112", "skill": "React",                       "min_depth": "Intermediate"},
    {"course_code": "CC112", "skill": "Node.js",                     "min_depth": "Foundational"},
    {"course_code": "CC112", "skill": "REST API",                    "min_depth": "Intermediate"},
    {"course_code": "CC113", "skill": "Cloud Computing",             "min_depth": "Foundational"},
    {"course_code": "CC113", "skill": "AWS",                         "min_depth": "Foundational"},
    {"course_code": "CC113", "skill": "Microsoft Azure",             "min_depth": "Foundational"},
    {"course_code": "CC114", "skill": "Unit Testing",                "min_depth": "Intermediate"},
    {"course_code": "CC114", "skill": "Git",                         "min_depth": "Proficient"},
    {"course_code": "CC114", "skill": "Selenium",                    "min_depth": "Foundational"},
    {"course_code": "CC115", "skill": "Docker",                      "min_depth": "Foundational"},
    {"course_code": "CC115", "skill": "CI/CD",                       "min_depth": "Foundational"},
    {"course_code": "CC116", "skill": "Technical Documentation",     "min_depth": "Proficient"},
    {"course_code": "CC116", "skill": "JIRA",                        "min_depth": "Intermediate"},
    {"course_code": "CC117", "skill": "UI/UX Design",                "min_depth": "Foundational"},
    {"course_code": "CC117", "skill": "Figma",                       "min_depth": "Foundational"},
    {"course_code": "CC117", "skill": "Wireframing",                 "min_depth": "Foundational"},
    {"course_code": "CC118", "skill": "PHP",                         "min_depth": "Intermediate"},
    {"course_code": "CC118", "skill": "Laravel",                     "min_depth": "Foundational"},
    {"course_code": "CC119", "skill": "Excel",                       "min_depth": "Intermediate"},
    {"course_code": "CC119", "skill": "Power BI",                    "min_depth": "Foundational"},
    {"course_code": "CC119", "skill": "Data Visualization",          "min_depth": "Foundational"},
    {"course_code": "CC120", "skill": "PostgreSQL",                  "min_depth": "Intermediate"},
    {"course_code": "CC120", "skill": "MongoDB",                     "min_depth": "Foundational"},
    # Year 4 — Advanced / emerging
    {"course_code": "CC121", "skill": "Kubernetes",                  "min_depth": "Intermediate"},
    {"course_code": "CC121", "skill": "Ansible",                     "min_depth": "Foundational"},
    {"course_code": "CC121", "skill": "Terraform",                   "min_depth": "Foundational"},
    {"course_code": "CC122", "skill": "Machine Learning",            "min_depth": "Proficient"},
    {"course_code": "CC122", "skill": "TensorFlow",                  "min_depth": "Intermediate"},
    {"course_code": "CC122", "skill": "PyTorch",                     "min_depth": "Intermediate"},
    {"course_code": "CC123", "skill": "Generative AI",               "min_depth": "Foundational"},
    {"course_code": "CC123", "skill": "LLM",                         "min_depth": "Foundational"},
    {"course_code": "CC123", "skill": "Prompt Engineering",          "min_depth": "Foundational"},
    {"course_code": "CC124", "skill": "Cybersecurity",               "min_depth": "Intermediate"},
    {"course_code": "CC124", "skill": "Penetration Testing",         "min_depth": "Foundational"},
    {"course_code": "CC124", "skill": "OWASP",                       "min_depth": "Foundational"},
    {"course_code": "CC125", "skill": "Business Analysis",           "min_depth": "Intermediate"},
    {"course_code": "CC125", "skill": "Stakeholder Management",      "min_depth": "Intermediate"},
    {"course_code": "CC126", "skill": "AI Ethics",                   "min_depth": "Foundational"},
    {"course_code": "CC126", "skill": "Responsible AI",              "min_depth": "Foundational"},
    {"course_code": "CC126", "skill": "Data Governance",             "min_depth": "Foundational"},
]


GRADE_DEPTH_RULES: list[dict] = [
    {"min_grade": "1.00", "max_grade": "1.50", "depth_level": "Advanced"},
    {"min_grade": "1.51", "max_grade": "2.00", "depth_level": "Proficient"},
    {"min_grade": "2.01", "max_grade": "2.75", "depth_level": "Intermediate"},
    {"min_grade": "2.76", "max_grade": "3.00", "depth_level": "Foundational"},
]


# 22 roles sourced directly from role_normalized column in dataset.
# Ordered by posting frequency (descending).
ROLES: list[dict[str, str]] = [
    {"name": "Software Engineer",       "description": "Designs, develops, and maintains software systems"},
    {"name": "QA Engineer",             "description": "Ensures software quality through manual and automated testing"},
    {"name": "Data Analyst",            "description": "Analyses datasets to generate actionable business insights"},
    {"name": "Web Developer",           "description": "Builds and maintains web applications and interfaces"},
    {"name": "DevOps Engineer",         "description": "Manages CI/CD pipelines, infrastructure, and deployment automation"},
    {"name": "Systems Engineer",        "description": "Designs and integrates complex IT and hardware systems"},
    {"name": "Cybersecurity Engineer",  "description": "Protects systems and networks from cyber threats"},
    {"name": "Data Scientist",          "description": "Builds predictive models and extracts insights from large datasets"},
    {"name": "Data Engineer",           "description": "Constructs and maintains data pipelines and warehouses"},
    {"name": "Cloud Engineer",          "description": "Architects and operates cloud-based infrastructure"},
    {"name": "IT Support",              "description": "Provides technical support, helpdesk, and network administration"},
    {"name": "Project Manager",         "description": "Plans and delivers IT projects within scope, time, and budget"},
    {"name": "Network Engineer",        "description": "Designs and maintains network infrastructure"},
    {"name": "Systems Analyst",         "description": "Analyses business requirements and translates them to IT solutions"},
    {"name": "AI/ML Engineer",          "description": "Develops and deploys machine learning and AI-powered systems"},
    {"name": "Database Administrator",  "description": "Manages database performance, security, and availability"},
    {"name": "Product Manager",         "description": "Defines product vision and roadmap; bridges business and engineering"},
    {"name": "Embedded Engineer",       "description": "Develops firmware and software for embedded hardware systems"},
    {"name": "Mobile Developer",        "description": "Builds native and cross-platform mobile applications"},
    {"name": "UX Designer",             "description": "Designs user-centred interfaces and experiences"},
    {"name": "Blockchain Developer",    "description": "Develops smart contracts and decentralised applications"},
    {"name": "AI Governance Specialist","description": "Ensures ethical, compliant, and responsible deployment of AI systems"},
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------


def run_seed() -> None:
    """Execute all seed operations against the database. Safe to rerun."""
    db = SessionLocal()
    try:
        logger.info("Seeding grade depth rules...")
        for rule_data in GRADE_DEPTH_RULES:
            existing = (
                db.query(GradeDepthRule)
                .filter(GradeDepthRule.depth_level == rule_data["depth_level"])
                .first()
            )
            if not existing:
                db.add(GradeDepthRule(**rule_data))
        db.commit()

        logger.info("Seeding %d canonical skills...", len(SKILLS))
        skill_name_to_id: dict[str, object] = {}
        for skill_data in SKILLS:
            existing = db.query(Skill).filter(Skill.name == skill_data["name"]).first()
            if not existing:
                skill = Skill(**skill_data)
                db.add(skill)
                db.flush()
                skill_name_to_id[skill.name] = skill.id
            else:
                skill_name_to_id[existing.name] = existing.id
        db.commit()

        logger.info("Seeding %d aliases...", len(ALIASES))
        for alias_data in ALIASES:
            skill_id = skill_name_to_id.get(alias_data["skill"])
            if not skill_id:
                logger.warning("Unknown skill '%s' for alias; skipping", alias_data["skill"])
                continue
            alias_lower = alias_data["alias"].lower()
            existing = db.query(SkillAlias).filter(SkillAlias.alias == alias_lower).first()
            if not existing:
                db.add(SkillAlias(alias=alias_lower, skill_id=skill_id))
        db.commit()

        logger.info("Seeding %d roles...", len(ROLES))
        for role_data in ROLES:
            existing = db.query(RoleCatalog).filter(RoleCatalog.name == role_data["name"]).first()
            if not existing:
                db.add(RoleCatalog(**role_data))
        db.commit()

        logger.info("Seeding %d course-skill mappings...", len(COURSE_SKILL_MAPS))
        for mapping_data in COURSE_SKILL_MAPS:
            skill_id = skill_name_to_id.get(mapping_data["skill"])
            if not skill_id:
                logger.warning("Unknown skill '%s'; skipping mapping", mapping_data["skill"])
                continue
            existing = (
                db.query(CourseSkillMap)
                .filter(
                    CourseSkillMap.course_code == mapping_data["course_code"],
                    CourseSkillMap.skill_id == skill_id,
                )
                .first()
            )
            if not existing:
                db.add(
                    CourseSkillMap(
                        course_code=mapping_data["course_code"],
                        skill_id=skill_id,
                        min_depth=mapping_data["min_depth"],
                    )
                )
        db.commit()

        logger.info("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
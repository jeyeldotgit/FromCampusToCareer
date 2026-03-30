"""Taxonomy seed script — required Stage 1 deliverable.

Run once against a fresh database (safe to rerun; all operations are idempotent):
    python -m modules.taxonomy_admin.seed_taxonomy

Covers:
- 50+ canonical skills for BSIT / BSCS / BSIS graduates
- Alias variants for common misspellings and abbreviations
- Course-to-skill mappings for a representative curriculum
- PH grade-to-depth rules (1.00–3.00 scale)
- Five active PH IT target roles
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

SKILLS: list[dict[str, str]] = [
    {"name": "Python", "description": "General-purpose programming language"},
    {"name": "Java", "description": "Object-oriented programming language"},
    {"name": "JavaScript", "description": "Web scripting language"},
    {"name": "TypeScript", "description": "Typed superset of JavaScript"},
    {"name": "PHP", "description": "Server-side scripting language"},
    {"name": "C++", "description": "Systems programming language"},
    {"name": "C#", "description": ".NET programming language"},
    {"name": "SQL", "description": "Relational database query language"},
    {"name": "HTML", "description": "Web markup language"},
    {"name": "CSS", "description": "Web styling language"},
    {"name": "React", "description": "JavaScript UI library"},
    {"name": "Vue.js", "description": "Progressive JavaScript framework"},
    {"name": "Angular", "description": "TypeScript-based web framework"},
    {"name": "Node.js", "description": "JavaScript runtime for backend"},
    {"name": "Laravel", "description": "PHP web framework"},
    {"name": "Django", "description": "Python web framework"},
    {"name": "FastAPI", "description": "Python async web framework"},
    {"name": "Spring Boot", "description": "Java enterprise framework"},
    {"name": "PostgreSQL", "description": "Relational database system"},
    {"name": "MySQL", "description": "Relational database system"},
    {"name": "MongoDB", "description": "NoSQL document database"},
    {"name": "Redis", "description": "In-memory data store"},
    {"name": "Git", "description": "Version control system"},
    {"name": "Docker", "description": "Containerization platform"},
    {"name": "Linux", "description": "Open-source operating system"},
    {"name": "REST API", "description": "RESTful API design"},
    {"name": "GraphQL", "description": "API query language"},
    {"name": "Machine Learning", "description": "Statistical learning from data"},
    {"name": "Data Analysis", "description": "Statistical data examination"},
    {"name": "pandas", "description": "Python data analysis library"},
    {"name": "NumPy", "description": "Python numerical computing library"},
    {"name": "Tableau", "description": "Data visualisation tool"},
    {"name": "Power BI", "description": "Microsoft business intelligence tool"},
    {"name": "Excel", "description": "Microsoft spreadsheet application"},
    {"name": "Data Structures", "description": "Algorithmic data organisation"},
    {"name": "Algorithms", "description": "Computational problem-solving methods"},
    {"name": "Object-Oriented Programming", "description": "OOP design paradigm"},
    {"name": "Agile", "description": "Iterative software development methodology"},
    {"name": "Scrum", "description": "Agile framework for team delivery"},
    {"name": "Unit Testing", "description": "Automated testing of individual units"},
    {"name": "Network Administration", "description": "Managing computer networks"},
    {"name": "Cybersecurity", "description": "Protecting digital systems"},
    {"name": "Cloud Computing", "description": "On-demand computing resources"},
    {"name": "AWS", "description": "Amazon Web Services cloud platform"},
    {"name": "Azure", "description": "Microsoft cloud platform"},
    {"name": "System Analysis", "description": "Evaluating system requirements"},
    {"name": "Database Design", "description": "Relational schema and modelling"},
    {"name": "UI/UX Design", "description": "User interface and experience design"},
    {"name": "Project Management", "description": "Planning and delivering projects"},
    {"name": "Technical Documentation", "description": "Writing system documentation"},
]

ALIASES: list[dict[str, str]] = [
    {"alias": "py", "skill": "Python"},
    {"alias": "python3", "skill": "Python"},
    {"alias": "javascript", "skill": "JavaScript"},
    {"alias": "js", "skill": "JavaScript"},
    {"alias": "reactjs", "skill": "React"},
    {"alias": "react.js", "skill": "React"},
    {"alias": "vuejs", "skill": "Vue.js"},
    {"alias": "vue", "skill": "Vue.js"},
    {"alias": "nodejs", "skill": "Node.js"},
    {"alias": "node", "skill": "Node.js"},
    {"alias": "postgres", "skill": "PostgreSQL"},
    {"alias": "postgresql", "skill": "PostgreSQL"},
    {"alias": "ms sql", "skill": "SQL"},
    {"alias": "mysql", "skill": "MySQL"},
    {"alias": "mongo", "skill": "MongoDB"},
    {"alias": "ms excel", "skill": "Excel"},
    {"alias": "microsoft excel", "skill": "Excel"},
    {"alias": "powerbi", "skill": "Power BI"},
    {"alias": "ml", "skill": "Machine Learning"},
    {"alias": "machine learning", "skill": "Machine Learning"},
    {"alias": "oop", "skill": "Object-Oriented Programming"},
    {"alias": "rest", "skill": "REST API"},
    {"alias": "restful api", "skill": "REST API"},
    {"alias": "git version control", "skill": "Git"},
    {"alias": "docker container", "skill": "Docker"},
    {"alias": "amazon web services", "skill": "AWS"},
    {"alias": "microsoft azure", "skill": "Azure"},
    {"alias": "scrum methodology", "skill": "Scrum"},
    {"alias": "agile methodology", "skill": "Agile"},
    {"alias": "dsa", "skill": "Data Structures"},
    {"alias": "data structures and algorithms", "skill": "Algorithms"},
]

# course_code -> list of (skill_name, min_depth)
COURSE_SKILL_MAPS: list[dict[str, str]] = [
    {"course_code": "CC101", "skill": "Python", "min_depth": "Foundational"},
    {"course_code": "CC101", "skill": "Data Structures", "min_depth": "Foundational"},
    {"course_code": "CC102", "skill": "Java", "min_depth": "Intermediate"},
    {"course_code": "CC102", "skill": "Object-Oriented Programming", "min_depth": "Intermediate"},
    {"course_code": "CC103", "skill": "Data Structures", "min_depth": "Intermediate"},
    {"course_code": "CC103", "skill": "Algorithms", "min_depth": "Intermediate"},
    {"course_code": "CC104", "skill": "SQL", "min_depth": "Intermediate"},
    {"course_code": "CC104", "skill": "Database Design", "min_depth": "Intermediate"},
    {"course_code": "CC105", "skill": "HTML", "min_depth": "Proficient"},
    {"course_code": "CC105", "skill": "CSS", "min_depth": "Proficient"},
    {"course_code": "CC105", "skill": "JavaScript", "min_depth": "Foundational"},
    {"course_code": "CC106", "skill": "Python", "min_depth": "Proficient"},
    {"course_code": "CC106", "skill": "pandas", "min_depth": "Intermediate"},
    {"course_code": "CC106", "skill": "NumPy", "min_depth": "Intermediate"},
    {"course_code": "CC107", "skill": "Machine Learning", "min_depth": "Foundational"},
    {"course_code": "CC107", "skill": "Data Analysis", "min_depth": "Intermediate"},
    {"course_code": "CC108", "skill": "Network Administration", "min_depth": "Intermediate"},
    {"course_code": "CC108", "skill": "Linux", "min_depth": "Foundational"},
    {"course_code": "CC109", "skill": "Cybersecurity", "min_depth": "Foundational"},
    {"course_code": "CC110", "skill": "Project Management", "min_depth": "Foundational"},
    {"course_code": "CC110", "skill": "Agile", "min_depth": "Foundational"},
    {"course_code": "CC111", "skill": "System Analysis", "min_depth": "Intermediate"},
    {"course_code": "CC112", "skill": "React", "min_depth": "Intermediate"},
    {"course_code": "CC112", "skill": "Node.js", "min_depth": "Foundational"},
    {"course_code": "CC113", "skill": "Cloud Computing", "min_depth": "Foundational"},
    {"course_code": "CC113", "skill": "AWS", "min_depth": "Foundational"},
    {"course_code": "CC114", "skill": "Unit Testing", "min_depth": "Intermediate"},
    {"course_code": "CC114", "skill": "Git", "min_depth": "Proficient"},
    {"course_code": "CC115", "skill": "Docker", "min_depth": "Foundational"},
    {"course_code": "CC116", "skill": "Technical Documentation", "min_depth": "Proficient"},
    {"course_code": "CC117", "skill": "UI/UX Design", "min_depth": "Foundational"},
    {"course_code": "CC118", "skill": "PHP", "min_depth": "Intermediate"},
    {"course_code": "CC118", "skill": "Laravel", "min_depth": "Foundational"},
    {"course_code": "CC119", "skill": "Excel", "min_depth": "Intermediate"},
    {"course_code": "CC120", "skill": "PostgreSQL", "min_depth": "Intermediate"},
]

GRADE_DEPTH_RULES: list[dict] = [
    {"min_grade": "1.00", "max_grade": "1.50", "depth_level": "Advanced"},
    {"min_grade": "1.51", "max_grade": "2.00", "depth_level": "Proficient"},
    {"min_grade": "2.01", "max_grade": "2.75", "depth_level": "Intermediate"},
    {"min_grade": "2.76", "max_grade": "3.00", "depth_level": "Foundational"},
]

ROLES: list[dict[str, str]] = [
    {
        "name": "Web Developer",
        "description": "Builds and maintains web applications",
    },
    {
        "name": "Data Analyst",
        "description": "Analyses data to support business decisions",
    },
    {
        "name": "Software Engineer",
        "description": "Designs and develops software systems",
    },
    {
        "name": "QA Engineer",
        "description": "Ensures software quality through testing",
    },
    {
        "name": "IT Support Specialist",
        "description": "Provides technical support and network administration",
    },
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

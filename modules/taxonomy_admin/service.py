from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from modules.taxonomy_admin.models import (
    CourseSkillMap,
    GradeDepthRule,
    RoleCatalog,
    Skill,
    SkillAlias,
)
from modules.taxonomy_admin.schemas import (
    AliasCreate,
    CourseMappingCreate,
    GradeDepthRuleCreate,
    RoleCreate,
    SkillCreate,
)

logger = logging.getLogger(__name__)


def create_skill(payload: SkillCreate, db: Session) -> Skill:
    """Upsert a canonical skill by name (idempotent).

    Args:
        payload: Skill name and optional description.
        db: Active database session.

    Returns:
        Existing or newly created Skill instance.
    """
    existing = db.query(Skill).filter(Skill.name == payload.name).first()
    if existing:
        return existing
    skill = Skill(name=payload.name, description=payload.description)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    logger.info("Skill created", extra={"skill_id": str(skill.id), "name": skill.name})
    return skill


def list_skills(db: Session) -> list[Skill]:
    return db.query(Skill).order_by(Skill.name).all()


def create_alias(payload: AliasCreate, db: Session) -> SkillAlias:
    """Upsert a skill alias mapping (idempotent by alias string).

    Args:
        payload: Alias string and target skill_id.
        db: Active database session.

    Returns:
        Existing or newly created SkillAlias instance.
    """
    existing = (
        db.query(SkillAlias).filter(SkillAlias.alias == payload.alias.lower()).first()
    )
    if existing:
        return existing
    alias = SkillAlias(alias=payload.alias.lower(), skill_id=payload.skill_id)
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


def build_alias_map(db: Session) -> dict[str, uuid.UUID]:
    """Return a lowercase alias -> skill_id lookup dict for the normalization pipeline.

    Includes both canonical skill names (as their own alias) and all explicit
    alias variants, so the PhraseMatcher's canonical-name labels resolve to UUIDs
    even when no explicit alias has been seeded.

    Explicit aliases take precedence over canonical names if there is ever a collision
    (which should not occur in practice).

    Args:
        db: Active database session.

    Returns:
        Dictionary mapping lowercase alias strings to canonical skill UUIDs.
    """
    # Seed with canonical names so the PhraseMatcher's match labels always resolve.
    alias_map: dict[str, uuid.UUID] = {
        skill.name.lower(): skill.id for skill in db.query(Skill).all()
    }
    # Overlay explicit aliases (allows variant spellings to map to the same skill).
    for row in db.query(SkillAlias).all():
        alias_map[row.alias.lower()] = row.skill_id
    return alias_map


def create_role(payload: RoleCreate, db: Session) -> RoleCatalog:
    """Upsert a role catalog entry by name (idempotent).

    Args:
        payload: Role name and optional description.
        db: Active database session.

    Returns:
        Existing or newly created RoleCatalog instance.
    """
    existing = db.query(RoleCatalog).filter(RoleCatalog.name == payload.name).first()
    if existing:
        return existing
    role = RoleCatalog(name=payload.name, description=payload.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def list_roles(db: Session) -> list[RoleCatalog]:
    return db.query(RoleCatalog).filter(RoleCatalog.is_active.is_(True)).all()


def create_course_mapping(payload: CourseMappingCreate, db: Session) -> CourseSkillMap:
    """Upsert a course-to-skill mapping (idempotent by course_code + skill_id).

    Args:
        payload: Course code, target skill_id, and minimum required depth.
        db: Active database session.

    Returns:
        Existing or newly created CourseSkillMap instance.
    """
    existing = (
        db.query(CourseSkillMap)
        .filter(
            CourseSkillMap.course_code == payload.course_code,
            CourseSkillMap.skill_id == payload.skill_id,
        )
        .first()
    )
    if existing:
        return existing
    mapping = CourseSkillMap(
        course_code=payload.course_code,
        skill_id=payload.skill_id,
        min_depth=payload.min_depth,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def upsert_grade_depth_rule(payload: GradeDepthRuleCreate, db: Session) -> GradeDepthRule:
    """Upsert a grade-to-depth rule (idempotent by depth_level).

    Args:
        payload: Grade range and corresponding depth label.
        db: Active database session.

    Returns:
        Existing or newly created GradeDepthRule instance.
    """
    existing = (
        db.query(GradeDepthRule)
        .filter(GradeDepthRule.depth_level == payload.depth_level)
        .first()
    )
    if existing:
        existing.min_grade = payload.min_grade
        existing.max_grade = payload.max_grade
        db.commit()
        db.refresh(existing)
        return existing
    rule = GradeDepthRule(
        min_grade=payload.min_grade,
        max_grade=payload.max_grade,
        depth_level=payload.depth_level,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def grade_to_depth(grade: float, db: Session) -> str | None:
    """Convert a PH numeric grade to a depth label using stored rules.

    Args:
        grade: Numeric grade value (e.g. 1.75).
        db: Active database session.

    Returns:
        Depth label string or None if no rule matches (e.g. grade > 3.00).
    """
    rules = db.query(GradeDepthRule).all()
    for rule in rules:
        if float(rule.min_grade) <= grade <= float(rule.max_grade):
            return rule.depth_level
    return None

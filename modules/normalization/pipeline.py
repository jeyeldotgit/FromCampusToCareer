"""Normalization pipeline orchestrator.

Reads job_postings_unified rows that have no posting_skills entries yet,
extracts and normalizes skills, and upserts posting_skills associations.
This pipeline is idempotent: re-running only processes unprocessed postings.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from modules.normalization.extractor import PhraseMatcher, build_matcher, extract_skills
from modules.normalization.models import PostingSkill
from modules.normalization.normalizer import normalize_skill_set
from modules.taxonomy_admin.models import Skill, SkillAlias
from modules.taxonomy_admin.service import build_alias_map

logger = logging.getLogger(__name__)


def _build_skill_patterns(db: Session) -> dict[str, str]:
    """Build a {lowercase_pattern: canonical_name} dict for PhraseMatcher.

    Includes both canonical skill names and all their alias variants.

    Args:
        db: Active database session.

    Returns:
        Mapping of lowercase skill/alias strings to canonical skill names.
    """
    patterns: dict[str, str] = {}
    skills = db.query(Skill).all()
    for skill in skills:
        patterns[skill.name.lower()] = skill.name

    aliases = db.query(SkillAlias).join(Skill).all()
    for alias in aliases:
        patterns[alias.alias.lower()] = alias.skill.name

    return patterns


def run_normalization(db: Session) -> dict[str, int]:
    """Extract and store skill associations for all unprocessed job postings.

    A posting is considered unprocessed if it has zero rows in posting_skills.
    Processed postings are skipped to ensure idempotency without comparing
    full content.

    Args:
        db: Active database session.

    Returns:
        Dictionary with keys 'processed', 'skills_extracted', 'unknown_flagged'.
    """
    alias_map: dict[str, uuid.UUID] = build_alias_map(db)
    skill_patterns = _build_skill_patterns(db)

    if not skill_patterns:
        logger.warning("No skill patterns available; taxonomy may not be seeded")
        return {"processed": 0, "skills_extracted": 0, "unknown_flagged": 0}

    import spacy as _spacy  # local import to defer loading until needed

    nlp, matcher = build_matcher(skill_patterns)

    # Find postings not yet in posting_skills; read skills column for richer extraction
    unprocessed_sql = text("""
        SELECT jp.posting_id, jp.title, COALESCE(jp.skills, '') AS skills_text
        FROM job_postings_unified jp
        WHERE NOT EXISTS (
            SELECT 1 FROM posting_skills ps WHERE ps.posting_id = jp.posting_id
        )
    """)
    rows = db.execute(unprocessed_sql).fetchall()

    processed = 0
    total_skills = 0
    total_unknown = 0

    for row in rows:
        posting_id: str = row[0]
        title: str = row[1]
        skills_text: str = row[2]

        # Combine title and pre-tagged skills for maximum coverage.
        # The skills column contains comma-separated keywords (e.g. "Python, Docker")
        # from the source dataset; combining with the title catches both sources.
        combined_text = f"{title} {skills_text}".strip()
        raw_skills = extract_skills(combined_text, nlp, matcher)
        resolved_ids, unknown = normalize_skill_set(raw_skills, alias_map)

        total_unknown += len(unknown)

        for skill_id in resolved_ids:
            stmt = (
                insert(PostingSkill)
                .values(posting_id=posting_id, skill_id=skill_id)
                .on_conflict_do_nothing()
            )
            db.execute(stmt)
            total_skills += 1

        processed += 1
        if processed % 1000 == 0:
            db.commit()
            logger.info("Normalization progress: %d postings processed", processed)

    db.commit()
    logger.info(
        "Normalization complete",
        extra={
            "processed": processed,
            "skills_extracted": total_skills,
            "unknown_flagged": total_unknown,
        },
    )
    return {
        "processed": processed,
        "skills_extracted": total_skills,
        "unknown_flagged": total_unknown,
    }

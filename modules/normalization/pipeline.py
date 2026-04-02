"""Normalization pipeline orchestrator.

Reads job_postings_unified rows that have no posting_skills entries yet,
extracts and normalizes skills, and upserts posting_skills associations.
This pipeline is idempotent: re-running only processes unprocessed postings.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from modules.normalization.extractor import PhraseMatcher, build_matcher, extract_skills_from_doc
from modules.normalization.models import PostingSkill
from modules.normalization.normalizer import normalize_skill_set
from modules.taxonomy_admin.models import Skill, SkillAlias
from modules.taxonomy_admin.service import build_alias_map

logger = logging.getLogger(__name__)

CHUNK_SIZE = 2000
BULK_INSERT_SIZE = 1000

_UNPROCESSED_IDS_SQL = text("""
    SELECT jp.posting_id
    FROM job_postings_unified jp
    WHERE NOT EXISTS (
        SELECT 1 FROM posting_skills ps WHERE ps.posting_id = jp.posting_id
    )
""")

_CHUNK_ROWS_SQL = text("""
    SELECT jp.posting_id, jp.title, COALESCE(jp.skills, '') AS skills_text
    FROM job_postings_unified jp
    WHERE jp.posting_id IN :ids
""").bindparams(bindparam("ids", expanding=True))


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


def _iter_chunks(items: list, size: int):
    """Yield successive fixed-size slices of a list.

    Args:
        items: Source list to slice.
        size: Maximum length of each yielded slice.

    Yields:
        Sublists of at most ``size`` elements.
    """
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _bulk_insert_posting_skills(db: Session, rows: list[dict]) -> None:
    """Execute a bulk upsert of posting_skills rows.

    Caller is responsible for committing the transaction. This function
    only executes the statement — it never calls db.commit().

    Args:
        db: Active database session.
        rows: List of dicts with keys 'posting_id' and 'skill_id'.
    """
    if not rows:
        return
    stmt = insert(PostingSkill).values(rows).on_conflict_do_nothing()
    db.execute(stmt)


def run_normalization(db: Session) -> dict[str, int]:
    """Extract and store skill associations for all unprocessed job postings.

    A posting is considered unprocessed if it has zero rows in posting_skills.
    Processed postings are skipped to ensure idempotency without comparing
    full content.

    Rows are fetched in two steps to avoid LIMIT/OFFSET correctness issues
    on a live-write table:
      1. Fetch all unprocessed posting_ids upfront (cheap, IDs only).
      2. Chunk those IDs in Python and fetch full rows per chunk.

    NLP is batched with nlp.pipe() per chunk (5–10x faster than per-row calls).
    DB writes are bulk-inserted per BULK_INSERT_SIZE accumulation.

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

    nlp, matcher = build_matcher(skill_patterns)

    # Step 1: collect all unprocessed posting_ids into memory (IDs only — cheap).
    # Using a fixed list avoids the shifting-offset bug that occurs when LIMIT/OFFSET
    # pagination is combined with live writes to posting_skills.
    unprocessed_ids: list[str] = [
        row[0] for row in db.execute(_UNPROCESSED_IDS_SQL).fetchall()
    ]

    if not unprocessed_ids:
        logger.info("Normalization: no unprocessed postings found")
        return {"processed": 0, "skills_extracted": 0, "unknown_flagged": 0}

    logger.info("Normalization: %d unprocessed postings to process", len(unprocessed_ids))

    processed = 0
    total_skills = 0
    total_unknown = 0
    skill_rows: list[dict] = []

    # Step 2: process in fixed chunks — fetch full rows, batch NLP, bulk insert.
    for chunk_ids in _iter_chunks(unprocessed_ids, CHUNK_SIZE):
        chunk_rows = db.execute(_CHUNK_ROWS_SQL, {"ids": chunk_ids}).fetchall()

        texts = [f"{row[1]} {row[2]}".strip() for row in chunk_rows]
        docs = list(nlp.pipe(texts, batch_size=512))

        for row, doc in zip(chunk_rows, docs):
            posting_id: str = row[0]
            raw_skills = extract_skills_from_doc(doc, matcher)
            resolved_ids, unknown = normalize_skill_set(raw_skills, alias_map)

            total_unknown += len(unknown)

            for skill_id in resolved_ids:
                skill_rows.append({"posting_id": posting_id, "skill_id": skill_id})
                total_skills += 1

            if len(skill_rows) >= BULK_INSERT_SIZE:
                _bulk_insert_posting_skills(db, skill_rows)
                skill_rows.clear()

            processed += 1

        # Commit once per chunk, not per row or per skill.
        db.commit()
        logger.info(
            "Normalization progress: %d / %d postings processed",
            processed,
            len(unprocessed_ids),
        )

    # Flush any remaining skill rows that didn't reach BULK_INSERT_SIZE.
    if skill_rows:
        _bulk_insert_posting_skills(db, skill_rows)
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

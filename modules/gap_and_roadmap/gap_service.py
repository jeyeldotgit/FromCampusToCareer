"""Gap analysis computation.

Implements set-difference + depth-level comparison logic from
intelligence-system-documentation.md §5.2.

Priority bands (by weighted SDI):
    >= 0.70  → critical
    >= 0.40  → important
    <  0.40  → emerging

Depth ordering (highest to lowest):
    Advanced > Proficient > Intermediate > Foundational

Gap types:
    missing   — skill absent from student inventory
    depth_gap — skill present but student depth < market-required depth
    no_gap    — student depth >= required depth (not returned to the student)

This module does NOT import from roadmap_service. The router assembles both.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from modules.gap_and_roadmap.models import GapResult, ReadinessHistory
from modules.gap_and_roadmap.schemas import GapItem
from modules.taxonomy_admin.service import grade_to_depth

logger = logging.getLogger(__name__)

DEPTH_ORDER = ["Foundational", "Intermediate", "Proficient", "Advanced"]

SDI_BANDS = [
    (0.70, "critical"),
    (0.40, "important"),
    (0.00, "emerging"),
]


def _classify_priority(sdi_value: float) -> str:
    for threshold, band in SDI_BANDS:
        if sdi_value >= threshold:
            return band
    return "emerging"


def _depth_rank(depth: str | None) -> int:
    if depth is None:
        return -1
    try:
        return DEPTH_ORDER.index(depth)
    except ValueError:
        return -1


def _derive_student_skill_depths(
    student_id: uuid.UUID, db: Session
) -> dict[uuid.UUID, str]:
    """Compute the student's depth per skill from their course records.

    Uses the best grade across all courses that map to a given skill.

    Args:
        student_id: UUID of the StudentProfile.
        db: Active database session.

    Returns:
        Mapping of skill_id to depth label.
    """
    rows = db.execute(
        text("""
            SELECT csm.skill_id, MIN(CAST(cr.grade AS FLOAT)) AS best_grade
            FROM course_records cr
            JOIN course_skill_map csm ON csm.course_code = cr.course_code
            WHERE cr.student_id = :student_id
            GROUP BY csm.skill_id
        """),
        {"student_id": str(student_id)},
    ).fetchall()

    depth_map: dict[uuid.UUID, str] = {}
    for row in rows:
        depth = grade_to_depth(float(row[1]), db)
        if depth:
            depth_map[uuid.UUID(str(row[0]))] = depth
    return depth_map


def _load_course_skill_requirements(
    role_id: uuid.UUID, db: Session
) -> dict[uuid.UUID, str]:
    """Load market-required depth per skill for the given role.

    Uses course_skill_map as a proxy for market depth requirements in MVP.
    In production this would also incorporate SDI-derived thresholds.

    Args:
        role_id: UUID of the target role.
        db: Active database session.

    Returns:
        Mapping of skill_id to minimum required depth label.
    """
    rows = db.execute(
        text("""
            SELECT DISTINCT csm.skill_id, csm.min_depth
            FROM course_skill_map csm
        """)
    ).fetchall()
    return {uuid.UUID(str(r[0])): str(r[1]) for r in rows}


def compute_gap_analysis(
    student_id: uuid.UUID,
    role_id: uuid.UUID,
    weighted_sdi: dict[uuid.UUID, float],
    db: Session,
) -> tuple[list[GapItem], float]:
    """Compute gap analysis and readiness score for a student/role pair.

    Persists gap results to the gap_results table, replacing previous results
    for the same student/role pair.

    Args:
        student_id: UUID of the StudentProfile.
        role_id: UUID of the target role.
        weighted_sdi: Precomputed recency-weighted SDI map (skill_id -> float).
        db: Active database session.

    Returns:
        Tuple of (list of GapItem, readiness_score_float 0.0-100.0).
    """
    student_depths = _derive_student_skill_depths(student_id, db)
    required_depths = _load_course_skill_requirements(role_id, db)

    # Load skill names for response
    skill_names: dict[uuid.UUID, str] = {}
    rows = db.execute(text("SELECT id, name FROM skills")).fetchall()
    for row in rows:
        skill_names[uuid.UUID(str(row[0]))] = str(row[1])

    # Skills the market cares about for this role (those with SDI data)
    relevant_skills = set(weighted_sdi.keys())

    gap_items: list[GapItem] = []
    total_weighted = 0.0
    met_weighted = 0.0

    # Delete previous gap results for this student/role before reinserting
    db.execute(
        text(
            "DELETE FROM gap_results WHERE student_id = :sid AND role_id = :rid"
        ),
        {"sid": str(student_id), "rid": str(role_id)},
    )

    for skill_id in relevant_skills:
        sdi_val = weighted_sdi.get(skill_id, 0.0)
        student_depth = student_depths.get(skill_id)
        required_depth = required_depths.get(skill_id)
        priority_band = _classify_priority(sdi_val)
        total_weighted += sdi_val

        if student_depth is None:
            gap_type = "missing"
        elif _depth_rank(student_depth) < _depth_rank(required_depth):
            gap_type = "depth_gap"
        else:
            gap_type = "no_gap"
            met_weighted += sdi_val

        db.add(
            GapResult(
                student_id=student_id,
                role_id=role_id,
                skill_id=skill_id,
                gap_type=gap_type,
                priority_band=priority_band,
                sdi_value=sdi_val,
                student_depth=student_depth,
                required_depth=required_depth,
            )
        )

        if gap_type != "no_gap":
            gap_items.append(
                GapItem(
                    skill_id=skill_id,
                    skill_name=skill_names.get(skill_id, str(skill_id)),
                    gap_type=gap_type,
                    priority_band=priority_band,
                    sdi_value=sdi_val,
                    student_depth=student_depth,
                    required_depth=required_depth,
                )
            )

    db.commit()
    readiness = round((met_weighted / total_weighted) * 100, 2) if total_weighted else 0.0
    gap_items.sort(key=lambda g: g.sdi_value, reverse=True)

    logger.info(
        "Gap analysis complete",
        extra={
            "student_id": str(student_id),
            "role_id": str(role_id),
            "readiness": readiness,
            "gaps": len(gap_items),
        },
    )
    return gap_items, readiness

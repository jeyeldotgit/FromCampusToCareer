"""SDI computation pipeline.

Implements the Skill Demand Index formula from intelligence-system-documentation.md §4.1:

    SDI(skill, role, t) = count(entry-level postings for role at t mentioning skill)
                          / count(total entry-level postings for role at t)

Recency-weighted SDI (for gap analysis ranking):

    SDI_weighted = sum(SDI(t) * decay_factor^(N - t_index)) / sum(decay_factor^(N - t_index))

Results are upserted (not appended), so reruns produce stable snapshot counts.
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from modules.analytics_sdi.models import SdiSnapshot

logger = logging.getLogger(__name__)

ENTRY_LEVEL_SENIORITY = "entry_level"
DEFAULT_DECAY_FACTOR = 0.90


def _load_posting_skill_df(db: Session, country_filter: str | None = None) -> pd.DataFrame:
    """Load entry-level posting/skill/role/period data into a DataFrame.

    Args:
        db: Active database session.
        country_filter: If provided, restrict to postings with this country value
            (e.g. 'PH'). If None, all countries are included (global scope).

    Returns:
        DataFrame with columns: posting_id, role_normalized, posted_date, skill_id.
    """
    if country_filter:
        sql = text("""
            SELECT
                jp.posting_id,
                jp.role_normalized,
                jp.posted_date,
                ps.skill_id::text AS skill_id
            FROM job_postings_unified jp
            JOIN posting_skills ps ON ps.posting_id = jp.posting_id
            WHERE jp.country = :country
              AND jp.seniority = :seniority
        """)
        rows = db.execute(sql, {"country": country_filter, "seniority": ENTRY_LEVEL_SENIORITY}).fetchall()
    else:
        sql = text("""
            SELECT
                jp.posting_id,
                jp.role_normalized,
                jp.posted_date,
                ps.skill_id::text AS skill_id
            FROM job_postings_unified jp
            JOIN posting_skills ps ON ps.posting_id = jp.posting_id
            WHERE jp.seniority = :seniority
        """)
        rows = db.execute(sql, {"seniority": ENTRY_LEVEL_SENIORITY}).fetchall()

    return pd.DataFrame(rows, columns=["posting_id", "role_normalized", "posted_date", "skill_id"])


def _load_role_id_map(db: Session) -> dict[str, uuid.UUID]:
    """Return a role_name -> role_id mapping from the database.

    Args:
        db: Active database session.

    Returns:
        Dictionary mapping role name strings to UUIDs.
    """
    rows = db.execute(text("SELECT id, name FROM role_catalog")).fetchall()
    return {row[1]: uuid.UUID(str(row[0])) for row in rows}


def _load_skill_id_map(db: Session) -> dict[str, uuid.UUID]:
    """Return a skill_name -> skill_id mapping from the database.

    Args:
        db: Active database session.

    Returns:
        Dictionary mapping skill name strings to UUIDs.
    """
    rows = db.execute(text("SELECT id, name FROM skills")).fetchall()
    return {row[1]: uuid.UUID(str(row[0])) for row in rows}


def compute_sdi_snapshots(
    df: pd.DataFrame,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
) -> pd.DataFrame:
    """Compute per-period SDI values for every (skill, role, period) triple.

    Args:
        df: DataFrame with columns posting_id, role_normalized, posted_date, skill_id.
        decay_factor: Exponential recency weight (default 0.90).

    Returns:
        DataFrame with columns: role_normalized, posted_date, skill_id, sdi_value, posting_count.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["role_normalized", "posted_date", "skill_id", "sdi_value", "posting_count"]
        )

    total_per_role_period = (
        df.drop_duplicates(subset=["posting_id", "role_normalized", "posted_date"])
        .groupby(["role_normalized", "posted_date"])["posting_id"]
        .nunique()
        .reset_index()
        .rename(columns={"posting_id": "total_postings"})
    )

    skill_per_role_period = (
        df.groupby(["role_normalized", "posted_date", "skill_id"])["posting_id"]
        .nunique()
        .reset_index()
        .rename(columns={"posting_id": "skill_count"})
    )

    merged = skill_per_role_period.merge(total_per_role_period, on=["role_normalized", "posted_date"])
    merged["sdi_value"] = (merged["skill_count"] / merged["total_postings"]).round(4)
    merged = merged.rename(columns={"skill_count": "posting_count"})

    return merged[["role_normalized", "posted_date", "skill_id", "sdi_value", "posting_count"]]


def run_sdi_refresh(
    db: Session,
    scope: str,
    country_filter: str | None = None,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
) -> int:
    """Compute and upsert SDI snapshots for all skill/role/period triples.

    Uses ON CONFLICT DO UPDATE so rows are upserted, not appended, making this
    safe to rerun without corrupting counts.

    Args:
        db: Active database session.
        scope: Snapshot scope label stored in sdi_snapshots ('ph' or 'global').
        country_filter: If provided, restrict source postings to this country
            (e.g. 'PH'). If None, all countries are included.
        decay_factor: Recency decay weight passed to snapshot computation.

    Returns:
        Number of snapshots upserted.
    """
    role_map = _load_role_id_map(db)
    skill_id_to_uuid: dict[str, uuid.UUID] = {}
    rows = db.execute(text("SELECT id FROM skills")).fetchall()
    for row in rows:
        skill_id_to_uuid[str(row[0])] = uuid.UUID(str(row[0]))

    df = _load_posting_skill_df(db, country_filter=country_filter)
    if df.empty:
        logger.warning(
            "No entry-level posting-skill data found for scope=%s country_filter=%s; SDI skipped",
            scope,
            country_filter,
        )
        return 0

    snapshot_df = compute_sdi_snapshots(df, decay_factor)
    upserted = 0

    for _, snap_row in snapshot_df.iterrows():
        role_id = role_map.get(snap_row["role_normalized"])
        if not role_id:
            continue

        skill_uuid_str = str(snap_row["skill_id"])
        skill_uuid = skill_id_to_uuid.get(skill_uuid_str)
        if not skill_uuid:
            continue

        sdi_val = Decimal(str(round(float(snap_row["sdi_value"]), 4)))
        stmt = (
            insert(SdiSnapshot)
            .values(
                id=uuid.uuid4(),
                skill_id=skill_uuid,
                role_id=role_id,
                period=str(snap_row["posted_date"]),
                sdi_value=sdi_val,
                posting_count=int(snap_row["posting_count"]),
                scope=scope,
            )
            .on_conflict_do_update(
                constraint="uq_sdi_snapshot",
                set_={
                    "sdi_value": sdi_val,
                    "posting_count": int(snap_row["posting_count"]),
                },
            )
        )
        db.execute(stmt)
        upserted += 1

    db.commit()
    logger.info("SDI refresh complete", extra={"scope": scope, "upserted": upserted})
    return upserted


def run_ph_sdi_refresh(db: Session, decay_factor: float = DEFAULT_DECAY_FACTOR) -> int:
    """Backward-compatible shim — calls run_sdi_refresh with scope='ph'.

    Args:
        db: Active database session.
        decay_factor: Recency decay weight.

    Returns:
        Number of PH snapshots upserted.
    """
    return run_sdi_refresh(db, scope="ph", country_filter="PH", decay_factor=decay_factor)


def get_weighted_sdi(
    role_id: uuid.UUID,
    db: Session,
    scope: str = "ph",
    decay_factor: float = DEFAULT_DECAY_FACTOR,
) -> dict[uuid.UUID, float]:
    """Return recency-weighted SDI values for all skills in the given role.

    Implements the weighted formula from the intelligence documentation:
        SDI_weighted = sum(SDI(t) * decay^(N-t_index)) / sum(decay^(N-t_index))

    Args:
        role_id: UUID of the target role.
        db: Active database session.
        scope: 'ph' for student-facing gap analysis.
        decay_factor: Exponential recency weight.

    Returns:
        Dictionary mapping skill_id UUID to weighted SDI float value.
    """
    rows = db.execute(
        text("""
            SELECT skill_id, period, sdi_value
            FROM sdi_snapshots
            WHERE role_id = :role_id AND scope = :scope
            ORDER BY period ASC
        """),
        {"role_id": str(role_id), "scope": scope},
    ).fetchall()

    if not rows:
        return {}

    skill_series: dict[str, list[tuple[int, float]]] = {}
    periods_all: list[str] = sorted({str(r[1]) for r in rows})
    period_index = {p: i + 1 for i, p in enumerate(periods_all)}
    n = len(periods_all)

    for row in rows:
        sid = str(row[0])
        t_idx = period_index[str(row[1])]
        sdi_val = float(row[2])
        skill_series.setdefault(sid, []).append((t_idx, sdi_val))

    weights = {p: decay_factor ** (n - idx) for p, idx in period_index.items()}
    weight_sum = sum(weights.values())

    result: dict[uuid.UUID, float] = {}
    for sid, series in skill_series.items():
        weighted_sum = sum(
            sdi * decay_factor ** (n - t_idx) for t_idx, sdi in series
        )
        result[uuid.UUID(sid)] = round(weighted_sum / weight_sum, 4) if weight_sum else 0.0

    return result

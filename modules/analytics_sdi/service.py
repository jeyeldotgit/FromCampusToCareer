"""SDI computation pipeline.

Implements the Skill Demand Index formula from intelligence-system-documentation.md §4.1:

    SDI(skill, role, t) = count(entry-level postings for role at t mentioning skill)
                          / count(total entry-level postings for role at t)

Recency-weighted SDI (for gap analysis ranking):

    SDI_weighted = sum(SDI(t) * decay_factor^(N - t_index)) / sum(decay_factor^(N - t_index))

Write path uses a single SQL INSERT...SELECT (ELT) for performance.
compute_sdi_snapshots is kept as the Python formula reference for unit testing.
See docs/plans/PIPELINE-analytics_sdi.md for the cross-reference rule.

Results are upserted (not appended), so reruns produce stable snapshot counts.
"""

from __future__ import annotations

import logging
import uuid

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENTRY_LEVEL_SENIORITY = "entry_level"
DEFAULT_DECAY_FACTOR = 0.90
VALID_SCOPES: frozenset[str] = frozenset({"ph", "global"})

_SDI_UPSERT_SQL = text("""
    INSERT INTO sdi_snapshots
        (id, skill_id, role_id, period, sdi_value, posting_count, scope)
    SELECT
        gen_random_uuid(),
        ps.skill_id,
        rc.id                                             AS role_id,
        jp.posted_date                                    AS period,
        ROUND(
            COUNT(DISTINCT ps.posting_id)::numeric /
            NULLIF(totals.total_postings, 0),
            4
        )                                                 AS sdi_value,
        COUNT(DISTINCT ps.posting_id)                     AS posting_count,
        :scope                                            AS scope
    FROM job_postings_unified jp
    JOIN posting_skills ps  ON ps.posting_id    = jp.posting_id
    JOIN role_catalog   rc  ON rc.name          = jp.role_normalized
    JOIN (
        SELECT role_normalized, posted_date,
               COUNT(DISTINCT posting_id) AS total_postings
        FROM   job_postings_unified
        WHERE  seniority = 'entry_level'
          AND  (:country IS NULL OR country = :country)
        GROUP  BY role_normalized, posted_date
    ) totals ON totals.role_normalized = jp.role_normalized
            AND totals.posted_date     = jp.posted_date
    WHERE jp.seniority = 'entry_level'
      AND (:country IS NULL OR jp.country = :country)
    GROUP BY ps.skill_id, rc.id, jp.posted_date, totals.total_postings
    ON CONFLICT ON CONSTRAINT uq_sdi_snapshot
    DO UPDATE SET
        sdi_value     = EXCLUDED.sdi_value,
        posting_count = EXCLUDED.posting_count,
        computed_at   = now()
""")

_UNMATCHED_ROLES_SQL = text("""
    SELECT jp.role_normalized, COUNT(DISTINCT jp.posting_id) AS posting_count
    FROM   job_postings_unified jp
    WHERE  jp.seniority = 'entry_level'
      AND  (:country IS NULL OR jp.country = :country)
      AND  NOT EXISTS (
               SELECT 1 FROM role_catalog rc WHERE rc.name = jp.role_normalized
           )
    GROUP  BY jp.role_normalized
    ORDER  BY posting_count DESC
""")


def _log_unmatched_roles(
    db: Session,
    country_filter: str | None,
    scope: str,
) -> None:
    """Log role_normalized values in job_postings_unified with no role_catalog match.

    Runs as a read-only diagnostic after the upsert commits. Does not affect
    pipeline execution. Admin should review WARNING entries to expand role mappings.

    Args:
        db: Active database session.
        country_filter: Same country filter used by the preceding upsert.
        scope: Scope label for context in log messages.
    """
    rows = db.execute(_UNMATCHED_ROLES_SQL, {"country": country_filter}).fetchall()
    for role_name, count in rows:
        logger.warning(
            "Unmatched role_normalized excluded from SDI snapshots",
            extra={"scope": scope, "role_normalized": role_name, "posting_count": count},
        )


def compute_sdi_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    """Formula reference implementation of the per-period SDI computation.

    This function is the authoritative Python specification of the SDI formula.
    It is NOT called by the production write path (run_sdi_refresh uses SQL).
    It exists solely for unit testing and formula auditability.

    IMPORTANT: If you change the formula here you must also update the SQL in
    run_sdi_refresh, and vice versa.
    See docs/plans/PIPELINE-analytics_sdi.md for the cross-reference rule.

    Args:
        df: DataFrame with columns posting_id, role_normalized, posted_date, skill_id.

    Returns:
        DataFrame with columns: role_normalized, posted_date, skill_id, sdi_value,
        posting_count.
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
) -> int:
    """Compute and upsert SDI snapshots for all skill/role/period triples.

    Uses a single SQL INSERT...SELECT...ON CONFLICT DO UPDATE (ELT pattern).
    This replaces the previous N+1 Python upsert loop, cutting wall time from
    minutes to seconds on large datasets.

    Idempotent: rerunning upserts existing rows rather than appending duplicates.
    computed_at is explicitly refreshed in the DO UPDATE SET clause because
    SQLAlchemy ORM onupdate hooks do not fire for raw SQL execution.

    Args:
        db: Active database session.
        scope: Snapshot scope label ('ph' or 'global'). Raises ValueError on
            unknown values.
        country_filter: If provided, restrict source postings to this country
            (e.g. 'PH'). Pass None to include all countries.

    Returns:
        Number of snapshots inserted or updated.

    Raises:
        ValueError: If scope is not a recognised value in VALID_SCOPES.
    """
    if scope not in VALID_SCOPES:
        raise ValueError(
            f"Unknown scope {scope!r}. Valid values: {sorted(VALID_SCOPES)}"
        )

    result = db.execute(_SDI_UPSERT_SQL, {"scope": scope, "country": country_filter})
    db.commit()
    upserted = result.rowcount

    if upserted == 0:
        logger.warning(
            "No snapshots written for scope=%s country_filter=%s — "
            "check posting_skills and role_catalog coverage",
            scope,
            country_filter,
        )
        return 0

    _log_unmatched_roles(db, country_filter, scope)
    logger.info("SDI refresh complete", extra={"scope": scope, "upserted": upserted})
    return upserted


def get_weighted_sdi(
    role_id: uuid.UUID,
    db: Session,
    scope: str = "ph",
    decay_factor: float = DEFAULT_DECAY_FACTOR,
) -> dict[uuid.UUID, float]:
    """Return recency-weighted SDI values for all skills in the given role.

    Implements the weighted formula from the intelligence documentation:
        SDI_weighted = sum(SDI(t) * decay^(N-t_index)) / sum(decay^(N-t_index))

    If the requested scope has no data (e.g. 'ph' but no PH postings have been
    ingested yet), automatically falls back to 'global' so the gap endpoint
    remains functional with the broader dataset.

    Args:
        role_id: UUID of the target role.
        db: Active database session.
        scope: Preferred scope ('ph' or 'global'). Falls back to 'global' when
            the preferred scope has no snapshots for this role.
        decay_factor: Exponential recency weight.

    Returns:
        Dictionary mapping skill_id UUID to weighted SDI float value.
    """
    scopes_to_try = [scope, "global"] if scope != "global" else ["global"]

    rows: list = []
    for try_scope in scopes_to_try:
        rows = db.execute(
            text("""
                SELECT skill_id, period, sdi_value
                FROM sdi_snapshots
                WHERE role_id = :role_id AND scope = :scope
                ORDER BY period ASC
            """),
            {"role_id": str(role_id), "scope": try_scope},
        ).fetchall()
        if rows:
            logger.debug(
                "get_weighted_sdi: using scope=%s (requested=%s) for role_id=%s",
                try_scope, scope, role_id,
            )
            break

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

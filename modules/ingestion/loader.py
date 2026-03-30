"""Historical batch ingestion loader.

Reads a pre-built unified_job_postings.csv from the processed data path
and upserts rows into job_postings_unified. Idempotent: running twice
produces no duplicates because posting_id is the primary key.

Expected CSV schema (9 columns):
    posting_id, title, role_normalized, skills,
    seniority, platform, country, posted_date, source_dataset
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core.config import settings
from modules.ingestion.models import JobPostingUnified

logger = logging.getLogger(__name__)

CANONICAL_COLUMNS = [
    "posting_id",
    "title",
    "role_normalized",
    "skills",
    "seniority",
    "platform",
    "country",
    "posted_date",
    "source_dataset",
]

VALID_SENIORITY = {"entry_level", "mid", "senior", "unknown"}
VALID_PLATFORMS = {"linkedin", "indeed", "jobstreet", "kalibrr", "historical"}
VALID_COUNTRIES = {"PH", "US", "global"}


def _validate_row(row: pd.Series) -> str | None:
    """Return a rejection reason string if a row fails quality gates, else None.

    Args:
        row: A single posting row from the CSV.

    Returns:
        A human-readable rejection reason, or None if the row is valid.
    """
    if not str(row.get("title", "")).strip():
        return "missing title"
    if not _is_valid_period(str(row.get("posted_date", ""))):
        return "invalid posted_date format"
    if str(row.get("seniority", "")) not in VALID_SENIORITY:
        return "invalid seniority"
    if str(row.get("country", "")) not in VALID_COUNTRIES:
        return "invalid country"
    if not str(row.get("role_normalized", "")).strip():
        return "missing role_normalized"
    return None


def _is_valid_period(value: str) -> bool:
    """Return True if value matches YYYY-MM format."""
    if len(value) != 7 or value[4] != "-":
        return False
    year, month = value[:4], value[5:]
    return year.isdigit() and month.isdigit() and 1 <= int(month) <= 12


def load_historical_batch(db: Session, csv_path: Path | None = None) -> dict[str, int]:
    """Load unified_job_postings.csv into job_postings_unified.

    Stores the `skills` column (raw comma-separated keywords from the source)
    so the normalization pipeline can extract from it alongside the title.

    Args:
        db: Active database session.
        csv_path: Path to the CSV file. Defaults to processed_data_path/unified_job_postings.csv.

    Returns:
        Dictionary with keys 'inserted', 'skipped', 'quarantined'.
    """
    if csv_path is None:
        csv_path = Path(settings.processed_data_path) / "unified_job_postings.csv"

    if not csv_path.exists():
        raise RuntimeError(
            f"unified_job_postings.csv not found at {csv_path}. "
            "Run the bootstrap script first: "
            "python scripts/historical_bootstrap.py"
        )

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    inserted = 0
    skipped = 0
    quarantined = 0

    for _, row in df.iterrows():
        reason = _validate_row(row)
        if reason:
            logger.warning(
                "Quarantined row",
                extra={"posting_id": row.get("posting_id", "?"), "reason": reason},
            )
            quarantined += 1
            continue

        raw_skills = str(row.get("skills", "")).strip()
        skills_val: str | None = raw_skills if raw_skills and raw_skills.lower() != "nan" else None

        stmt = (
            insert(JobPostingUnified)
            .values(
                posting_id=str(row["posting_id"]),
                title=str(row["title"]).strip(),
                role_normalized=str(row["role_normalized"]).strip(),
                skills=skills_val,
                seniority=str(row["seniority"]),
                platform=str(row["platform"]),
                country=str(row["country"]),
                posted_date=str(row["posted_date"]),
                source_dataset=str(row["source_dataset"]),
            )
            .on_conflict_do_update(
                index_elements=["posting_id"],
                set_={"skills": skills_val},
            )
        )
        result = db.execute(stmt)
        inserted += result.rowcount

    db.commit()
    logger.info(
        "Historical batch load complete",
        extra={"inserted": inserted, "skipped": skipped, "quarantined": quarantined},
    )
    return {"inserted": inserted, "skipped": skipped, "quarantined": quarantined}

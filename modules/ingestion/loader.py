"""Historical batch ingestion loader.

Reads one or more pre-built CSV files from the processed data path,
merges them in memory, deduplicates on posting_id, and upserts rows
into job_postings_unified. Idempotent: running twice produces no
duplicates because posting_id is the primary key.

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


def _read_and_validate_csv(csv_path: Path) -> pd.DataFrame:
    """Read a single CSV file and verify it contains all canonical columns.

    Args:
        csv_path: Path to a processed canonical CSV file.

    Returns:
        DataFrame with all rows from the file (dtype=str).

    Raises:
        ValueError: If one or more canonical columns are absent.
    """
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{csv_path.name} missing required columns: {missing}")
    return df


def load_historical_batch(
    db: Session,
    csv_paths: list[Path] | None = None,
) -> dict[str, int]:
    """Load one or more processed CSV files into job_postings_unified.

    Files are merged in memory and deduplicated on posting_id before
    upserting. When two files share a posting_id the first file's row
    wins — so unified_job_postings.csv (always first in the default list)
    is the authoritative source on collision.

    Stores the `skills` column (raw comma-separated keywords from the
    source) so the normalization pipeline can extract from it alongside
    the title.

    Args:
        db: Active database session.
        csv_paths: Explicit list of canonical CSV paths to load. Defaults
            to [processed_data_path/unified_job_postings.csv]. Pass
            additional paths (e.g. live_scraped_ph.csv) to merge multiple
            processed datasets in one pass.

    Returns:
        Dictionary with keys 'inserted', 'skipped', 'quarantined'.

    Raises:
        RuntimeError: If none of the resolved paths exist on disk, or if
            all existing files fail schema validation.
    """
    if csv_paths is None:
        csv_paths = [Path(settings.processed_data_path) / "unified_job_postings.csv"]

    # --- startup guard -----------------------------------------------
    # Raise only when ALL paths are missing; warn and skip individual ones.
    existing: list[Path] = []
    for p in csv_paths:
        if p.exists():
            existing.append(p)
        else:
            logger.warning(
                "Processed CSV not found — skipping",
                extra={"path": str(p)},
            )

    if not existing:
        paths_str = ", ".join(str(p) for p in csv_paths)
        raise RuntimeError(
            f"No processed CSV files found at: {paths_str}. "
            "Run the bootstrap script first: "
            "python scripts/historical_bootstrap.py"
        )

    # --- per-file read + column validation ---------------------------
    # Validate schema before concat so a malformed file fails fast and
    # does not contaminate the merged frame.
    frames: list[pd.DataFrame] = []
    for p in existing:
        try:
            df = _read_and_validate_csv(p)
            logger.info(
                "CSV loaded for merge",
                extra={"path": str(p), "rows": len(df)},
            )
            frames.append(df)
        except ValueError as exc:
            logger.error(
                "CSV schema validation failed — skipping file",
                extra={"path": str(p), "error": str(exc)},
            )

    if not frames:
        raise RuntimeError(
            "All CSV files failed schema validation. "
            "Run the bootstrap script first: "
            "python scripts/historical_bootstrap.py"
        )

    # --- merge + dedup -----------------------------------------------
    combined = pd.concat(frames, ignore_index=True)
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=["posting_id"], keep="first")
    duplicates_dropped = before_dedup - len(combined)
    if duplicates_dropped:
        logger.info(
            "Dropped duplicate posting_ids across source files",
            extra={"dropped": duplicates_dropped},
        )

    # --- upsert loop -------------------------------------------------
    # BEFORE: one DB round-trip per row via iterrows() — very slow at scale
    # AFTER: validate all rows first, then bulk upsert in one statement

    inserted = 0
    skipped = 0
    quarantined = 0

    valid_rows = []
    for _, row in combined.iterrows():
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

        valid_rows.append({
            "posting_id":     str(row["posting_id"]),
            "title":          str(row["title"]).strip(),
            "role_normalized":str(row["role_normalized"]).strip(),
            "skills":         skills_val,
            "seniority":      str(row["seniority"]),
            "platform":       str(row["platform"]),
            "country":        str(row["country"]),
            "posted_date":    str(row["posted_date"]),
            "source_dataset": str(row["source_dataset"]),
        })

    if valid_rows:
        stmt = (
            insert(JobPostingUnified)
            .values(valid_rows)
            .on_conflict_do_update(
                index_elements=["posting_id"],
                set_={"skills": insert(JobPostingUnified).excluded.skills},
            )
        )
        result = db.execute(stmt)
        inserted = result.rowcount

    db.commit()
    logger.info(
        "Historical batch load complete",
        extra={"inserted": inserted, "skipped": skipped, "quarantined": quarantined},
    )
    return {"inserted": inserted, "skipped": skipped, "quarantined": quarantined}

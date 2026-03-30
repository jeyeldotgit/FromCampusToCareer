"""Transformer for Philippines Job Postings (Kaggle, JobStreet-sourced).

This is the only Stage 1 source with country='PH'. Critical for the PH SDI branch
and student-facing gap analysis.

Expected files in source_dir:
    Any single CSV file — the transformer auto-discovers the first .csv file.
    Common filenames: 'jobs.csv', 'philippines_jobs.csv', 'ph_jobs.csv'

Column mapping reference: transformers/column_mappings.md §Source 5.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from modules.ingestion.transformers import CANONICAL_COLUMNS, map_seniority

logger = logging.getLogger(__name__)

SOURCE_DATASET = "philippines_job_postings_kaggle"
PLATFORM = "jobstreet"
COUNTRY = "PH"

# Candidate column names tried in order. First found is used.
_TITLE_CANDIDATES = [
    "job_title", "title", "Job Title", "JobTitle", "position", "Position",
    "role", "job_role",
]
_DATE_CANDIDATES = [
    "date_posted", "posted_date", "created_at", "Date Posted", "date",
    "post_date", "listing_date",
]
_SENIORITY_CANDIDATES = [
    "experience", "experience_level", "seniority", "job_level",
    "Experience", "Experience Level", "level",
]
_ID_CANDIDATES = [
    "id", "job_id", "listing_id", "posting_id", "Job ID",
]
_SKILLS_CANDIDATES = [
    "skills", "job_skills", "required_skills", "Skills",
]


def _find_csv(source_dir: Path) -> Path:
    """Find the first CSV file in source_dir.

    Args:
        source_dir: Directory to search.

    Returns:
        Path to the first CSV file found.

    Raises:
        FileNotFoundError: If no CSV files are found.
    """
    csv_files = list(source_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {source_dir}. "
            "Download from Kaggle and place in this directory. "
            "See column_mappings.md §Source 5 for expected format."
        )
    if len(csv_files) > 1:
        logger.warning(
            "Multiple CSV files in %s; using first: %s", source_dir, csv_files[0].name
        )
    return csv_files[0]


def _resolve_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first candidate column name present in df.

    Args:
        df: DataFrame to check.
        candidates: Ordered list of candidate column names.

    Returns:
        The first matching column name, or None if none match.
    """
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _parse_date(raw: str) -> str:
    """Parse a date string to YYYY-MM.

    Args:
        raw: Raw date string.

    Returns:
        'YYYY-MM' string, or '1970-01' on failure.
    """
    if not raw or raw in {"nan", ""}:
        return "1970-01"
    try:
        return pd.to_datetime(raw).strftime("%Y-%m")
    except Exception:
        return "1970-01"


def transform(source_dir: Path) -> pd.DataFrame:
    """Read Philippines Job Postings CSV and return a canonical DataFrame.

    Args:
        source_dir: Directory containing the dataset CSV.

    Returns:
        DataFrame with columns matching CANONICAL_COLUMNS (minus posting_id).
        The 'country' column is always 'PH'.

    Raises:
        FileNotFoundError: If no CSV file is found.
        ValueError: If no title column can be identified.
    """
    csv_path = _find_csv(source_dir)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    logger.info(
        "Loaded %s: %d rows, columns: %s", csv_path.name, len(df), df.columns.tolist()
    )

    title_col = _resolve_col(df, _TITLE_CANDIDATES)
    if title_col is None:
        raise ValueError(
            f"Cannot identify a title column in {csv_path.name}. "
            f"Tried: {_TITLE_CANDIDATES}. "
            f"Actual columns: {df.columns.tolist()}. "
            "Update column_mappings.md §Source 5 and add the correct name."
        )

    date_col = _resolve_col(df, _DATE_CANDIDATES)
    seniority_col = _resolve_col(df, _SENIORITY_CANDIDATES)
    id_col = _resolve_col(df, _ID_CANDIDATES)
    skills_col = _resolve_col(df, _SKILLS_CANDIDATES)

    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        title = str(row[title_col]).strip()
        if not title or title.lower() in {"nan", "none"}:
            continue

        native_id = str(row[id_col]) if id_col else None
        raw_date = str(row[date_col]) if date_col else ""
        raw_seniority = str(row[seniority_col]) if seniority_col else ""
        skills_raw = str(row[skills_col]) if skills_col else ""

        records.append({
            "posting_id": "",
            "title": title,
            "role_normalized": "",
            "skills": skills_raw,
            "seniority": map_seniority(raw_seniority),
            "platform": PLATFORM,
            "country": COUNTRY,
            "posted_date": _parse_date(raw_date),
            "source_dataset": SOURCE_DATASET,
        })

    result = pd.DataFrame(records, columns=CANONICAL_COLUMNS)
    logger.info(
        "philippines_kaggle transform complete",
        extra={"rows": len(result), "source": str(source_dir), "country": COUNTRY},
    )
    return result

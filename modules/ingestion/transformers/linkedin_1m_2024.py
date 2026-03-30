"""Transformer for 1.3M LinkedIn Jobs and Skills 2024 (Kaggle, asaniczka).

Expected files in source_dir:
    linkedin_job_postings.csv  — main postings file
    job_skills.csv             — posting ↔ comma-separated skills

Column mapping reference: transformers/column_mappings.md §Source 2.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from modules.ingestion.transformers import CANONICAL_COLUMNS, map_seniority

logger = logging.getLogger(__name__)

SOURCE_DATASET = "1m_linkedin_skills_2024_kaggle"
PLATFORM = "linkedin"
COUNTRY = "global"
FALLBACK_DATE = "2024-01"

_REQUIRED_POSTING_COLS = {"job_link", "job_title"}
_REQUIRED_SKILLS_COLS = {"job_link", "job_skills"}


def _parse_date(raw: str) -> str:
    """Parse a date string to YYYY-MM.

    Args:
        raw: Raw date string from first_seen column.

    Returns:
        'YYYY-MM' string, or FALLBACK_DATE on parse failure.
    """
    if not raw or raw == "nan":
        return FALLBACK_DATE
    try:
        return pd.to_datetime(raw).strftime("%Y-%m")
    except Exception:
        return FALLBACK_DATE


def transform(source_dir: Path) -> pd.DataFrame:
    """Read 1.3M LinkedIn 2024 Kaggle files and return a canonical DataFrame.

    Args:
        source_dir: Directory containing linkedin_job_postings.csv and job_skills.csv.

    Returns:
        DataFrame with columns matching CANONICAL_COLUMNS (minus posting_id).

    Raises:
        FileNotFoundError: If the main postings file is missing.
        ValueError: If required columns are absent.
    """
    postings_path = source_dir / "linkedin_job_postings.csv"
    if not postings_path.exists():
        raise FileNotFoundError(
            f"linkedin_job_postings.csv not found in {source_dir}. "
            "Download from Kaggle (asaniczka/1-3-million-linkedin-jobs-and-skills-2024)."
        )

    postings = pd.read_csv(postings_path, dtype=str, keep_default_na=False)
    _assert_columns(postings, _REQUIRED_POSTING_COLS, "linkedin_job_postings.csv")

    skills_lookup: dict[str, str] = {}
    skills_path = source_dir / "job_skills.csv"
    if skills_path.exists():
        job_skills = pd.read_csv(skills_path, dtype=str, keep_default_na=False)
        if _REQUIRED_SKILLS_COLS.issubset(set(job_skills.columns)):
            for _, row in job_skills.iterrows():
                skills_lookup[str(row["job_link"])] = str(row["job_skills"])
        else:
            logger.warning("job_skills.csv missing expected columns; skills will be empty")
    else:
        logger.warning("job_skills.csv not found in %s; skills will be empty", source_dir)

    records: list[dict[str, str]] = []
    for _, row in postings.iterrows():
        job_link = str(row["job_link"])
        title = str(row["job_title"]).strip()
        if not title:
            continue

        raw_date = str(row.get("first_seen", ""))
        raw_seniority = str(row.get("job_level", ""))
        skills_raw = skills_lookup.get(job_link, "")

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

    df = pd.DataFrame(records, columns=CANONICAL_COLUMNS)
    logger.info(
        "linkedin_1m_2024 transform complete",
        extra={"rows": len(df), "source": str(source_dir)},
    )
    return df


def _assert_columns(df: pd.DataFrame, required: set[str], filename: str) -> None:
    """Raise ValueError if any required column is missing from df.

    Args:
        df: DataFrame to check.
        required: Set of required column names.
        filename: Source filename for the error message.

    Raises:
        ValueError: Lists the missing columns and actual columns present.
    """
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing required columns: {sorted(missing)}. "
            f"Actual columns: {df.columns.tolist()}. "
            "Update column_mappings.md and the transformer to match."
        )

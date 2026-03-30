"""Transformer for Online Job Postings Historical (Kaggle).

Verified against: data/raw/kaggle/online_historical/job_posting.csv
Encoding: latin-1
Total rows: ~9,919

Verified column names:
    'Job Opening Title'     → title
    'First Seen At'         → posted_date  (ISO 8601 e.g. '2024-05-29T19:59:45Z')
    'Seniority'             → seniority    (non_manager, manager, head, director, ...)
    'Keywords'              → skills       (comma-separated keywords/skills)
    'O*NET Occupation Name' → supplemental role label (used as role_normalized hint)
    'Job Opening URL'       → native_id for posting_id generation

Column mapping reference: transformers/column_mappings.md §Source 4.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from modules.ingestion.transformers import CANONICAL_COLUMNS, map_seniority

logger = logging.getLogger(__name__)

SOURCE_DATASET = "online_job_posts_historical_kaggle"
PLATFORM = "historical"
COUNTRY = "global"
FILE_ENCODING = "latin-1"

# Primary column names verified from actual CSV headers.
TITLE_COL = "Job Opening Title"
DATE_COL = "First Seen At"
SENIORITY_COL = "Seniority"
SKILLS_COL = "Keywords"
# Fallback candidates in case the dataset is loaded with different column names.
_TITLE_CANDIDATES = [
    TITLE_COL, "Job Opening Title",
    "Title", "title", "job_title", "position", "Position", "jobpost",
]
_DATE_CANDIDATES = [
    DATE_COL, "First Seen At",
    "Date", "date", "StartDate", "start_date", "posted_date", "created_at",
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
            "Download the dataset from Kaggle and place it here."
        )
    if len(csv_files) > 1:
        logger.warning(
            "Multiple CSV files found in %s; using first: %s",
            source_dir,
            csv_files[0].name,
        )
    return csv_files[0]


def _resolve_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Return the first candidate column name present in df, or None.

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

    Handles ISO 8601 timestamps ('2024-05-29T19:59:45Z') and plain dates.

    Args:
        raw: Raw date string.

    Returns:
        'YYYY-MM' string, or '1970-01' on failure.
    """
    if not raw or raw in {"nan", ""}:
        return "1970-01"
    try:
        return pd.to_datetime(raw, utc=True).strftime("%Y-%m")
    except Exception:
        try:
            return pd.to_datetime(raw).strftime("%Y-%m")
        except Exception:
            return "1970-01"


def transform(source_dir: Path) -> pd.DataFrame:
    """Read Online Job Postings Historical CSV and return a canonical DataFrame.

    Uses verified column names from the job_posting.csv Kaggle dataset.
    Falls back to candidate column lists for resilience against minor variations.

    Args:
        source_dir: Directory containing the dataset CSV.

    Returns:
        DataFrame with columns matching CANONICAL_COLUMNS (minus posting_id).
        Skills are populated from the 'Keywords' column when available.

    Raises:
        FileNotFoundError: If no CSV file is found.
        ValueError: If no title column can be identified.
    """
    csv_path = _find_csv(source_dir)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding=FILE_ENCODING)
    logger.info(
        "Loaded %s: %d rows, columns: %s", csv_path.name, len(df), df.columns.tolist()
    )

    title_col = _resolve_col(df, _TITLE_CANDIDATES)
    if title_col is None:
        raise ValueError(
            f"Cannot identify a title column in {csv_path.name}. "
            f"Tried: {_TITLE_CANDIDATES}. "
            f"Actual columns: {df.columns.tolist()}. "
            f"Update {__file__} and column_mappings.md with the correct name."
        )

    date_col = _resolve_col(df, _DATE_CANDIDATES)
    seniority_col = SENIORITY_COL if SENIORITY_COL in df.columns else None
    skills_col = SKILLS_COL if SKILLS_COL in df.columns else None

    logger.info(
        "Column resolution — title=%s date=%s seniority=%s skills=%s",
        title_col, date_col, seniority_col, skills_col,
    )

    records: list[dict[str, str]] = []
    for _, row in df.iterrows():
        title = str(row[title_col]).strip()
        if not title or title.lower() in {"nan", "none"}:
            continue

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
    if result.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    logger.info(
        "online_historical transform complete",
        extra={"rows": len(result), "source": str(source_dir)},
    )
    return result

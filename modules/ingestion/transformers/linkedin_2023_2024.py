"""Transformer for LinkedIn Job Postings 2023-2024 (Kaggle, arshkon).

Expected files in source_dir:
    job_postings.csv  — main postings with title and experience level
    job_skills.csv    — posting ↔ skill_abr associations
    skills.csv        — skill_abr ↔ skill_name lookup (optional)

Column mapping reference: transformers/column_mappings.md §Source 1.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from modules.ingestion.transformers import CANONICAL_COLUMNS, map_seniority

logger = logging.getLogger(__name__)

SOURCE_DATASET = "linkedin_2023_2024_kaggle"
PLATFORM = "linkedin"
COUNTRY = "global"

_REQUIRED_POSTING_COLS = {"job_id", "title", "original_listed_time"}
_REQUIRED_SKILLS_COLS = {"job_id", "skill_abr"}


def _parse_posted_date(ts_ms: object) -> str:
    """Convert a Unix millisecond timestamp to YYYY-MM.

    Args:
        ts_ms: Raw timestamp value (may be float, int, or string).

    Returns:
        'YYYY-MM' string, or '1970-01' on parse failure.
    """
    try:
        ts_sec = float(ts_ms) / 1000.0
        return pd.to_datetime(ts_sec, unit="s").strftime("%Y-%m")
    except Exception:
        return "1970-01"


def transform(source_dir: Path) -> pd.DataFrame:
    """Read LinkedIn 2023-2024 Kaggle files and return a canonical DataFrame.

    Args:
        source_dir: Directory containing job_postings.csv and job_skills.csv.

    Returns:
        DataFrame with columns matching CANONICAL_COLUMNS (minus posting_id).

    Raises:
        FileNotFoundError: If job_postings.csv is missing.
        ValueError: If required columns are absent from the CSV.
    """
    postings_path = source_dir / "job_postings.csv"
    if not postings_path.exists():
        raise FileNotFoundError(
            f"job_postings.csv not found in {source_dir}. "
            "Download the dataset from Kaggle and place it here."
        )

    postings = pd.read_csv(postings_path, dtype=str, keep_default_na=False)
    _assert_columns(postings, _REQUIRED_POSTING_COLS, "job_postings.csv")

    skills_lookup: dict[str, list[str]] = {}
    skills_path = source_dir / "job_skills.csv"
    if skills_path.exists():
        job_skills = pd.read_csv(skills_path, dtype=str, keep_default_na=False)
        if _REQUIRED_SKILLS_COLS.issubset(set(job_skills.columns)):
            name_map = _build_skill_name_map(source_dir)
            for _, row in job_skills.iterrows():
                jid = str(row["job_id"])
                abr = str(row["skill_abr"])
                name = name_map.get(abr, abr)
                skills_lookup.setdefault(jid, []).append(name)
        else:
            logger.warning("job_skills.csv missing expected columns; skills will be empty")
    else:
        logger.warning("job_skills.csv not found in %s; skills will be empty", source_dir)

    records: list[dict[str, str]] = []
    for _, row in postings.iterrows():
        job_id = str(row["job_id"])
        title = str(row["title"]).strip()
        if not title:
            continue

        posted_date = _parse_posted_date(row.get("original_listed_time", "0"))
        raw_seniority = str(row.get("formatted_experience_level", ""))
        skills_list = skills_lookup.get(job_id, [])

        records.append({
            "posting_id": "",
            "title": title,
            "role_normalized": "",
            "skills": ",".join(skills_list),
            "seniority": map_seniority(raw_seniority),
            "platform": PLATFORM,
            "country": COUNTRY,
            "posted_date": posted_date,
            "source_dataset": SOURCE_DATASET,
        })

    df = pd.DataFrame(records, columns=CANONICAL_COLUMNS)
    logger.info(
        "linkedin_2023_2024 transform complete",
        extra={"rows": len(df), "source": str(source_dir)},
    )
    return df


def _build_skill_name_map(source_dir: Path) -> dict[str, str]:
    """Build abr → name lookup from skills.csv if available.

    Args:
        source_dir: Source data directory.

    Returns:
        Dict mapping skill abbreviation to full skill name.
    """
    skills_file = source_dir / "skills.csv"
    if not skills_file.exists():
        return {}
    try:
        df = pd.read_csv(skills_file, dtype=str, keep_default_na=False)
        if {"skill_abr", "skill_name"}.issubset(set(df.columns)):
            return dict(zip(df["skill_abr"], df["skill_name"]))
    except Exception as exc:
        logger.warning("Could not read skills.csv: %s", exc)
    return {}


def _assert_columns(df: pd.DataFrame, required: set[str], filename: str) -> None:
    """Raise ValueError if any required column is missing from df.

    Args:
        df: DataFrame to check.
        required: Set of required column names.
        filename: Source filename for the error message.

    Raises:
        ValueError: Lists the missing columns and the actual columns present.
    """
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing required columns: {sorted(missing)}. "
            f"Actual columns: {df.columns.tolist()}. "
            "Update column_mappings.md and the transformer to match."
        )

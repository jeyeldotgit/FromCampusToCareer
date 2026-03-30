"""Shared constants and utilities for Kaggle source transformers.

Each transformer module exposes a single `transform(source_dir: Path) -> pd.DataFrame`
function that returns a DataFrame with exactly the 9 canonical columns.
"""

from __future__ import annotations

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

# Maps raw seniority strings (lowercased) from Kaggle sources to canonical values.
# First match wins when iterating; add new keys at the top to override defaults.
SENIORITY_MAP: dict[str, str] = {
    "entry level": "entry_level",
    "entry-level": "entry_level",
    "associate": "entry_level",
    "internship": "entry_level",
    "intern": "entry_level",
    "junior": "entry_level",
    "jr": "entry_level",
    "graduate": "entry_level",
    "fresh graduate": "entry_level",
    "mid-senior level": "mid",
    "mid-senior": "mid",
    "mid level": "mid",
    "mid-level": "mid",
    "middle": "mid",
    "intermediate": "mid",
    "experienced": "mid",
    "senior": "senior",
    "sr": "senior",
    "lead": "senior",
    "staff": "senior",
    "principal": "senior",
    "director": "senior",
    "executive": "senior",
    "vp": "senior",
    "vice president": "senior",
    "manager": "senior",
    "head of": "senior",
    # online_historical dataset values
    "non_manager": "entry_level",
    "manager": "senior",
    "head": "senior",
    "c_level": "senior",
    "partner": "senior",
    "president": "senior",
    # generic fallbacks
    "not applicable": "unknown",
    "other": "unknown",
    "": "unknown",
}


def map_seniority(raw: str) -> str:
    """Map a raw seniority string to a canonical value.

    Args:
        raw: Raw seniority label from a source dataset.

    Returns:
        One of: 'entry_level', 'mid', 'senior', 'unknown'.
    """
    return SENIORITY_MAP.get(str(raw).strip().lower(), "unknown")

"""Tech-field inclusion filter for job posting bootstrapping.

Filters raw job posting DataFrames to tech/IT positions only.
Applied in historical_bootstrap.py after all transformers have run
and before role mapping and posting_id generation.
"""

from __future__ import annotations

import pandas as pd

# Lowercase keyword list. A posting is kept if its title contains
# at least one of these terms.
_TECH_KEYWORDS: frozenset[str] = frozenset({
    "engineer",
    "developer",
    "analyst",
    "programmer",
    "architect",
    "software",
    "data",
    "devops",
    "cloud",
    "security",
    "network",
    "systems",
    "infrastructure",
    "database",
    "backend",
    "back-end",
    "back end",
    "frontend",
    "front-end",
    "front end",
    "fullstack",
    "full stack",
    "full-stack",
    "qa",
    "tester",
    "testing",
    "it support",
    "helpdesk",
    "help desk",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "ml engineer",
    "ai engineer",
    "cyber",
    "sre",
    "platform",
    "mobile",
    "android",
    "ios",
    "flutter",
    "react",
    "angular",
    "vue",
    "blockchain",
    "web3",
    "firmware",
    "embedded",
    "iot",
    "sdet",
    "scrum",
    "agile",
    "technical",
    "technology",
    "computing",
    "information technology",
    "it specialist",
    "it technician",
    "it coordinator",
    "sysadmin",
    "sys admin",
    "dba",
    "etl",
    "game developer",
    "game programmer",
})


def is_tech_job(title: str) -> bool:
    """Return True if a job title contains at least one tech keyword.

    Args:
        title: Raw job title string.

    Returns:
        True if the title matches any tech keyword; False otherwise.
    """
    lower = title.strip().lower()
    return any(kw in lower for kw in _TECH_KEYWORDS)


def filter_tech_jobs(df: pd.DataFrame, title_col: str = "title") -> pd.DataFrame:
    """Filter a DataFrame to tech/IT postings only.

    Args:
        df: Input DataFrame containing a title column.
        title_col: Name of the title column. Defaults to 'title'.

    Returns:
        Filtered DataFrame containing only rows where the title matches
        at least one tech keyword.
    """
    if title_col not in df.columns:
        raise ValueError(
            f"Column '{title_col}' not found in DataFrame. "
            f"Available columns: {df.columns.tolist()}"
        )
    mask = df[title_col].fillna("").apply(is_tech_job)
    return df[mask].reset_index(drop=True)

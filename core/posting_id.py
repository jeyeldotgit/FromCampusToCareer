"""Deterministic posting_id generation.

The same input always produces the same 20-char ID. This is the critical
dedup guarantee that prevents SDI count corruption on reruns.

Rule (from initial-unified-dataset-and-scraping.md §4):
    base = f"{source_dataset}|{native_id or ''}|{title.strip().lower()}|{posted_date}"
    posting_id = sha1(base).hexdigest()[:20]
"""

from __future__ import annotations

import hashlib


def make_posting_id(
    source_dataset: str,
    native_id: str | None,
    title: str,
    posted_date: str,
) -> str:
    """Compute a deterministic 20-char posting identifier.

    Args:
        source_dataset: Source identifier string (e.g. 'linkedin_2023_2024_kaggle').
        native_id: Native job ID from the source dataset, or None if unavailable.
        title: Raw job title string.
        posted_date: Posting period in YYYY-MM format.

    Returns:
        20-character lowercase hex digest (SHA-1 prefix).

    Example:
        >>> make_posting_id("linkedin_ph", "123", "Data Analyst", "2025-03")
        'a3f8e2...'  # deterministic across calls
    """
    base = f"{source_dataset}|{native_id or ''}|{title.strip().lower()}|{posted_date}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:20]

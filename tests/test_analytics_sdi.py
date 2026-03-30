"""Tests for SDI computation logic.

Validates the core formula: SDI = skill_count / total_postings per period.
"""

from __future__ import annotations

import uuid

import pandas as pd

from modules.analytics_sdi.service import compute_sdi_snapshots


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sdi_basic_computation() -> None:
    skill_a = str(uuid.uuid4())
    rows = [
        {"posting_id": "p1", "role_normalized": "Data Analyst", "posted_date": "2025-01", "skill_id": skill_a},
        {"posting_id": "p2", "role_normalized": "Data Analyst", "posted_date": "2025-01", "skill_id": skill_a},
        {"posting_id": "p3", "role_normalized": "Data Analyst", "posted_date": "2025-01", "skill_id": str(uuid.uuid4())},
    ]
    df = _make_df(rows)
    result = compute_sdi_snapshots(df)

    analyst_rows = result[result["role_normalized"] == "Data Analyst"]
    skill_a_rows = analyst_rows[analyst_rows["skill_id"] == skill_a]
    assert len(skill_a_rows) == 1
    # skill_a appears in 2 of 3 postings
    assert abs(float(skill_a_rows.iloc[0]["sdi_value"]) - 2 / 3) < 0.001


def test_sdi_perfect_demand() -> None:
    skill_id = str(uuid.uuid4())
    rows = [
        {"posting_id": f"p{i}", "role_normalized": "SWE", "posted_date": "2025-01", "skill_id": skill_id}
        for i in range(5)
    ]
    df = _make_df(rows)
    result = compute_sdi_snapshots(df)
    swe_rows = result[(result["role_normalized"] == "SWE") & (result["skill_id"] == skill_id)]
    assert float(swe_rows.iloc[0]["sdi_value"]) == 1.0


def test_sdi_empty_input_returns_empty_df() -> None:
    result = compute_sdi_snapshots(pd.DataFrame())
    assert result.empty


def test_sdi_multiple_periods() -> None:
    skill_id = str(uuid.uuid4())
    rows = [
        {"posting_id": "p1", "role_normalized": "QA", "posted_date": "2025-01", "skill_id": skill_id},
        {"posting_id": "p2", "role_normalized": "QA", "posted_date": "2025-02", "skill_id": skill_id},
    ]
    df = _make_df(rows)
    result = compute_sdi_snapshots(df)
    assert len(result) == 2
    assert set(result["posted_date"].tolist()) == {"2025-01", "2025-02"}

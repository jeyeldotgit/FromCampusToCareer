"""Tests for deterministic posting_id and normalization logic.

Acceptance criterion: posting_id is deterministic and idempotent.
"""

from __future__ import annotations

from core.posting_id import make_posting_id
from modules.normalization.normalizer import normalize_skill_name, normalize_skill_set
import uuid


def test_posting_id_is_deterministic() -> None:
    """Same inputs always produce the same posting_id."""
    id1 = make_posting_id("linkedin_ph", "JOB123", "Data Analyst", "2025-03")
    id2 = make_posting_id("linkedin_ph", "JOB123", "Data Analyst", "2025-03")
    assert id1 == id2


def test_posting_id_length() -> None:
    pid = make_posting_id("linkedin_ph", None, "Software Engineer", "2025-01")
    assert len(pid) == 20


def test_posting_id_is_lowercase_hex() -> None:
    pid = make_posting_id("linkedin_ph", "X", "Backend Dev", "2024-12")
    assert pid == pid.lower()
    int(pid, 16)  # raises ValueError if not valid hex


def test_posting_id_differs_on_different_inputs() -> None:
    id1 = make_posting_id("linkedin_ph", "A", "Data Analyst", "2025-03")
    id2 = make_posting_id("linkedin_ph", "B", "Data Analyst", "2025-03")
    assert id1 != id2


def test_posting_id_title_case_insensitive() -> None:
    """Title normalisation: 'Data Analyst' and 'data analyst' produce same ID."""
    id1 = make_posting_id("src", "1", "Data Analyst", "2025-01")
    id2 = make_posting_id("src", "1", "data analyst", "2025-01")
    assert id1 == id2


def test_normalize_skill_known_alias() -> None:
    skill_uuid = uuid.uuid4()
    alias_map = {"reactjs": skill_uuid, "react.js": skill_uuid}
    result = normalize_skill_name("ReactJS", alias_map)
    assert result == skill_uuid


def test_normalize_skill_unknown_returns_none() -> None:
    alias_map: dict[str, uuid.UUID] = {}
    result = normalize_skill_name("CobolMaster", alias_map)
    assert result is None


def test_normalize_skill_set_splits_resolved_and_unknown() -> None:
    skill_uuid = uuid.uuid4()
    alias_map = {"python": skill_uuid}
    resolved, unknown = normalize_skill_set({"Python", "CobolMaster"}, alias_map)
    assert skill_uuid in resolved
    assert "cobolmaster" in unknown

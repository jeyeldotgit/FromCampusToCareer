"""Tests for deterministic posting_id and normalization logic.

Acceptance criterion: posting_id is deterministic and idempotent.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from core.posting_id import make_posting_id
from modules.normalization.extractor import build_matcher, extract_skills, extract_skills_from_doc
from modules.normalization.normalizer import normalize_skill_name, normalize_skill_set
from modules.normalization.pipeline import _bulk_insert_posting_skills, _iter_chunks


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


# ---------------------------------------------------------------------------
# extract_skills_from_doc — new batch-NLP helper (AC-5, AC-6)
# ---------------------------------------------------------------------------


def test_extract_skills_from_doc_basic() -> None:
    """A doc containing a known skill phrase returns the canonical name."""
    skill_patterns = {"python": "Python"}
    nlp, matcher = build_matcher(skill_patterns)
    doc = nlp("We need someone with Python experience")
    result = extract_skills_from_doc(doc, matcher)
    assert "Python" in result


def test_extract_skills_from_doc_empty() -> None:
    """An empty doc returns an empty set without raising."""
    skill_patterns = {"python": "Python"}
    nlp, matcher = build_matcher(skill_patterns)
    doc = nlp("")
    result = extract_skills_from_doc(doc, matcher)
    assert result == set()


def test_extract_skills_parity() -> None:
    """extract_skills and extract_skills_from_doc return identical results.

    Validates AC-6: the new doc-based function is functionally equivalent
    to the original text-based function for the same input.
    """
    skill_patterns = {
        "python": "Python",
        "sql": "SQL",
        "docker": "Docker",
        "machine learning": "Machine Learning",
        "git": "Git",
    }
    nlp, matcher = build_matcher(skill_patterns)

    sample_texts = [
        "Looking for a Python and SQL developer",
        "Docker and Git experience required",
        "Machine learning engineer with Python skills",
        "No matching skills here whatsoever",
        "",
    ]

    for text in sample_texts:
        via_text = extract_skills(text, nlp, matcher)
        via_doc = extract_skills_from_doc(nlp(text[:50_000]) if text.strip() else nlp(""), matcher)
        assert via_text == via_doc, f"Parity failed for text: {text!r}"


# ---------------------------------------------------------------------------
# _iter_chunks — pure Python chunking utility
# ---------------------------------------------------------------------------


def test_iter_chunks_sizes() -> None:
    """5,500 IDs chunked at 2,000 yields slices of [2000, 2000, 1500]."""
    items = list(range(5500))
    chunks = list(_iter_chunks(items, 2000))
    assert [len(c) for c in chunks] == [2000, 2000, 1500]


def test_iter_chunks_empty() -> None:
    """An empty list yields no chunks."""
    assert list(_iter_chunks([], 1000)) == []


def test_iter_chunks_smaller_than_size() -> None:
    """A list smaller than chunk size yields a single chunk."""
    items = list(range(50))
    chunks = list(_iter_chunks(items, 1000))
    assert len(chunks) == 1
    assert chunks[0] == items


# ---------------------------------------------------------------------------
# _bulk_insert_posting_skills — never commits, only executes (C-4)
# ---------------------------------------------------------------------------


def test_bulk_insert_does_not_commit() -> None:
    """_bulk_insert_posting_skills calls execute but never commit (C-4)."""
    mock_db = MagicMock()
    rows = [
        {"posting_id": "abc123", "skill_id": uuid.uuid4()},
        {"posting_id": "def456", "skill_id": uuid.uuid4()},
    ]
    _bulk_insert_posting_skills(mock_db, rows)
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_not_called()


def test_bulk_insert_skips_empty_rows() -> None:
    """_bulk_insert_posting_skills does nothing when rows list is empty."""
    mock_db = MagicMock()
    _bulk_insert_posting_skills(mock_db, [])
    mock_db.execute.assert_not_called()
    mock_db.commit.assert_not_called()

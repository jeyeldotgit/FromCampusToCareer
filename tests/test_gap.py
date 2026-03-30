"""Tests for gap analysis and roadmap logic."""

from __future__ import annotations

import uuid

from modules.gap_and_roadmap.gap_service import _classify_priority, _depth_rank
from modules.gap_and_roadmap.roadmap_service import build_roadmap
from modules.gap_and_roadmap.schemas import GapItem


def test_classify_priority_critical() -> None:
    assert _classify_priority(0.75) == "critical"
    assert _classify_priority(0.70) == "critical"


def test_classify_priority_important() -> None:
    assert _classify_priority(0.50) == "important"
    assert _classify_priority(0.40) == "important"


def test_classify_priority_emerging() -> None:
    assert _classify_priority(0.20) == "emerging"
    assert _classify_priority(0.00) == "emerging"


def test_depth_rank_ordering() -> None:
    assert _depth_rank("Advanced") > _depth_rank("Proficient")
    assert _depth_rank("Proficient") > _depth_rank("Intermediate")
    assert _depth_rank("Intermediate") > _depth_rank("Foundational")
    assert _depth_rank(None) == -1


def _make_gap(skill_name: str, band: str, sdi: float, gap_type: str = "missing") -> GapItem:
    return GapItem(
        skill_id=uuid.uuid4(),
        skill_name=skill_name,
        gap_type=gap_type,
        priority_band=band,
        sdi_value=sdi,
        student_depth=None,
        required_depth="Intermediate",
    )


def test_roadmap_sorted_by_band_then_sdi() -> None:
    gaps = [
        _make_gap("Skill A", "emerging", 0.30),
        _make_gap("Skill B", "critical", 0.80),
        _make_gap("Skill C", "important", 0.55),
        _make_gap("Skill D", "critical", 0.72),
    ]
    roadmap = build_roadmap(gaps)
    assert roadmap[0].skill_name == "Skill B"  # critical, highest SDI
    assert roadmap[1].skill_name == "Skill D"  # critical, lower SDI
    assert roadmap[2].skill_name == "Skill C"  # important
    assert roadmap[3].skill_name == "Skill A"  # emerging


def test_roadmap_ranks_are_sequential() -> None:
    gaps = [_make_gap(f"S{i}", "emerging", 0.1 * i) for i in range(5)]
    roadmap = build_roadmap(gaps)
    ranks = [r.rank for r in roadmap]
    assert ranks == list(range(1, 6))


def test_roadmap_action_contains_skill_name() -> None:
    gaps = [_make_gap("Python", "critical", 0.90)]
    roadmap = build_roadmap(gaps)
    assert "Python" in roadmap[0].action


def test_roadmap_depth_gap_action_mentions_depths() -> None:
    gap = GapItem(
        skill_id=uuid.uuid4(),
        skill_name="SQL",
        gap_type="depth_gap",
        priority_band="critical",
        sdi_value=0.85,
        student_depth="Foundational",
        required_depth="Advanced",
    )
    roadmap = build_roadmap([gap])
    assert "Foundational" in roadmap[0].action
    assert "Advanced" in roadmap[0].action

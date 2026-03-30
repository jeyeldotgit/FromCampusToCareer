"""Roadmap generation service.

Stage 1: Converts gap results into a priority-ranked action list.
Stage 2 will extend this file with certification and project suggestions.

This module does NOT import from gap_service. The router calls both
independently and assembles the combined response.
"""

from __future__ import annotations

from modules.gap_and_roadmap.schemas import GapItem, RoadmapItem

_ACTION_TEMPLATES = {
    "missing": "Learn {skill_name} — not yet in your skill set",
    "depth_gap": "Deepen {skill_name} — currently {student_depth}, market requires {required_depth}",
}

_BAND_ORDER = {"critical": 0, "important": 1, "emerging": 2}


def build_roadmap(gaps: list[GapItem]) -> list[RoadmapItem]:
    """Convert a list of gap items into a ranked roadmap action list.

    Items are sorted by priority band first, then by SDI value descending.
    No-gap skills are excluded — gaps should already be filtered to non-'no_gap' items.

    Stage 1 actions are plain skill study recommendations. Stage 2 will add
    certification and project suggestions without modifying gap_service.

    Args:
        gaps: List of GapItem instances from gap_service.compute_gap_analysis().

    Returns:
        List of RoadmapItem instances sorted by priority and SDI value.
    """
    sorted_gaps = sorted(
        gaps,
        key=lambda g: (_BAND_ORDER.get(g.priority_band, 99), -g.sdi_value),
    )

    roadmap: list[RoadmapItem] = []
    for rank, gap in enumerate(sorted_gaps, start=1):
        action = _ACTION_TEMPLATES.get(gap.gap_type, "Work on {skill_name}").format(
            skill_name=gap.skill_name,
            student_depth=gap.student_depth or "none",
            required_depth=gap.required_depth or "unknown",
        )
        roadmap.append(
            RoadmapItem(
                rank=rank,
                skill_name=gap.skill_name,
                priority_band=gap.priority_band,
                sdi_value=gap.sdi_value,
                action=action,
            )
        )
    return roadmap

"""Skill normalization: resolves raw skill strings to canonical skill names.

Uses the alias map loaded from the taxonomy database. Unknown strings are
flagged for admin review rather than silently dropped.
"""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


def normalize_skill_name(raw: str, alias_map: dict[str, uuid.UUID]) -> uuid.UUID | None:
    """Resolve a raw skill string to its canonical skill UUID.

    Lookup is case-insensitive via the pre-lowercased alias_map keys.

    Args:
        raw: Raw skill string from a job posting or student input.
        alias_map: Mapping of lowercase alias strings to canonical skill UUIDs,
                   as returned by taxonomy_admin.service.build_alias_map().

    Returns:
        Canonical skill UUID if a match is found, else None.
    """
    key = raw.strip().lower()
    skill_id = alias_map.get(key)
    if skill_id is None:
        logger.debug("Unknown skill alias, flagging for review: '%s'", raw)
    return skill_id


def normalize_skill_set(
    raw_skills: set[str],
    alias_map: dict[str, uuid.UUID],
) -> tuple[set[uuid.UUID], set[str]]:
    """Normalize a set of raw skill strings, separating resolved from unknown.

    Args:
        raw_skills: Set of raw skill strings to normalize.
        alias_map: Lowercase alias -> canonical skill UUID mapping.

    Returns:
        Tuple of (resolved_skill_ids, unknown_strings) where unknown_strings
        are candidates for admin taxonomy review.
    """
    resolved: set[uuid.UUID] = set()
    unknown: set[str] = set()

    for raw in raw_skills:
        skill_id = normalize_skill_name(raw, alias_map)
        if skill_id is not None:
            resolved.add(skill_id)
        else:
            unknown.add(raw.strip().lower())

    return resolved, unknown

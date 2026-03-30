from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel


class GapItem(BaseModel):
    """A single gap entry returned to the student."""

    skill_id: uuid.UUID
    skill_name: str
    gap_type: str
    priority_band: str
    sdi_value: float
    student_depth: str | None
    required_depth: str | None

    model_config = {"from_attributes": True}


class RoadmapItem(BaseModel):
    """A prioritised action item derived from gap results."""

    rank: int
    skill_name: str
    priority_band: str
    sdi_value: float
    action: str


class GapAnalysisResponse(BaseModel):
    role_id: uuid.UUID
    role_name: str
    readiness_score: float
    period: str
    gaps: list[GapItem]
    roadmap: list[RoadmapItem]


class ReadinessHistoryItem(BaseModel):
    period: str
    readiness_score: Decimal
    role_id: uuid.UUID

    model_config = {"from_attributes": True}

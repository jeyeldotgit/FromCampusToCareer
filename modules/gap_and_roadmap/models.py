from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class GapResult(Base):
    """Persisted gap analysis result for a student/role pair.

    Recomputed and replaced on every profile update or SDI refresh.
    gap_type: 'missing' | 'depth_gap' | 'no_gap'
    priority_band: 'critical' | 'important' | 'emerging'
    """

    __tablename__ = "gap_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("role_catalog.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id"), nullable=False
    )
    gap_type: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_band: Mapped[str] = mapped_column(String(20), nullable=False)
    sdi_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    student_depth: Mapped[str | None] = mapped_column(String(20))
    required_depth: Mapped[str | None] = mapped_column(String(20))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReadinessHistory(Base):
    """Point-in-time readiness score for a student/role pair.

    period stores the academic period (YYYY-MM) when the score was computed,
    supporting semester-by-semester querying without retrofitting.
    """

    __tablename__ = "readiness_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("role_catalog.id"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SdiSnapshot(Base):
    """Single SDI value for a skill/role/period/scope combination.

    scope='ph'     — Philippine postings (preferred for student gap analysis)
    scope='global' — All-country postings (gap analysis fallback when PH empty;
                    Stage 2 analytics_decay time series)

    UNIQUE constraint on (skill_id, role_id, period, scope) ensures that
    recomputation upserts existing rows rather than appending new ones.
    """

    __tablename__ = "sdi_snapshots"
    __table_args__ = (
        UniqueConstraint("skill_id", "role_id", "period", "scope", name="uq_sdi_snapshot"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role_catalog.id"), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    sdi_value: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    posting_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(String(10), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

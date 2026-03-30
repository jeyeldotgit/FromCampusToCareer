from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PipelineRun(Base):
    """Tracks the state of each worker pipeline execution.

    The admin writes a pending row; the worker reads and executes it.
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class JobPostingUnified(Base):
    """Canonical unified job posting. Consumed by all analytics modules.

    posting_id is a deterministic 20-char SHA-1 hex fingerprint.
    Skills are stored in the separate posting_skills join table.
    """

    __tablename__ = "job_postings_unified"

    posting_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    role_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    seniority: Mapped[str] = mapped_column(String(20), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    posted_date: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    source_dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

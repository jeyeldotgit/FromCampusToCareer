from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PostingSkill(Base):
    """Join table linking a canonical job posting to its extracted skill IDs.

    This is the required normalization output that the SDI computation pipeline
    aggregates against. Without these rows, SDI has no skill frequency data.
    """

    __tablename__ = "posting_skills"

    posting_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("job_postings_unified.posting_id"),
        primary_key=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skills.id"),
        primary_key=True,
    )

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Skill(Base):
    """Canonical skill in the taxonomy. All references use this table's IDs."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    aliases: Mapped[list[SkillAlias]] = relationship("SkillAlias", back_populates="skill")


class SkillAlias(Base):
    """Maps raw skill variant strings to a canonical Skill."""

    __tablename__ = "skill_aliases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)

    skill: Mapped[Skill] = relationship("Skill", back_populates="aliases")


class RoleCatalog(Base):
    """Canonical target career roles students declare against."""

    __tablename__ = "role_catalog"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CourseSkillMap(Base):
    """Maps a course code to a canonical skill with a minimum depth level."""

    __tablename__ = "course_skill_map"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    min_depth: Mapped[str] = mapped_column(String(20), nullable=False)


class GradeDepthRule(Base):
    """Maps PH grade ranges to skill depth labels used in gap analysis."""

    __tablename__ = "grade_depth_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    min_grade: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    max_grade: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    depth_level: Mapped[str] = mapped_column(String(20), nullable=False)

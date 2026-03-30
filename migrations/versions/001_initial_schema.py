"""Initial schema — all Stage 1 tables.

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_skills_name", "skills", ["name"])

    op.create_table(
        "skill_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(255), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias"),
    )

    op.create_table(
        "role_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "course_skill_map",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_code", sa.String(20), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("min_depth", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_skill_map_course_code", "course_skill_map", ["course_code"])

    op.create_table(
        "grade_depth_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("min_grade", sa.Numeric(4, 2), nullable=False),
        sa.Column("max_grade", sa.Numeric(4, 2), nullable=False),
        sa.Column("depth_level", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("year_level", sa.Integer(), nullable=False),
        sa.Column("program", sa.String(10), nullable=False),
        sa.Column("university", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_student_profiles_user_id", "student_profiles", ["user_id"])

    op.create_table(
        "course_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("course_code", sa.String(20), nullable=False),
        sa.Column("course_name", sa.String(255), nullable=False),
        sa.Column("grade", sa.Numeric(4, 2), nullable=False),
        sa.Column("academic_year", sa.String(10), nullable=False),
        sa.Column("semester", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_records_student_id", "course_records", ["student_id"])

    op.create_table(
        "certifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("credential_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tech_stack", sa.String(500), nullable=True),
        sa.Column("project_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "student_target_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_target_roles_student_id", "student_target_roles", ["student_id"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "job_postings_unified",
        sa.Column("posting_id", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("role_normalized", sa.String(255), nullable=False),
        sa.Column("seniority", sa.String(20), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("country", sa.String(10), nullable=False),
        sa.Column("posted_date", sa.String(7), nullable=False),
        sa.Column("source_dataset", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("posting_id"),
    )
    op.create_index("ix_job_postings_unified_country", "job_postings_unified", ["country"])
    op.create_index("ix_job_postings_unified_posted_date", "job_postings_unified", ["posted_date"])
    op.create_index("ix_job_postings_unified_role", "job_postings_unified", ["role_normalized"])

    op.create_table(
        "posting_skills",
        sa.Column("posting_id", sa.String(20), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["posting_id"], ["job_postings_unified.posting_id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("posting_id", "skill_id"),
    )

    op.create_table(
        "sdi_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("sdi_value", sa.Numeric(6, 4), nullable=False),
        sa.Column("posting_count", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(10), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("skill_id", "role_id", "period", "scope", name="uq_sdi_snapshot"),
    )
    op.create_index("ix_sdi_snapshots_skill_id", "sdi_snapshots", ["skill_id"])
    op.create_index("ix_sdi_snapshots_role_id", "sdi_snapshots", ["role_id"])

    op.create_table(
        "gap_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("skill_id", sa.Uuid(), nullable=False),
        sa.Column("gap_type", sa.String(20), nullable=False),
        sa.Column("priority_band", sa.String(20), nullable=False),
        sa.Column("sdi_value", sa.Numeric(6, 4), nullable=True),
        sa.Column("student_depth", sa.String(20), nullable=True),
        sa.Column("required_depth", sa.String(20), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role_catalog.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gap_results_student_id", "gap_results", ["student_id"])

    op.create_table(
        "readiness_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("readiness_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_readiness_history_student_id", "readiness_history", ["student_id"])


def downgrade() -> None:
    op.drop_table("readiness_history")
    op.drop_table("gap_results")
    op.drop_table("sdi_snapshots")
    op.drop_table("posting_skills")
    op.drop_table("job_postings_unified")
    op.drop_table("pipeline_runs")
    op.drop_table("student_target_roles")
    op.drop_table("projects")
    op.drop_table("certifications")
    op.drop_table("course_records")
    op.drop_table("student_profiles")
    op.drop_table("grade_depth_rules")
    op.drop_table("course_skill_map")
    op.drop_table("role_catalog")
    op.drop_table("skill_aliases")
    op.drop_table("skills")
    op.drop_table("users")

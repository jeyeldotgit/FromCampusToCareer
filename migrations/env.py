from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend package is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.database import Base  # noqa: F401

# Import all models so Alembic autogenerate can discover them
from modules.auth.models import User  # noqa: F401
from modules.analytics_sdi.models import SdiSnapshot  # noqa: F401
from modules.gap_and_roadmap.models import GapResult, ReadinessHistory  # noqa: F401
from modules.ingestion.models import JobPostingUnified, PipelineRun  # noqa: F401
from modules.normalization.models import PostingSkill  # noqa: F401
from modules.student_profile.models import (  # noqa: F401
    Certification,
    CourseRecord,
    Project,
    StudentProfile,
    StudentTargetRole,
)
from modules.taxonomy_admin.models import (  # noqa: F401
    CourseSkillMap,
    GradeDepthRule,
    RoleCatalog,
    Skill,
    SkillAlias,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from settings so we never hardcode credentials
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

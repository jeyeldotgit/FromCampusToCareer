"""Integration tests for analytics_sdi.run_sdi_refresh.

These tests require a real PostgreSQL database and minimum seed data.
They are skipped in the default SQLite unit test run.

To run locally:

    $env:RUN_INTEGRATION_TESTS = "1"
    $env:DATABASE_URL = "postgresql://user:password@localhost:5432/fctc_test"
    .venv\\Scripts\\pytest.exe tests/test_analytics_sdi_integration.py -v -m integration

The test database must have the full schema applied (run migrations first).
Each test seeds its own data and cleans up after itself.
"""

from __future__ import annotations

import os
import time
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.environ.get("RUN_INTEGRATION_TESTS", "0") == "1"


@pytest.fixture(scope="module")
def pg_engine():
    """Create a SQLAlchemy engine pointing at the PostgreSQL test database."""
    if not _integration_enabled():
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run integration tests")

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "sqlite" in db_url.lower():
        pytest.skip(
            "Integration tests require a PostgreSQL DATABASE_URL env var; "
            "current value is empty or SQLite."
        )

    engine = create_engine(db_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine) -> Session:
    """Open a session and roll back any uncommitted state on close."""
    SessionLocal = sessionmaker(bind=pg_engine, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture()
def seeded_session(pg_session: Session):
    """Seed minimum rows for one SDI computation and clean up after the test.

    Yields:
        Tuple of (session, skill_id UUID, role_id UUID).
    """
    role_id = uuid.uuid4()
    skill_id = uuid.uuid4()
    posting_id = f"inttest{uuid.uuid4().hex[:12]}"

    pg_session.execute(
        text(
            "INSERT INTO role_catalog (id, name, is_active) "
            "VALUES (:id, :name, true) ON CONFLICT (name) DO NOTHING"
        ),
        {"id": str(role_id), "name": f"Integration Test Role {role_id.hex[:6]}"},
    )
    pg_session.execute(
        text(
            "INSERT INTO skills (id, name) VALUES (:id, :name) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {"id": str(skill_id), "name": f"Integration Test Skill {skill_id.hex[:6]}"},
    )
    pg_session.execute(
        text("""
            INSERT INTO job_postings_unified
                (posting_id, title, role_normalized, seniority, platform,
                 country, posted_date, source_dataset)
            VALUES
                (:pid, :title, :role, 'entry_level', 'linkedin',
                 'PH', '2025-01', 'integration_test')
            ON CONFLICT (posting_id) DO NOTHING
        """),
        {
            "pid": posting_id,
            "title": "Integration Test Engineer",
            "role": f"Integration Test Role {role_id.hex[:6]}",
        },
    )
    pg_session.execute(
        text(
            "INSERT INTO posting_skills (posting_id, skill_id) "
            "VALUES (:pid, :sid) ON CONFLICT DO NOTHING"
        ),
        {"pid": posting_id, "sid": str(skill_id)},
    )
    pg_session.commit()

    yield pg_session, skill_id, role_id

    # Teardown: remove test rows in reverse FK order
    pg_session.execute(
        text("DELETE FROM sdi_snapshots WHERE role_id = :rid"),
        {"rid": str(role_id)},
    )
    pg_session.execute(
        text("DELETE FROM posting_skills WHERE posting_id = :pid"),
        {"pid": posting_id},
    )
    pg_session.execute(
        text("DELETE FROM job_postings_unified WHERE posting_id = :pid"),
        {"pid": posting_id},
    )
    pg_session.execute(
        text("DELETE FROM skills WHERE id = :id"),
        {"id": str(skill_id)},
    )
    pg_session.execute(
        text("DELETE FROM role_catalog WHERE id = :id"),
        {"id": str(role_id)},
    )
    pg_session.commit()


def test_run_sdi_refresh_writes_snapshot(seeded_session) -> None:
    """Snapshots are written when valid seed data is present."""
    from modules.analytics_sdi.service import run_sdi_refresh

    db, _skill_id, _role_id = seeded_session
    count = run_sdi_refresh(db, scope="ph", country_filter="PH")
    assert count > 0, "Expected at least one snapshot to be written"


def test_run_sdi_refresh_is_idempotent(seeded_session) -> None:
    """Re-running does not increase the snapshot row count in the database."""
    from modules.analytics_sdi.service import run_sdi_refresh

    db, _skill_id, role_id = seeded_session

    run_sdi_refresh(db, scope="ph", country_filter="PH")
    row_count_before = db.execute(
        text("SELECT COUNT(*) FROM sdi_snapshots WHERE role_id = :rid"),
        {"rid": str(role_id)},
    ).scalar()

    run_sdi_refresh(db, scope="ph", country_filter="PH")
    row_count_after = db.execute(
        text("SELECT COUNT(*) FROM sdi_snapshots WHERE role_id = :rid"),
        {"rid": str(role_id)},
    ).scalar()

    assert row_count_after == row_count_before, (
        f"Row count changed on re-run: {row_count_before} → {row_count_after}"
    )


def test_run_sdi_refresh_updates_computed_at(seeded_session) -> None:
    """computed_at is refreshed on every re-run, not frozen at the first insert.

    Validates the BLOCKER fix: explicit 'computed_at = now()' in DO UPDATE SET,
    because SQLAlchemy onupdate hooks do not fire for raw SQL execution.
    """
    from modules.analytics_sdi.service import run_sdi_refresh

    db, _skill_id, role_id = seeded_session

    run_sdi_refresh(db, scope="ph", country_filter="PH")
    first_computed_at = db.execute(
        text(
            "SELECT computed_at FROM sdi_snapshots "
            "WHERE role_id = :rid ORDER BY computed_at ASC LIMIT 1"
        ),
        {"rid": str(role_id)},
    ).scalar()

    # Sleep to guarantee a measurable timestamp difference
    time.sleep(1.1)

    run_sdi_refresh(db, scope="ph", country_filter="PH")
    second_computed_at = db.execute(
        text(
            "SELECT computed_at FROM sdi_snapshots "
            "WHERE role_id = :rid ORDER BY computed_at ASC LIMIT 1"
        ),
        {"rid": str(role_id)},
    ).scalar()

    assert second_computed_at > first_computed_at, (
        f"computed_at was not updated on re-run: "
        f"first={first_computed_at}, second={second_computed_at}"
    )


def test_run_sdi_refresh_raises_on_invalid_scope(seeded_session) -> None:
    """ValueError is raised immediately for unrecognised scope values."""
    from modules.analytics_sdi.service import run_sdi_refresh

    db, _skill_id, _role_id = seeded_session
    with pytest.raises(ValueError, match="Unknown scope"):
        run_sdi_refresh(db, scope="invalid_scope", country_filter=None)

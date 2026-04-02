"""Integration tests for normalization.run_normalization.

These tests require a real PostgreSQL database and minimum seed data.
They are skipped in the default SQLite unit test run.

To run locally:

    $env:RUN_INTEGRATION_TESTS = "1"
    $env:DATABASE_URL = "postgresql://user:password@localhost:5432/fctc_test"
    .venv\\Scripts\\pytest.exe tests/test_normalization_integration.py -v -m integration

The test database must have the full schema applied (run migrations first).
Each test seeds its own data and cleans up after itself.
"""

from __future__ import annotations

import os
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
def seeded_normalization_session(pg_session: Session):
    """Seed minimum rows for normalization tests and clean up after.

    Seeds one skill, one alias, and three postings whose titles and skills
    columns mention the seeded skill so the matcher can resolve them.

    Yields:
        Tuple of (session, skill_id UUID, list[posting_id str]).
    """
    skill_id = uuid.uuid4()
    skill_name = f"IntegTestSkill{skill_id.hex[:6]}"
    alias_text = f"integtestalias{skill_id.hex[:6]}"
    posting_ids = [f"normit{uuid.uuid4().hex[:14]}" for _ in range(3)]

    pg_session.execute(
        text(
            "INSERT INTO skills (id, name) VALUES (:id, :name) "
            "ON CONFLICT (name) DO NOTHING"
        ),
        {"id": str(skill_id), "name": skill_name},
    )
    pg_session.execute(
        text(
            "INSERT INTO skill_aliases (alias, skill_id) "
            "VALUES (:alias, :skill_id) ON CONFLICT (alias) DO NOTHING"
        ),
        {"alias": alias_text, "skill_id": str(skill_id)},
    )

    for pid in posting_ids:
        pg_session.execute(
            text("""
                INSERT INTO job_postings_unified
                    (posting_id, title, role_normalized, skills, seniority,
                     platform, country, posted_date, source_dataset)
                VALUES
                    (:pid, :title, 'software engineer', :skills, 'entry_level',
                     'linkedin', 'PH', '2025-01', 'integration_test')
                ON CONFLICT (posting_id) DO NOTHING
            """),
            {
                "pid": pid,
                "title": f"Engineer with {skill_name} skills",
                # skills column uses the alias so both extraction paths are exercised
                "skills": alias_text,
            },
        )
    pg_session.commit()

    yield pg_session, skill_id, posting_ids

    # Teardown: remove test rows in reverse FK order
    for pid in posting_ids:
        pg_session.execute(
            text("DELETE FROM posting_skills WHERE posting_id = :pid"),
            {"pid": pid},
        )
        pg_session.execute(
            text("DELETE FROM job_postings_unified WHERE posting_id = :pid"),
            {"pid": pid},
        )
    pg_session.execute(
        text("DELETE FROM skill_aliases WHERE skill_id = :id"),
        {"id": str(skill_id)},
    )
    pg_session.execute(
        text("DELETE FROM skills WHERE id = :id"),
        {"id": str(skill_id)},
    )
    pg_session.commit()


def test_run_normalization_inserts_posting_skills(seeded_normalization_session) -> None:
    """run_normalization writes posting_skills rows for seeded postings."""
    from modules.normalization.pipeline import run_normalization

    db, _skill_id, posting_ids = seeded_normalization_session

    result = run_normalization(db)

    assert result["processed"] >= len(posting_ids), (
        f"Expected at least {len(posting_ids)} postings processed, got {result['processed']}"
    )
    assert result["skills_extracted"] > 0, "Expected at least one skill to be extracted"

    row_count = db.execute(
        text(
            "SELECT COUNT(*) FROM posting_skills "
            "WHERE posting_id = ANY(:ids)"
        ),
        {"ids": posting_ids},
    ).scalar()
    assert row_count > 0, "Expected posting_skills rows to exist after normalization"


def test_run_normalization_idempotent(seeded_normalization_session) -> None:
    """Running run_normalization twice does not change posting_skills row count.

    Validates AC-4: second run returns skills_extracted=0 for already-processed
    postings and the DB row count is unchanged.
    """
    from modules.normalization.pipeline import run_normalization

    db, _skill_id, posting_ids = seeded_normalization_session

    # First run — processes the seeded postings
    first_result = run_normalization(db)
    assert first_result["skills_extracted"] > 0

    row_count_after_first = db.execute(
        text(
            "SELECT COUNT(*) FROM posting_skills "
            "WHERE posting_id = ANY(:ids)"
        ),
        {"ids": posting_ids},
    ).scalar()

    # Second run — all seeded postings already have posting_skills rows
    second_result = run_normalization(db)
    assert second_result["skills_extracted"] == 0, (
        f"Expected 0 new skills on second run, got {second_result['skills_extracted']}"
    )

    row_count_after_second = db.execute(
        text(
            "SELECT COUNT(*) FROM posting_skills "
            "WHERE posting_id = ANY(:ids)"
        ),
        {"ids": posting_ids},
    ).scalar()

    assert row_count_after_second == row_count_after_first, (
        f"Row count changed on re-run: "
        f"{row_count_after_first} → {row_count_after_second}"
    )


def test_run_normalization_row_count_parity(seeded_normalization_session) -> None:
    """posting_skills row count matches resolved skill IDs per posting.

    Spot-checks that every posting in the seed set has at least one
    posting_skills entry after normalization (AC-7).
    """
    from modules.normalization.pipeline import run_normalization

    db, skill_id, posting_ids = seeded_normalization_session

    run_normalization(db)

    for pid in posting_ids:
        count = db.execute(
            text(
                "SELECT COUNT(*) FROM posting_skills "
                "WHERE posting_id = :pid AND skill_id = :sid"
            ),
            {"pid": pid, "sid": str(skill_id)},
        ).scalar()
        assert count >= 1, (
            f"posting_id {pid!r} has no posting_skills row for skill {skill_id}"
        )

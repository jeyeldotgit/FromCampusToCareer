"""Tests for the ingestion module.

Covers:
- core/posting_id  (canonical location after move)
- transformers/role_mapping
- transformers/tech_filter
- transformers/__init__ (seniority map)
- per-source transformers (synthetic DataFrames, no file I/O for core logic)
- loader.py (startup guard, insert, idempotency)
- router.py (POST /admin/jobs/run, GET /admin/pipeline-runs)
- scripts/historical_bootstrap (run() with tmp CSV sources)
"""

from __future__ import annotations

import csv
import uuid
from pathlib import Path

import pandas as pd
import pytest

from core.posting_id import make_posting_id
from modules.ingestion.transformers import map_seniority
from modules.ingestion.transformers.role_mapping import (
    OTHER_ROLE,
    get_all_canonical_roles,
    map_role,
)
from modules.ingestion.transformers.tech_filter import filter_tech_jobs, is_tech_job


# ---------------------------------------------------------------------------
# core/posting_id
# ---------------------------------------------------------------------------


def test_posting_id_is_deterministic() -> None:
    id1 = make_posting_id("src", "123", "Data Analyst", "2025-03")
    id2 = make_posting_id("src", "123", "Data Analyst", "2025-03")
    assert id1 == id2


def test_posting_id_length() -> None:
    pid = make_posting_id("src", None, "Software Engineer", "2025-01")
    assert len(pid) == 20


def test_posting_id_title_case_insensitive() -> None:
    id1 = make_posting_id("src", "1", "Data Analyst", "2025-01")
    id2 = make_posting_id("src", "1", "data analyst", "2025-01")
    assert id1 == id2


def test_posting_id_differs_on_different_inputs() -> None:
    id1 = make_posting_id("src", "A", "Data Analyst", "2025-03")
    id2 = make_posting_id("src", "B", "Data Analyst", "2025-03")
    assert id1 != id2


# ---------------------------------------------------------------------------
# transformers/role_mapping
# ---------------------------------------------------------------------------


def test_map_role_software_engineer() -> None:
    assert map_role("Software Engineer") == "Software Engineer"


def test_map_role_case_insensitive() -> None:
    assert map_role("SOFTWARE ENGINEER") == "Software Engineer"


def test_map_role_data_analyst() -> None:
    assert map_role("Senior Data Analyst") == "Data Analyst"


def test_map_role_data_scientist() -> None:
    assert map_role("Machine Learning Engineer") == "Data Scientist"


def test_map_role_devops() -> None:
    assert map_role("DevOps Engineer") == "DevOps Engineer"


def test_map_role_cloud() -> None:
    assert map_role("AWS Cloud Engineer") == "Cloud Engineer"


def test_map_role_qa() -> None:
    assert map_role("QA Engineer") == "QA Engineer"
    assert map_role("Automation Tester") == "QA Engineer"
    assert map_role("SDET") == "QA Engineer"


def test_map_role_it_support() -> None:
    assert map_role("IT Support Specialist") == "IT Support"
    assert map_role("Helpdesk Technician") == "IT Support"


def test_map_role_web_developer() -> None:
    assert map_role("Frontend Developer") == "Web Developer"
    assert map_role("Full Stack Developer") == "Web Developer"
    assert map_role("React Developer") == "Web Developer"


def test_map_role_mobile() -> None:
    assert map_role("Android Developer") == "Mobile Developer"
    assert map_role("iOS Developer") == "Mobile Developer"


def test_map_role_network_engineer() -> None:
    assert map_role("Network Engineer") == "Network Engineer"
    assert map_role("Systems Administrator") == "Network Engineer"


def test_map_role_database_admin() -> None:
    assert map_role("Database Administrator") == "Database Administrator"
    assert map_role("DBA") == "Database Administrator"


def test_map_role_cybersecurity() -> None:
    assert map_role("Cybersecurity Analyst") == "Cybersecurity Engineer"
    assert map_role("Information Security Engineer") == "Cybersecurity Engineer"


def test_map_role_data_engineer() -> None:
    assert map_role("Data Engineer") == "Data Engineer"
    assert map_role("ETL Developer") == "Data Engineer"


def test_map_role_backend_is_software_engineer() -> None:
    assert map_role("Backend Developer") == "Software Engineer"


def test_map_role_systems_engineer() -> None:
    assert map_role("Systems Architect") == "Systems Engineer"
    assert map_role("Solutions Architect") == "Systems Engineer"


def test_map_role_ux_designer() -> None:
    assert map_role("UX Designer") == "UX Designer"
    assert map_role("UI/UX Engineer") == "UX Designer"


def test_map_role_project_manager() -> None:
    assert map_role("IT Project Manager") == "Project Manager"


def test_map_role_unmatched_returns_other() -> None:
    assert map_role("Chef") == OTHER_ROLE
    assert map_role("Marketing Manager") == OTHER_ROLE
    assert map_role("") == OTHER_ROLE


def test_get_all_canonical_roles_no_duplicates() -> None:
    roles = get_all_canonical_roles()
    assert len(roles) == len(set(roles))


def test_get_all_canonical_roles_minimum_coverage() -> None:
    roles = set(get_all_canonical_roles())
    required = {
        "Software Engineer",
        "Data Analyst",
        "Web Developer",
        "QA Engineer",
        "IT Support",
    }
    assert required.issubset(roles)


# ---------------------------------------------------------------------------
# transformers/tech_filter
# ---------------------------------------------------------------------------


def test_is_tech_job_engineer() -> None:
    assert is_tech_job("Software Engineer") is True


def test_is_tech_job_developer() -> None:
    assert is_tech_job("Frontend Developer") is True


def test_is_tech_job_data_analyst() -> None:
    assert is_tech_job("Data Analyst") is True


def test_is_tech_job_non_tech() -> None:
    assert is_tech_job("Marketing Manager") is False
    assert is_tech_job("Chef") is False
    assert is_tech_job("Sales Representative") is False


def test_is_tech_job_case_insensitive() -> None:
    assert is_tech_job("SOFTWARE DEVELOPER") is True


def test_filter_tech_jobs_keeps_only_tech() -> None:
    df = pd.DataFrame({
        "title": ["Software Engineer", "Marketing Manager", "Data Analyst", "Chef"],
        "country": ["global", "global", "global", "global"],
    })
    result = filter_tech_jobs(df)
    assert set(result["title"]) == {"Software Engineer", "Data Analyst"}


def test_filter_tech_jobs_missing_column_raises() -> None:
    df = pd.DataFrame({"role": ["Software Engineer"]})
    with pytest.raises(ValueError, match="title"):
        filter_tech_jobs(df)


def test_filter_tech_jobs_empty_input() -> None:
    df = pd.DataFrame({"title": []})
    result = filter_tech_jobs(df)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# transformers/__init__ — seniority map
# ---------------------------------------------------------------------------


def test_map_seniority_entry_level() -> None:
    assert map_seniority("Entry level") == "entry_level"
    assert map_seniority("Internship") == "entry_level"
    assert map_seniority("Associate") == "entry_level"


def test_map_seniority_mid() -> None:
    assert map_seniority("Mid-Senior level") == "mid"
    assert map_seniority("Intermediate") == "mid"


def test_map_seniority_senior() -> None:
    assert map_seniority("Director") == "senior"
    assert map_seniority("Executive") == "senior"
    assert map_seniority("Lead") == "senior"


def test_map_seniority_unknown_fallback() -> None:
    assert map_seniority("Not Applicable") == "unknown"
    assert map_seniority("") == "unknown"
    assert map_seniority("SomethingRandom") == "unknown"


# ---------------------------------------------------------------------------
# Transformer unit tests (synthetic DataFrames — no file I/O)
# ---------------------------------------------------------------------------


class TestLinkedin2023Transformer:
    """Unit tests for linkedin_2023_2024 transformer internals."""

    def test_parse_posted_date_valid(self) -> None:
        from modules.ingestion.transformers.linkedin_2023_2024 import _parse_posted_date

        result = _parse_posted_date(1680000000000)
        assert result.count("-") == 1
        year, month = result.split("-")
        assert len(year) == 4
        assert 1 <= int(month) <= 12

    def test_parse_posted_date_invalid(self) -> None:
        from modules.ingestion.transformers.linkedin_2023_2024 import _parse_posted_date

        assert _parse_posted_date("not-a-number") == "1970-01"

    def test_assert_columns_raises_on_missing(self) -> None:
        from modules.ingestion.transformers.linkedin_2023_2024 import _assert_columns

        df = pd.DataFrame({"job_id": ["1"]})
        with pytest.raises(ValueError, match="missing required columns"):
            _assert_columns(df, {"job_id", "title", "original_listed_time"}, "test.csv")


class TestLinkedin1mTransformer:
    """Unit tests for linkedin_1m_2024 transformer internals."""

    def test_parse_date_valid(self) -> None:
        from modules.ingestion.transformers.linkedin_1m_2024 import _parse_date

        assert _parse_date("2024-03-15") == "2024-03"

    def test_parse_date_fallback(self) -> None:
        from modules.ingestion.transformers.linkedin_1m_2024 import _parse_date

        assert _parse_date("") == "2024-01"
        assert _parse_date("nan") == "2024-01"


class TestDataScience2024Transformer:
    """Unit tests for data_science_2024 transformer internals."""

    def test_parse_date_valid(self) -> None:
        from modules.ingestion.transformers.data_science_2024 import _parse_date

        assert _parse_date("2024-07-01") == "2024-07"

    def test_find_postings_file_raises_when_missing(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.data_science_2024 import _find_postings_file

        with pytest.raises(FileNotFoundError):
            _find_postings_file(tmp_path)


class TestOnlineHistoricalTransformer:
    """Unit tests for online_historical transformer internals."""

    def test_parse_date_valid(self) -> None:
        from modules.ingestion.transformers.online_historical import _parse_date

        assert _parse_date("2019-11-05") == "2019-11"

    def test_parse_date_empty_fallback(self) -> None:
        from modules.ingestion.transformers.online_historical import _parse_date

        assert _parse_date("") == "1970-01"

    def test_resolve_col_found(self) -> None:
        from modules.ingestion.transformers.online_historical import _resolve_col

        df = pd.DataFrame({"Title": [], "Company": []})
        assert _resolve_col(df, ["title", "Title"]) == "Title"

    def test_resolve_col_not_found(self) -> None:
        from modules.ingestion.transformers.online_historical import _resolve_col

        df = pd.DataFrame({"Company": []})
        assert _resolve_col(df, ["title", "Title"]) is None

    def test_transform_with_synthetic_csv(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.online_historical import transform

        csv_path = tmp_path / "jobs.csv"
        csv_path.write_text("Title,Company,Date\nSoftware Engineer,ACME,2019-01-15\n")
        result = transform(tmp_path)
        assert len(result) == 1
        assert result.iloc[0]["title"] == "Software Engineer"
        assert result.iloc[0]["platform"] == "historical"
        assert result.iloc[0]["country"] == "global"
        assert result.iloc[0]["posted_date"] == "2019-01"
        assert result.iloc[0]["skills"] == ""

    def test_transform_no_csv_raises(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.online_historical import transform

        with pytest.raises(FileNotFoundError):
            transform(tmp_path)

    def test_transform_missing_title_col_raises(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.online_historical import transform

        csv_path = tmp_path / "jobs.csv"
        csv_path.write_text("Company,Date\nACME,2019-01-15\n")
        with pytest.raises(ValueError, match="title"):
            transform(tmp_path)


class TestPhilippinesTransformer:
    """Unit tests for philippines_kaggle transformer."""

    def test_transform_basic(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.philippines_kaggle import transform

        csv_path = tmp_path / "ph_jobs.csv"
        csv_path.write_text(
            "job_title,date_posted,experience\n"
            "Software Engineer,2023-05-10,Entry level\n"
        )
        result = transform(tmp_path)
        assert len(result) == 1
        assert result.iloc[0]["title"] == "Software Engineer"
        assert result.iloc[0]["country"] == "PH"
        assert result.iloc[0]["platform"] == "jobstreet"
        assert result.iloc[0]["seniority"] == "entry_level"
        assert result.iloc[0]["posted_date"] == "2023-05"

    def test_transform_no_csv_raises(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.philippines_kaggle import transform

        with pytest.raises(FileNotFoundError):
            transform(tmp_path)

    def test_transform_missing_title_col_raises(self, tmp_path: Path) -> None:
        from modules.ingestion.transformers.philippines_kaggle import transform

        csv_path = tmp_path / "jobs.csv"
        csv_path.write_text("company,date\nACME,2023-01-01\n")
        with pytest.raises(ValueError, match="title"):
            transform(tmp_path)


# ---------------------------------------------------------------------------
# loader.py — startup guard, insert, idempotency
# ---------------------------------------------------------------------------


def test_loader_raises_runtime_error_when_csv_missing(db_session, tmp_path: Path) -> None:
    from modules.ingestion.loader import load_historical_batch

    missing_path = tmp_path / "unified_job_postings.csv"
    with pytest.raises(RuntimeError, match="historical_bootstrap"):
        load_historical_batch(db_session, csv_paths=[missing_path])


def test_loader_inserts_rows(db_session, tmp_path: Path) -> None:
    from modules.ingestion.loader import load_historical_batch

    csv_path = tmp_path / "unified_job_postings.csv"
    _write_test_csv(csv_path, rows=3)

    result = load_historical_batch(db_session, csv_paths=[csv_path])
    assert result["inserted"] == 3
    assert result["quarantined"] == 0


def test_loader_idempotent(db_session, tmp_path: Path) -> None:
    from modules.ingestion.loader import load_historical_batch
    from modules.ingestion.models import JobPostingUnified

    csv_path = tmp_path / "unified_job_postings.csv"
    _write_test_csv(csv_path, rows=3)

    r1 = load_historical_batch(db_session, csv_paths=[csv_path])
    assert r1["inserted"] == 3

    count_before = db_session.query(JobPostingUnified).count()
    r2 = load_historical_batch(db_session, csv_paths=[csv_path])
    count_after = db_session.query(JobPostingUnified).count()

    # on_conflict_do_update always returns rowcount=1 (insert or update);
    # true idempotency is that no duplicate rows are created.
    assert count_after == count_before


def test_loader_quarantines_invalid_rows(db_session, tmp_path: Path) -> None:
    from modules.ingestion.loader import load_historical_batch

    csv_path = tmp_path / "unified_job_postings.csv"
    _write_test_csv_with_bad_rows(csv_path)

    result = load_historical_batch(db_session, csv_paths=[csv_path])
    assert result["quarantined"] >= 1


def test_loader_merges_two_csv_files(db_session, tmp_path: Path) -> None:
    """Two non-overlapping CSVs are merged and all rows are inserted."""
    from modules.ingestion.loader import load_historical_batch
    from modules.ingestion.models import JobPostingUnified

    csv_a = tmp_path / "unified_job_postings.csv"
    csv_b = tmp_path / "live_scraped_ph.csv"
    _write_test_csv(csv_a, rows=3)
    _write_test_csv_with_source(csv_b, rows=2, source="live_ph", country="PH")

    result = load_historical_batch(db_session, csv_paths=[csv_a, csv_b])

    assert result["inserted"] == 5
    assert result["quarantined"] == 0
    assert db_session.query(JobPostingUnified).count() == 5


def test_loader_dedup_across_files(db_session, tmp_path: Path) -> None:
    """A posting_id shared across two files produces exactly one DB row.

    CSV A: rows 0, 1, 2  (posting_ids p0, p1, p2)
    CSV B: row 0 repeated (same posting_id p0) + one new row
    Expected DB rows: 4  (p0 from CSV A wins, no duplicate)
    """
    from modules.ingestion.loader import load_historical_batch
    from modules.ingestion.models import JobPostingUnified

    shared_pid = make_posting_id("test", "0", "Software Engineer 0", "2024-01")

    csv_a = tmp_path / "unified_job_postings.csv"
    _write_test_csv(csv_a, rows=3)

    csv_b = tmp_path / "live_scraped_ph.csv"
    _write_test_csv_with_overlap(csv_b, shared_pid=shared_pid)

    load_historical_batch(db_session, csv_paths=[csv_a, csv_b])

    assert db_session.query(JobPostingUnified).count() == 4


# ---------------------------------------------------------------------------
# router.py — admin endpoints
# ---------------------------------------------------------------------------


def test_trigger_pipeline_creates_pending_run(client) -> None:
    token = _get_admin_token(client)
    resp = client.post(
        "/admin/jobs/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


def test_trigger_pipeline_requires_admin(client) -> None:
    token = _get_student_token(client)
    resp = client.post(
        "/admin/jobs/run",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_trigger_pipeline_requires_auth(client) -> None:
    resp = client.post("/admin/jobs/run")
    assert resp.status_code in {401, 403}


def test_list_pipeline_runs_returns_list(client) -> None:
    token = _get_admin_token(client)
    client.post("/admin/jobs/run", headers={"Authorization": f"Bearer {token}"})
    resp = client.get(
        "/admin/pipeline-runs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["status"] == "pending"


def test_list_pipeline_runs_limit(client) -> None:
    token = _get_admin_token(client)
    for _ in range(5):
        client.post("/admin/jobs/run", headers={"Authorization": f"Bearer {token}"})
    resp = client.get(
        "/admin/pipeline-runs?limit=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ---------------------------------------------------------------------------
# bootstrap run() integration (synthetic tmp sources)
# ---------------------------------------------------------------------------


def test_bootstrap_run_produces_csv(tmp_path: Path) -> None:
    """Bootstrap run() with a single synthetic source writes a valid CSV."""
    import unittest.mock as mock
    import scripts.historical_bootstrap as bootstrap

    source_dir = tmp_path / "raw" / "kaggle" / "online_historical"
    source_dir.mkdir(parents=True)
    (source_dir / "jobs.csv").write_text(
        "Title,Date\n"
        "Software Engineer,2022-06-01\n"
        "Chef,2022-06-02\n"
        "Data Analyst,2022-06-03\n"
    )

    output_path = tmp_path / "processed" / "unified_job_postings.csv"

    mock_settings = mock.MagicMock()
    mock_settings.raw_data_path = str(tmp_path / "raw")
    mock_settings.processed_data_path = str(tmp_path / "processed")
    with mock.patch("scripts.historical_bootstrap.settings", mock_settings):
        result = bootstrap.run(output_path=output_path, dry_run=False)

    assert output_path.exists()
    assert len(result) >= 1
    titles = set(result["title"].values)
    assert titles & {"Software Engineer", "Data Analyst"}
    for col in ["posting_id", "title", "role_normalized", "seniority", "platform",
                "country", "posted_date", "source_dataset"]:
        assert col in result.columns


def test_bootstrap_filters_non_tech(tmp_path: Path) -> None:
    """Non-tech titles are removed by the tech filter."""
    import unittest.mock as mock
    import scripts.historical_bootstrap as bootstrap

    source_dir = tmp_path / "raw" / "kaggle" / "online_historical"
    source_dir.mkdir(parents=True)
    (source_dir / "jobs.csv").write_text(
        "Title,Date\n"
        "Chef,2022-06-01\n"
        "Marketing Manager,2022-06-02\n"
    )
    output_path = tmp_path / "processed" / "out.csv"

    mock_settings = mock.MagicMock()
    mock_settings.raw_data_path = str(tmp_path / "raw")
    mock_settings.processed_data_path = str(tmp_path / "processed")
    with mock.patch("scripts.historical_bootstrap.settings", mock_settings):
        result = bootstrap.run(output_path=output_path, dry_run=True)

    assert len(result) == 0


def test_bootstrap_posting_ids_are_unique(tmp_path: Path) -> None:
    """All posting_ids in the output are unique."""
    import unittest.mock as mock
    import scripts.historical_bootstrap as bootstrap

    source_dir = tmp_path / "raw" / "kaggle" / "online_historical"
    source_dir.mkdir(parents=True)
    rows = "\n".join(
        f"Software Engineer {i},2022-0{(i % 9) + 1}-01" for i in range(1, 10)
    )
    (source_dir / "jobs.csv").write_text(f"Title,Date\n{rows}\n")
    output_path = tmp_path / "processed" / "out.csv"

    mock_settings = mock.MagicMock()
    mock_settings.raw_data_path = str(tmp_path / "raw")
    mock_settings.processed_data_path = str(tmp_path / "processed")
    with mock.patch("scripts.historical_bootstrap.settings", mock_settings):
        result = bootstrap.run(output_path=output_path, dry_run=True)

    if len(result) > 0:
        assert result["posting_id"].nunique() == len(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_test_csv(path: Path, rows: int = 3) -> None:
    """Write a valid canonical CSV for loader tests."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "posting_id", "title", "role_normalized", "skills",
                "seniority", "platform", "country", "posted_date", "source_dataset",
            ],
        )
        writer.writeheader()
        for i in range(rows):
            pid = make_posting_id("test", str(i), f"Software Engineer {i}", "2024-01")
            writer.writerow({
                "posting_id": pid,
                "title": f"Software Engineer {i}",
                "role_normalized": "Software Engineer",
                "skills": "Python,SQL",
                "seniority": "entry_level",
                "platform": "linkedin",
                "country": "global",
                "posted_date": "2024-01",
                "source_dataset": "test",
            })


def _write_test_csv_with_bad_rows(path: Path) -> None:
    """Write a CSV that contains one invalid row (missing title)."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "posting_id", "title", "role_normalized", "skills",
                "seniority", "platform", "country", "posted_date", "source_dataset",
            ],
        )
        writer.writeheader()
        pid_good = make_posting_id("test", "1", "Data Analyst", "2024-01")
        writer.writerow({
            "posting_id": pid_good,
            "title": "Data Analyst",
            "role_normalized": "Data Analyst",
            "skills": "",
            "seniority": "entry_level",
            "platform": "linkedin",
            "country": "global",
            "posted_date": "2024-01",
            "source_dataset": "test",
        })
        pid_bad = make_posting_id("test", "2", "", "2024-01")
        writer.writerow({
            "posting_id": pid_bad,
            "title": "",
            "role_normalized": "Data Analyst",
            "skills": "",
            "seniority": "entry_level",
            "platform": "linkedin",
            "country": "global",
            "posted_date": "2024-01",
            "source_dataset": "test",
        })


def _write_test_csv_with_source(
    path: Path,
    rows: int,
    source: str,
    country: str = "global",
) -> None:
    """Write a valid canonical CSV with a custom source_dataset and country.

    Row indices start at 100 to avoid posting_id collisions with _write_test_csv.
    """
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "posting_id", "title", "role_normalized", "skills",
                "seniority", "platform", "country", "posted_date", "source_dataset",
            ],
        )
        writer.writeheader()
        for i in range(100, 100 + rows):
            pid = make_posting_id(source, str(i), f"Data Analyst {i}", "2024-06")
            writer.writerow({
                "posting_id": pid,
                "title": f"Data Analyst {i}",
                "role_normalized": "Data Analyst",
                "skills": "SQL,Excel",
                "seniority": "entry_level",
                "platform": "jobstreet",
                "country": country,
                "posted_date": "2024-06",
                "source_dataset": source,
            })


def _write_test_csv_with_overlap(path: Path, shared_pid: str) -> None:
    """Write a CSV containing one row with shared_pid and one unique new row.

    Used to verify that dedup on posting_id keeps the first-file row.
    """
    unique_pid = make_posting_id("live_ph", "999", "Network Engineer", "2024-06")
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "posting_id", "title", "role_normalized", "skills",
                "seniority", "platform", "country", "posted_date", "source_dataset",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "posting_id": shared_pid,
            "title": "Software Engineer 0",
            "role_normalized": "Software Engineer",
            "skills": "Python",
            "seniority": "entry_level",
            "platform": "jobstreet",
            "country": "PH",
            "posted_date": "2024-01",
            "source_dataset": "live_ph",
        })
        writer.writerow({
            "posting_id": unique_pid,
            "title": "Network Engineer",
            "role_normalized": "Network Engineer",
            "skills": "",
            "seniority": "mid",
            "platform": "jobstreet",
            "country": "PH",
            "posted_date": "2024-06",
            "source_dataset": "live_ph",
        })


def _get_admin_token(client) -> str:
    client.post(
        "/auth/register",
        json={
            "email": "admin@test.com",
            "password": "AdminPass123!",
            "full_name": "Test Admin",
            "role": "admin",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]


def _get_student_token(client) -> str:
    client.post(
        "/auth/register",
        json={
            "email": "student@test.com",
            "password": "StudentPass123!",
            "full_name": "Test Student",
            "role": "student",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "student@test.com", "password": "StudentPass123!"},
    )
    return resp.json()["access_token"]

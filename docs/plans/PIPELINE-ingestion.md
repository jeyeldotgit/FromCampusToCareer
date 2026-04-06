# PIPELINE-ingestion

## Purpose

This document is the single source of truth for the **ingestion** stage of the ETL chain.

Ingestion is responsible for loading **canonical job posting rows** into
`job_postings_unified` from one or more **processed CSV files** on disk. It does
not extract skills into `posting_skills` (that is the normalization pipeline)
and does not compute SDI (that is `analytics_sdi`).

---

## Position in the Pipeline

```
[offline bootstrap]   raw Kaggle CSVs ──► transformers ──► unified CSV(s)
                                                              │
[1. ingestion]        processed *.csv ──► job_postings_unified    ← this module
[2. normalization]    job_postings_unified ──► posting_skills
[3. analytics_sdi]    posting_skills + job_postings_unified ──► sdi_snapshots
```

Step 1 is executed by `worker.py` after an admin creates a pending run via
`POST /admin/jobs/run`. The offline bootstrap is a **prerequisite** for the
default worker path when only `unified_job_postings.csv` exists.

---

## Two Entry Points

| Entry point | When | Output |
|-------------|------|--------|
| **`scripts/historical_bootstrap.py`** | One-time or when raw sources change | Writes `data/processed/unified_job_postings.csv` (or `--output` path) from raw Kaggle folders under `data/raw/kaggle/` |
| **`load_historical_batch`** in `modules/ingestion/loader.py` | Every worker run (Step 1) | Upserts rows into `job_postings_unified` |

Bootstrap **builds** the canonical CSV; the loader **reads** it into PostgreSQL.
You typically run bootstrap before the first pipeline run, then re-run the worker
when the CSV is updated.

---

## Canonical CSV Schema

Every processed file consumed by the loader must contain exactly these columns
(see `CANONICAL_COLUMNS` in `loader.py`):

| Column | Type (in CSV) | Notes |
|--------|---------------|--------|
| `posting_id` | string | 20-char deterministic ID; primary key in DB |
| `title` | string | Non-empty after trim |
| `role_normalized` | string | Must match a `role_catalog.name` for SDI joins |
| `skills` | string | Optional; comma-separated keywords for normalization text |
| `seniority` | enum | One of: `entry_level`, `mid`, `senior`, `unknown` |
| `platform` | enum | One of: `linkedin`, `indeed`, `jobstreet`, `kalibrr`, `historical` |
| `country` | enum | One of: `PH`, `US`, `global` |
| `posted_date` | string | `YYYY-MM` |
| `source_dataset` | string | Provenance label (e.g. `online_historical_kaggle`) |

Missing columns cause the file to be **skipped** with a schema error; the load
aborts if **all** files fail validation.

---

## Bootstrap Pipeline (`historical_bootstrap.py`)

**Location:** `backend/scripts/historical_bootstrap.py`

For each configured Kaggle subdirectory under `settings.raw_data_path/kaggle/`,
the script calls the matching `transform(source_dir) -> pd.DataFrame` in
`modules/ingestion/transformers/`. Each transformer returns a frame with the 9
canonical columns (except `posting_id` / `role_normalized` may be filled in
later steps — see per-source notes in `transformers/column_mappings.md`).

High-level flow:

1. **Concatenate** all non-empty source frames.
2. **`filter_tech_jobs`** — keep rows whose title matches tech keywords
   (`transformers/tech_filter.py`).
3. **`map_role`** — derive `role_normalized` from title
   (`transformers/role_mapping.py`).
4. **`make_posting_id`** — SHA-1 based deterministic ID
   (`core/posting_id.py`).
5. **`drop_duplicates`** on `posting_id` (first wins).
6. **Quality gates** — align with loader rules (title, date, seniority,
   country, non-empty role, not `Other`).
7. **Sort** by `posted_date` and **write CSV** (unless `--dry-run`).

Per-source column and file expectations are documented in
[`transformers/column_mappings.md`](../../modules/ingestion/transformers/column_mappings.md).

---

## Runtime Loader (`load_historical_batch`)

**Location:** `modules/ingestion/loader.py`

### Inputs

- **`csv_paths`**: Explicit list of `Path` objects. If `None`, defaults to
  `[processed_data_path / "unified_job_postings.csv"]` from settings.
- **`worker.py`** passes **every `*.csv`** in `settings.processed_data_path`
  (sorted by name), so additional files (e.g. `ict_postings_2020_2025.csv`) are
  merged in one load step.

### Merge and deduplication

1. Read each existing file with `pandas.read_csv(..., dtype=str, keep_default_na=False)`.
2. **Concatenate** all frames.
3. **`drop_duplicates(subset=["posting_id"], keep="first")`** — earlier files in
   the concatenation order win. With sorted glob order, lexicographically first
   filename wins on collision.

### Row validation (`_validate_row`)

A row is **quarantined** (logged, not loaded) if any of:

- empty `title`
- `posted_date` not `YYYY-MM` with month 1–12
- `seniority` not in `VALID_SENIORITY`
- `country` not in `VALID_COUNTRIES`
- empty `role_normalized`

### Database write

Valid rows are bulk-inserted via PostgreSQL **`INSERT ... ON CONFLICT (posting_id) DO UPDATE`**
(`sqlalchemy.dialects.postgresql.insert`). The **only** column updated on conflict
is **`skills`** — so re-ingesting the same posting refreshes the raw skills text
without rewriting the rest of the row.

### Return value

```python
{"inserted": <rowcount from executemany/execute>, "skipped": 0, "quarantined": <count>}
```

(`skipped` is reserved; currently unused in the bulk path.)

---

## Pipeline Runs and Admin API

**Model:** `PipelineRun` (`modules/ingestion/models.py`) — table `pipeline_runs`.

| Endpoint | Behavior |
|----------|----------|
| `POST /admin/jobs/run` | Inserts `status='pending'`; returns 202. Does **not** run ingestion. |
| `GET /admin/pipeline-runs` | Lists recent runs (admin JWT required). |

The worker (`worker.py`) selects the oldest pending run, sets `running`, executes
ingestion → normalization → SDI, then `completed` or `failed` with `error_message`.

---

## Deterministic `posting_id`

**Rule** (`core/posting_id.py`):

```
base = f"{source_dataset}|{native_id or ''}|{title.strip().lower()}|{posted_date}"
posting_id = sha1(base).hexdigest()[:20]
```

Changing the formula without a migration plan breaks deduplication and SDI
counts. Keep bootstrap and any live scraper aligned with this contract.

---

## Configuration

From `core.config` / `.env`:

| Setting | Role |
|---------|------|
| `PROCESSED_DATA_PATH` | Directory containing CSVs for `load_historical_batch` |
| `RAW_DATA_PATH` | Root for `historical_bootstrap.py` (`kaggle/` subfolders) |

---

## Operational Checklist

1. Place raw Kaggle files under `data/raw/kaggle/<source>/` per
   `column_mappings.md`.
2. Run `python scripts/historical_bootstrap.py` from `backend/` (or `--dry-run`
   first).
3. `POST /admin/jobs/run`, then `python worker.py` from `backend/`.
4. Confirm `pipeline_runs` shows `completed` and row counts in logs.

---

## Cross-Reference Rule

If you change **canonical columns**, **validation enums**, or **upsert behavior**
in `loader.py`, update this document and any bootstrap validation in
`historical_bootstrap.py` that is intended to stay in parity (`_validate_rows`).

---

## Related Documents

- [`PIPELINE-normalization.md`](PIPELINE-normalization.md) — next stage
- [`PIPELINE-analytics_sdi.md`](PIPELINE-analytics_sdi.md) — SDI after `posting_skills` exists
- [`modules/ingestion/transformers/column_mappings.md`](../../modules/ingestion/transformers/column_mappings.md) — per-source column maps

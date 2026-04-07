# REVIEW-SIGNOFF-ingestion-2026-03-29

**Input plan:** ARCH-PLAN-ingestion-2026-03-29  
**Reviewer role:** backend-reviewer  
**Date:** 2026-03-29

---

## Verdict: APPROVED WITH CONDITIONS

The module boundary is mostly coherent, the ETL flow is valid, and the sync-only Stage 1 decision is correct. However, four issues must be resolved before the engineer writes a single line of transformer code. Two are hard blockers that will produce silent data corruption or a broken demo if skipped.

---

## Required Changes (engineer may not start until all are resolved)

### BLOCKER 1 — Kaggle CSV column headers must be inspected and documented first

The plan lists this only as a risk footnote. It must be a hard pre-condition.

All five Kaggle datasets must be downloaded and their actual column headers inspected before any transformer is written. If a transformer assumes `job_id` and the actual column is `Job ID` or `id`, it will silently produce an empty DataFrame. There will be no error — just zero rows in `unified_job_postings.csv` and zero rows loaded into the DB.

**Required gate:** Before any transformer code is written, produce a reference document (e.g., `transformers/column_mappings.md`) containing the actual column names from each CSV and their mapping to the canonical 9-column schema. The engineer does not begin coding transformers until this document exists and is reviewed.

---

### BLOCKER 2 — Tech-field filter is absent from the plan

The plan does not mention filtering job postings to tech/IT roles. This is a significant gap.

The LinkedIn 2023-2024 and 1.3M LinkedIn Kaggle datasets span all industries — marketing, finance, healthcare, legal, manufacturing. If the bootstrap ingests all of them:

- The DB will contain millions of irrelevant rows
- SDI computation will group over hundreds of non-tech role strings
- The five target PH IT roles will be buried in noise and produce meaningless SDI values
- The demo will fail to show meaningful gap analysis for a BSIT/BSCS student

**Required before transformer design is finalized:** Define the filter criteria for "tech job." A keyword-based title filter is sufficient for Stage 1 — for example, include only postings whose `title` contains terms like `engineer`, `developer`, `analyst`, `data`, `software`, `IT`, `systems`, `network`, `QA`, `DevOps`, `cloud`, `security`. Specify where the filter is applied in the transformer pipeline (transformer output, or a shared filter step in `historical_bootstrap.py` before concatenation). This filter must be documented in the plan before the engineer starts.

---

### REQUIRED CHANGE 3 — `role_normalized` as raw title will break the demo

The plan acknowledges this as a risk but does not require a mitigation. The severity is understated.

`analytics_sdi` groups by `role_normalized`. With raw titles like `"Senior Software Engineer III"`, `"SWE - Backend"`, `"Software Engineer (New Grad)"` all as distinct values, no meaningful SDI snapshot will exist for any of the five target roles. Gap analysis will return empty results. The demo cannot proceed.

SBERT is not required for Stage 1. A simple keyword-based mapping dictionary is sufficient:

```
"data analyst"           → "Data Analyst"
"software engineer"      → "Software Engineer"
"web developer"          → "Web Developer"
"qa engineer"            → "QA Engineer"
"it support"             → "IT Support"
...
```

**Required:** The plan must specify that the bootstrap applies a minimum title-to-role mapping before writing the CSV. Titles that do not match any canonical role are assigned `"Other"` and excluded from SDI computation. This does not need to be SBERT — a keyword match dict covering the five target roles is the MVP floor. The engineer must not write `historical_bootstrap.py` until this mapping strategy is specified.

---

### REQUIRED CHANGE 4 — `posting_id.py` cross-module boundary violation

`historical_bootstrap.py` (inside `modules/ingestion/`) would import `make_posting_id` from `modules/normalization/posting_id.py`. This creates an `ingestion → normalization` import dependency.

`normalization` already consumes data produced by `ingestion` (reads `job_postings_unified`). If `ingestion` also imports from `normalization`, the conceptual dependency runs in both directions. This is a hidden coupling that will cause import errors or circular dependency issues as the modules grow.

`posting_id.py` is a pure utility — no database access, no external imports, just `hashlib`. It belongs in `core/`, not in `normalization/`.

**Required:** Move `normalization/posting_id.py` to `core/posting_id.py` (or `core/utils.py`). Both `ingestion` and `normalization` import from `core/`. No circular dependency.

---

## Simplifications (must be addressed, not ignored)

### Simplification 1 — Drop `job_type` from `pipeline_runs` in Stage 1

In Stage 1 there is exactly one pipeline job: `historical_bootstrap` → `load_historical_batch`. Adding a `job_type` column now is premature generalization. The column adds a migration, a model change, and validation logic for zero practical benefit.

**Action:** Remove the `job_type` schema change from Stage 1 scope. Add it in Stage 2 when `ph_live_ingest` is actually built.

---

### Simplification 2 — Move `historical_bootstrap.py` to `backend/scripts/`

Placing `historical_bootstrap.py` inside `modules/ingestion/` implies it is part of the module's callable API. It is not — it is a one-time offline data preparation script that runs before the backend is started. Putting it in `modules/ingestion/` will confuse future engineers about whether it is part of the worker chain.

**Action:** Place the script at `backend/scripts/historical_bootstrap.py`. The `transformers/` subpackage stays inside `modules/ingestion/` because the loader may reference those transforms later.

---

### Simplification 3 — Startup guard must be code, not a README note

The plan proposes "a startup check or README step" to handle the critical bootstrap-precedes-worker dependency. A README note is not a mitigation — it will be missed.

**Action:** Add a guard in `load_historical_batch()` (or at the top of `worker.py`) that checks for the existence of `unified_job_postings.csv` at startup and raises a `RuntimeError` with a clear message:

```
RuntimeError: unified_job_postings.csv not found at data/processed/.
Run `python scripts/historical_bootstrap.py` first.
```

This turns a confusing mid-pipeline `FileNotFoundError` into an immediately actionable error.

---

## Findings That Are Acceptable (no change required)

- **Folder structure** is clean and scalable. Stage 2 scrapers slot in without restructuring.
- **Sync-only Stage 1** is correct. No Celery, no threads.
- **`pipeline_run_logs` deferred to Stage 2** — correct call for MVP.
- **`data/` inside `backend/`** — already covered by `.gitignore` (`data/raw/`, `data/processed/` with `.gitkeep` placeholders). No issue.
- **Skills from Kaggle CSVs discarded by normalization** — plan correctly notes this as a known gap. Preserving the raw `skills` column in the CSV is the right audit strategy. Acceptable for Stage 1.
- **`indeed` in VALID_PLATFORMS enum** — minor inconsistency, not a blocker. Can be cleaned up when transformer outputs are known.

---

## Pre-Start Checklist for Engineer

The following must be complete before the engineer writes any code:

- [ ] All 5 Kaggle datasets downloaded and placed under `data/raw/kaggle/<source>/`
- [ ] Actual CSV column headers inspected; `transformers/column_mappings.md` written
- [ ] Tech-field filter criteria defined and added to the plan
- [ ] `role_normalized` mapping strategy defined (keyword dict, minimum 5 target roles)
- [ ] `posting_id.py` moved to `core/` in a prior commit
- [ ] `job_type` removed from Stage 1 scope
- [ ] `historical_bootstrap.py` target location confirmed as `backend/scripts/`
- [ ] Startup guard spec added to `loader.py` or `worker.py` task

Engineer may begin transformer implementation only after all items above are checked.

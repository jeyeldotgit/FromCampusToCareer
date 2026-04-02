# PIPELINE-normalization

## Purpose

This document is the single source of truth for the normalization pipeline.

The normalization pipeline is **Stage 2 of the ETL chain**. It reads raw job
postings from `job_postings_unified`, extracts skill mentions using a
rule-based spaCy PhraseMatcher, resolves them to canonical skill UUIDs via the
taxonomy alias map, and writes the resulting associations into `posting_skills`.

Without populated `posting_skills` rows, the SDI computation pipeline
(`run_sdi_refresh`) has no skill frequency data to aggregate and produces
zero/null SDI values for all roles.

---

## Position in the Pipeline

```
[1. ingestion]        CSV files ──► job_postings_unified
[2. normalization]    job_postings_unified ──► posting_skills    ← this module
[3. analytics_sdi]   posting_skills + job_postings_unified ──► sdi_snapshots
```

All three stages are triggered sequentially by `worker.py` as a single
synchronous pipeline run, gated by a `pipeline_runs` status row.

---

## ETL Pattern

The normalization pipeline follows an **incremental ETL** pattern:

| Phase | What happens |
|---|---|
| **Extract** | Query `job_postings_unified` for posting IDs with no `posting_skills` entry; load taxonomy patterns from `skills` and `skill_aliases` tables |
| **Transform** | Run spaCy PhraseMatcher on `title + skills` text; resolve matched canonical names to UUIDs via alias map |
| **Load** | Bulk-upsert `(posting_id, skill_id)` pairs into `posting_skills` with `ON CONFLICT DO NOTHING` |

The pipeline is **idempotent**: a posting is only processed when it has zero
rows in `posting_skills`. Re-running on already-processed data inserts nothing.

---

## Data Flow

```
job_postings_unified
        │
        │  SELECT posting_id WHERE NOT EXISTS (posting_skills row)
        ▼
unprocessed_ids: list[str]    ← one cheap query, IDs only
        │
        │  _iter_chunks(CHUNK_SIZE=2000)
        ▼
chunk_ids: list[str]
        │
        │  SELECT posting_id, title, skills WHERE posting_id IN :ids
        ▼
chunk_rows
        │
        │  nlp.pipe(texts, batch_size=512)
        ▼
spaCy docs (batched)
        │
        │  extract_skills_from_doc → normalize_skill_set
        ▼
skill_rows: list[{posting_id, skill_id}]
        │
        │  accumulate; flush when len >= BULK_INSERT_SIZE=1000
        ▼
_bulk_insert_posting_skills
        │
        │  db.commit() once per chunk
        ▼
posting_skills (DB table)
```

---

## Chunking Strategy

### Why two-step ID-first chunking?

Using `LIMIT/OFFSET` pagination on a live-write table produces a
correctness bug: as each chunk is processed and `posting_skills` rows are
inserted, the `WHERE NOT EXISTS` filter causes the effective result set
to shrink. Subsequent `OFFSET` values then skip rows that were in the
original result set.

The safe pattern is:
1. Fetch all unprocessed `posting_id` values into a Python list upfront
   (one query, returns IDs only — cheap even at 100k rows).
2. Slice that fixed list in Python using `_iter_chunks`.
3. For each chunk, fetch full row data via `WHERE posting_id IN :ids`.

Because the ID list is fixed in memory, live writes cannot affect which
rows are processed.

### Constants

| Constant | Value | Purpose |
|---|---|---|
| `CHUNK_SIZE` | 2000 | Number of posting IDs processed per iteration |
| `BULK_INSERT_SIZE` | 1000 | Number of `(posting_id, skill_id)` rows per bulk insert statement |

---

## NLP Extraction

The PhraseMatcher is rule-based, not transformer-based. This keeps
extraction deterministic and fast at scale.

**`build_matcher(skill_patterns)`** — builds the matcher once per pipeline run
from a `{lowercase_pattern: canonical_name}` dict. Both canonical skill names
and all alias variants are registered as patterns under the canonical name
label.

**`extract_skills_from_doc(doc, matcher)`** — accepts a pre-built spaCy `Doc`
returned by `nlp.pipe()`. Used by the pipeline for batch processing.

**`extract_skills(text, nlp, matcher)`** — original per-text function. Kept
for backward compatibility and unit tests. Not used by the production pipeline
loop.

The spaCy model is cached with `@lru_cache(maxsize=1)` and loaded once per
process.

---

## Commit Cadence

| When | What |
|---|---|
| After each chunk of `CHUNK_SIZE` postings | `db.commit()` — commits all skill rows accumulated for that chunk |
| After the final flush of remaining rows | `db.commit()` |
| Inside `_bulk_insert_posting_skills` | **Never** — the helper only executes; the caller owns commit |

Committing once per chunk (not per row, not per skill) balances transaction
size against memory pressure. A failed run mid-pipeline leaves already-committed
chunks intact; those postings are skipped on the next run.

---

## Known Limitations

### Unknown skills are discarded

`normalize_skill_set` returns an `unknown` set of skill strings that had no
match in the alias map. These are counted in the pipeline return dict
(`unknown_flagged`) but are not persisted. There is no table, queue, or admin
surface for reviewing vocabulary gaps.

**Impact:** Skills mentioned in job postings that are not in the taxonomy
(including aliases) are silently dropped. SDI values for unmapped skills will
be zero.

**Mitigation:** Admins should monitor `unknown_flagged` in pipeline logs and
seed missing skills/aliases via the taxonomy admin API before re-running.

### Re-normalization requires a manual delete

The idempotency check is coarse: any posting with at least one `posting_skills`
row is considered processed and skipped. If the taxonomy grows (new skills or
aliases added), already-processed postings will not be re-evaluated.

To re-normalize all postings after a taxonomy update:

```sql
DELETE FROM posting_skills;
```

Then re-run the worker pipeline. All three stages will execute from scratch.

### Text truncation

spaCy truncates input text at 50,000 characters per document in
`extract_skills()`. The `nlp.pipe()` batch path applies spaCy's internal
default limit. Postings with extremely long descriptions may have trailing
content ignored.

---

## Return Value

`run_normalization(db)` returns:

```python
{
    "processed": int,         # number of postings iterated
    "skills_extracted": int,  # total (posting_id, skill_id) pairs inserted
    "unknown_flagged": int,   # skill strings with no alias map match
}
```

This dict is logged by `worker.py` after Step 2 and can be used to verify
pipeline health.

---

## Testing Strategy

| Layer | File | Requires DB? | What is covered |
|---|---|---|---|
| Unit | `tests/test_normalization.py` | No (SQLite in-memory) | `extract_skills`, `extract_skills_from_doc`, parity, `_iter_chunks`, `_bulk_insert_posting_skills` mock |
| Integration | `tests/test_normalization_integration.py` | Yes (PostgreSQL) | `run_normalization` idempotency, row count parity, posting_skills FK correctness |

Integration tests are skipped unless `RUN_INTEGRATION_TESTS=1` is set.

To run unit tests only:

```
.venv\Scripts\pytest.exe tests/test_normalization.py -v
```

To run integration tests:

```
$env:RUN_INTEGRATION_TESTS = "1"
$env:DATABASE_URL = "postgresql://user:password@localhost:5432/fctc_test"
.venv\Scripts\pytest.exe tests/test_normalization_integration.py -v -m integration
```

---

## Acceptance Criteria

| # | Criterion |
|---|---|
| AC-1 | No `debug-feaa13.log` file is created on pipeline run |
| AC-2 | `run_normalization` completes 22,570 rows in under 20 minutes |
| AC-3 | `posting_skills` row count after run matches pre-refactor baseline |
| AC-4 | Re-running returns `skills_extracted: 0`; no new rows inserted |
| AC-5 | `extract_skills()` old signature still works; existing tests pass |
| AC-6 | `extract_skills_from_doc()` returns identical results to `extract_skills()` for same input |
| AC-7 | No `posting_skills` rows skipped due to chunking (count parity) |

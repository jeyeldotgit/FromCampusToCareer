# PIPELINE-analytics_sdi

## Purpose

This document is the single source of truth for the SDI computation pipeline.
It cross-references the SQL write path and the Python formula reference so they
stay consistent. It also defines the scope model and clarifies where
`decay_factor` applies.

---

## The Rule: Change One, Change Both

> **If you modify the SDI formula in `run_sdi_refresh` (SQL) you MUST also
> update `compute_sdi_snapshots` (Python), and vice versa.**
>
> Run `pytest tests/test_analytics_sdi.py` to confirm the Python formula is
> correct. Run `pytest tests/test_analytics_sdi_integration.py` (with a live
> PostgreSQL instance) to confirm the SQL write path is correct.
>
> Never leave the two implementations expressing different formulas.

---

## SDI Formula

### Definition

For a given (skill, role, period) triple:

```
SDI(skill, role, t) =
    count(DISTINCT posting_id WHERE skill is mentioned, role = role, period = t, seniority = entry_level)
    ──────────────────────────────────────────────────────────────────────────────────────────────────────
    count(DISTINCT posting_id WHERE role = role, period = t, seniority = entry_level)
```

Values are rounded to 4 decimal places. Division by zero produces `NULL` (SQL
`NULLIF`) or is avoided by the `if df.empty` guard in Python.

---

### SQL implementation (production write path)

Located in: `backend/modules/analytics_sdi/service.py` → `_SDI_UPSERT_SQL`

```sql
INSERT INTO sdi_snapshots
    (id, skill_id, role_id, period, sdi_value, posting_count, scope)
SELECT
    gen_random_uuid(),
    ps.skill_id,
    rc.id                                             AS role_id,
    jp.posted_date                                    AS period,
    ROUND(
        COUNT(DISTINCT ps.posting_id)::numeric /
        NULLIF(totals.total_postings, 0),
        4
    )                                                 AS sdi_value,
    COUNT(DISTINCT ps.posting_id)                     AS posting_count,
    :scope                                            AS scope
FROM job_postings_unified jp
JOIN posting_skills ps  ON ps.posting_id    = jp.posting_id
JOIN role_catalog   rc  ON rc.name          = jp.role_normalized
JOIN (
    SELECT role_normalized, posted_date,
           COUNT(DISTINCT posting_id) AS total_postings
    FROM   job_postings_unified
    WHERE  seniority = 'entry_level'
      AND  (:country IS NULL OR country = :country)
    GROUP  BY role_normalized, posted_date
) totals ON totals.role_normalized = jp.role_normalized
        AND totals.posted_date     = jp.posted_date
WHERE jp.seniority = 'entry_level'
  AND (:country IS NULL OR jp.country = :country)
GROUP BY ps.skill_id, rc.id, jp.posted_date
ON CONFLICT ON CONSTRAINT uq_sdi_snapshot
DO UPDATE SET
    sdi_value     = EXCLUDED.sdi_value,
    posting_count = EXCLUDED.posting_count,
    computed_at   = now()
```

**Why `computed_at = now()` is explicit:** SQLAlchemy's `onupdate=func.now()`
ORM hook does not fire when executing raw SQL via `db.execute(text(...))`. The
explicit clause in `DO UPDATE SET` is the only reliable way to refresh the
timestamp on every re-run.

---

### Python implementation (formula reference / unit tests)

Located in: `backend/modules/analytics_sdi/service.py` → `compute_sdi_snapshots`

This function is **not called by the production pipeline**. It is kept as the
authoritative Python specification of the formula so it can be unit-tested
without a database. Any change to the SQL formula must be reflected here.

---

## decay_factor Scope

`decay_factor` is **only used at read time** in `get_weighted_sdi`. It is not
part of the SDI snapshot stored in the database.

| Function | Uses decay_factor? | Purpose |
|---|---|---|
| `compute_sdi_snapshots` | No | Formula reference only |
| `run_sdi_refresh` | No | Writes raw per-period snapshots |
| `get_weighted_sdi` | **Yes** | Applies `0.90^(N - t_index)` weighting across periods at query time |

The weighted formula:

```
SDI_weighted(skill) =
    Σ [SDI(skill, t) × decay_factor^(N - t_index)]
    ─────────────────────────────────────────────────
    Σ [decay_factor^(N - t_index)]
```

Where `N` = total number of distinct periods with snapshots for this role,
and `t_index` is the 1-based chronological index of each period.

---

## Two-Branch Scope Model

The pipeline runs in two scopes:

| scope | country_filter | Purpose |
|---|---|---|
| `ph` | `PH` | Philippine-only snapshots for student-facing gap analysis |
| `global` | `None` | All-country snapshots for Stage 2 decay trend analysis |

`worker.py` triggers both scopes in sequence:

```python
run_sdi_refresh(db, scope="ph", country_filter="PH")
run_sdi_refresh(db, scope="global", country_filter=None)
```

`get_weighted_sdi` defaults to `scope='ph'` and automatically falls back to
`'global'` when the PH scope has no snapshots for a given role.

---

## Unmatched Role Diagnostic

After each upsert, `_log_unmatched_roles` queries for `role_normalized` values
in `job_postings_unified` that have no matching row in `role_catalog`. These
postings are silently excluded from SDI computation.

Admin must review `WARNING` log entries with the key
`"Unmatched role_normalized excluded from SDI snapshots"` after each pipeline
run to identify gaps in the role taxonomy.

---

## Data Dependencies

```
job_postings_unified  ──┐
                        ├──► run_sdi_refresh ──► sdi_snapshots
posting_skills        ──┤
role_catalog          ──┘

sdi_snapshots ──► get_weighted_sdi ──► gap_and_roadmap (API)
sdi_snapshots ──► analytics_decay  (Stage 2, reads directly via SQL)
```

`sdi_snapshots` must be populated before `get_weighted_sdi` returns non-empty
results. Run the full worker pipeline first.

---

## Testing Strategy

| Layer | File | Requires DB? |
|---|---|---|
| Unit (formula) | `tests/test_analytics_sdi.py` | No (in-memory Pandas) |
| Integration (SQL write path) | `tests/test_analytics_sdi_integration.py` | Yes (PostgreSQL) |

Integration tests are skipped unless `RUN_INTEGRATION_TESTS=1` is set. They
must pass before any change to `run_sdi_refresh` is merged.

# From Campus to Career

## Unified Dataset and Scraping Job Specification

## 1. Purpose

This spec defines how to build and maintain the unified job-postings dataset in a way that is consistent with:

- the capstone paper
- the System Intelligence Documentation
- the SDI + Skill Decay + Gap Analysis pipeline

The output of this spec is one canonical dataset format that all downstream analytics can trust.

## 2. Scope Alignment to Paper

- **Paper requirement:** real-time Philippine market intelligence for student-facing gap analysis  
  **Design:** PH live scraping pipeline with regular refresh and PH-only SDI branch.
- **Paper requirement:** temporal monitoring for Skill Decay Warning  
  **Design:** global + historical time-series branch for long-horizon SDI snapshots.
- **Paper requirement:** unified system with auditable computations  
  **Design:** strict schema contract, deterministic IDs, and quality checks.

## 3. Canonical Unified Schema (SDI-Ready)

Every row in `unified_job_postings.csv` represents one posting and must contain only these columns:

1. `posting_id` - deterministic unique ID
2. `title` - raw job title
3. `role_normalized` - canonical role label (for grouping)
4. `skills` - comma-separated canonical skills
5. `seniority` - `entry_level` | `mid` | `senior` | `unknown`
6. `platform` - `linkedin` | `indeed` | `jobstreet` | `kalibrr` | `historical`
7. `country` - `PH` | `US` | `global`
8. `posted_date` - `YYYY-MM`
9. `source_dataset` - source identifier

Everything else (salary, company, full description, URL, location details, etc.) stays in raw storage, not in this SDI table.

## 4. Deterministic `posting_id` Rule

Do not use random UUIDs at combine time, because random IDs break incremental dedup and time-series consistency.

Use deterministic hashing:

```python
import hashlib

def make_posting_id(source_dataset: str, native_id: str | None, title: str, posted_date: str) -> str:
    base = f"{source_dataset}|{native_id or ''}|{title.strip().lower()}|{posted_date}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:20]
```

If a dataset has a native posting ID (for example `job_id`), include it. If not, fallback to title + date fingerprint.

## 5. Historical Dataset Transformation Rules

Transform each source into the canonical schema before concatenation.

### 5.1 LinkedIn Job Postings 2023-2024 (Kaggle)

- Merge postings with `job_skills` grouped by `job_id`
- Map experience level to canonical seniority
- Convert timestamp to `YYYY-MM`
- `platform='linkedin'`, `country='global'`
- `source_dataset='linkedin_2023_2024_kaggle'`

### 5.2 1.3M LinkedIn Jobs and Skills 2024 (Kaggle)

- Group skills by `job_id`
- `posted_date='2024-01'` when exact date unavailable
- `platform='linkedin'`, `country='global'`
- `source_dataset='1m_linkedin_skills_2024_kaggle'`

### 5.3 Data Science Job Postings and Skills 2024 (Kaggle)

- Same normalization strategy as LinkedIn skills datasets
- `posted_date='2024-01'` when exact date unavailable
- `country='global'`
- `source_dataset='data_science_jobs_2024_kaggle'`

### 5.4 Online Job Postings Historical (Kaggle)

- No pre-tagged skills: leave `skills=''` initially
- Parse `Date` into `YYYY-MM`
- `platform='historical'`, `country='global'`
- `source_dataset='online_job_posts_historical_kaggle'`

### 5.5 Philippines Job Postings (Kaggle)

- Apply canonical mapping like other sources
- `country='PH'` (critical for PH branch)
- `platform='jobstreet'` (or source-appropriate value if dataset includes mixed origin)
- `source_dataset='philippines_job_postings_kaggle'`

## 6. Skill Population Policy

- If source has pre-tagged skills: ingest then normalize aliases.
- If source has no skills: run NLP extraction (`spaCy PhraseMatcher`) on description text from raw storage.
- Run alias normalization after extraction to canonical taxonomy.

Final `skills` values must be canonical names joined by commas, with duplicates removed.

## 7. `role_normalized` Population Policy

`role_normalized` must be populated before SDI aggregation.

Recommended process:

1. Use title-based role mapping dictionary for obvious matches.
2. Use SBERT similarity fallback for ambiguous titles.
3. Assign nearest canonical role if confidence >= threshold (for example 0.70).
4. Otherwise assign `Other` and exclude from role-specific SDI until reviewed.

## 8. Live Philippine Scraping Job (Production)

This job is the paper-aligned source of current PH market intelligence.

### 8.1 Sources

- LinkedIn Philippines
- JobStreet Philippines
- Kalibrr

Use official APIs/feeds where available. If scraping is used, follow platform terms and rate limits.

### 8.2 Job Name

`ph_live_ingest_weekly`

### 8.3 Schedule

- Weekly run: every Monday, 02:00 Asia/Manila
- Optional daily delta micro-run for freshness (same contract, smaller batch)

### 8.4 Job Steps

1. Fetch postings from PH-targeted queries.
2. Store raw records in raw layer.
3. Transform raw to canonical schema fields.
4. Extract and normalize skills.
5. Normalize role and seniority.
6. Generate deterministic `posting_id`.
7. Deduplicate against existing unified store.
8. Save batch output to `data/processed/live_scraped_ph.csv`.
9. Append valid records to `unified_job_postings.csv` (or warehouse table equivalent).
10. Trigger PH SDI recomputation.

### 8.5 Required Output Contract (`live_scraped_ph.csv`)

Must use the same 9-column canonical schema:

- `posting_id,title,role_normalized,skills,seniority,platform,country,posted_date,source_dataset`

Hard constraints:

- `country` must be `PH`
- `posted_date` format must be `YYYY-MM`
- `source_dataset` must indicate source and run family, for example:
  - `linkedin_ph_live`
  - `jobstreet_ph_live`
  - `kalibrr_ph_live`

## 9. Data Quality Gates

Reject or quarantine records if any rule fails:

- Missing `title`
- Invalid `posted_date` format
- Invalid enum values for `seniority`, `platform`, or `country`
- Empty `role_normalized` after mapping
- Duplicate `posting_id` in current batch

Batch-level warnings:

- Skill extraction empty rate above threshold
- Role mapping confidence drift
- Sudden posting-count drop from previous week

## 10. Unified Build Workflow

1. Transform each historical dataset into canonical schema.
2. Concatenate all transformed datasets.
3. Populate deterministic `posting_id`.
4. Clean invalid rows.
5. Sort by `posted_date`.
6. Save `data/processed/unified_job_postings.csv`.
7. Run QA summary:
   - row count
   - date range
   - country distribution
   - source distribution

## 11. Two-Branch Analytics Pipeline (Required)

After unified data exists, split into two branches:

### Branch A: Global Historical + Current (Decay Engine)

- Input: all rows
- Filter: `seniority in ['entry_level']`
- Output: SDI time-series snapshots per skill-role-period
- Consumer: Skill Decay Warning engine (linear slope detection)

### Branch B: PH Only (Student Dashboard)

- Input: `country == 'PH'` + weekly live PH batches
- Filter: `seniority in ['entry_level']`
- Output: PH SDI snapshots per skill-role-period
- Consumer: student-facing gap rankings and demand percentages

This split preserves the paper's logic:

- deep global history for decay trends
- PH relevance for recommendations shown to students

## 12. SDI Function Contract

Both branches must call the same SDI computation function shape:

```python
def compute_sdi_snapshots(
    df: pd.DataFrame,
    seniority_filter: list[str],
    group_by: list[str],
    decay_factor: float = 0.9,
) -> pd.DataFrame:
    """
    Returns:
        skill | role | time_period | sdi_value | posting_count
    """
```

`group_by` should be `['role_normalized', 'posted_date']` for standard operation.

## 13. Storage Layout (Recommended)

```text
data/
  raw/
    <source>/<run_date>/*.json|csv
  processed/
    unified_job_postings.csv
    live_scraped_ph.csv
    sdi_global_snapshots.csv
    sdi_ph_snapshots.csv
```

## 14. Operational Jobs (Minimum Set)

1. `historical_bootstrap` - one-time historical ingest and transformation
2. `ph_live_ingest_weekly` - recurring PH live collection + normalization
3. `unified_compaction` - dedup and canonical merge
4. `sdi_global_refresh` - global branch snapshots
5. `sdi_ph_refresh` - PH branch snapshots
6. `decay_refresh` - slope computation and alert candidates
7. `qa_report` - validation and drift summary

## 15. Acceptance Criteria

This design is accepted when:

- Unified dataset respects exact 9-column schema
- Deterministic IDs prevent duplicate growth across reruns
- PH live batches append cleanly and trigger PH SDI refresh
- Both SDI branches run from same canonical contract
- Student dashboard uses PH SDI values
- Decay engine uses all-country historical SDI time-series

## 16. Risks and Controls

- Source structure changes: implement parser versioning per source.
- Scrape interruptions: retry with backoff, alert on run failure.
- Skills sparsity in historical data: backfill with NLP extraction pipeline.
- Role mapping ambiguity: confidence thresholds + admin review queue.

## 17. Build-This-Week Checklist

1. Create folders:

```powershell
New-Item -ItemType Directory -Path "data\raw" -Force
New-Item -ItemType Directory -Path "data\processed" -Force
```

2. Implement dataset transformers with canonical output.
3. Implement deterministic ID function and dedup logic.
4. Build `unified_job_postings.csv`.
5. Add weekly PH live ingest job emitting canonical CSV.
6. Run global and PH SDI snapshot jobs.
7. Generate first QA report and baseline metrics.

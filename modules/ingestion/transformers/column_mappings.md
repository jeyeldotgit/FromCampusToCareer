# Kaggle Source Column Mappings

**Purpose:** Documents the actual CSV column names from each raw Kaggle source and
their mapping to the canonical 9-column schema. This is the required gate document.
Engineers must verify each `VERIFY` annotation before the transformer for that source
is considered production-ready.

Canonical schema:
`posting_id | title | role_normalized | skills | seniority | platform | country | posted_date | source_dataset`

---

## Source 1: LinkedIn Job Postings 2023-2024

**Kaggle dataset:** "LinkedIn Job Postings - 2023-2024" by arshkon  
**`source_dataset` value:** `linkedin_2023_2024_kaggle`  
**Expected files in `data/raw/kaggle/linkedin_2023_2024/`:**
- `job_postings.csv` — main postings file
- `job_skills.csv` — posting ↔ skill_abr associations
- `skills.csv` — skill_abr ↔ skill_name lookup (optional; abr used as fallback)

### Column mapping

| Canonical field  | Source column               | Notes                                          |
|------------------|-----------------------------|------------------------------------------------|
| `posting_id`     | *(generated)*               | `make_posting_id(source, job_id, title, date)` |
| `title`          | `title`                     | VERIFY                                         |
| `role_normalized`| *(from role mapping)*       | Applied in bootstrap after transform           |
| `skills`         | `skill_name` (joined)       | From skills.csv via job_skills.csv             |
| `seniority`      | `formatted_experience_level`| VERIFY; mapped via SENIORITY_MAP               |
| `platform`       | `"linkedin"` (constant)     |                                                |
| `country`        | `"global"` (constant)       |                                                |
| `posted_date`    | `original_listed_time`      | VERIFY; Unix ms timestamp → YYYY-MM            |
| `source_dataset` | `"linkedin_2023_2024_kaggle"` (constant) |                               |

### Known experience level values
`Entry level`, `Mid-Senior level`, `Associate`, `Director`, `Executive`,
`Internship`, `Not Applicable` — all covered by SENIORITY_MAP.

---

## Source 2: 1.3M LinkedIn Jobs and Skills 2024

**Kaggle dataset:** "1.3M LinkedIn Jobs and Skills" by asaniczka  
**`source_dataset` value:** `1m_linkedin_skills_2024_kaggle`  
**Expected files in `data/raw/kaggle/linkedin_1m_2024/`:**
- `linkedin_job_postings.csv` — main postings file
- `job_skills.csv` — posting ↔ skills associations

### Column mapping

| Canonical field  | Source column          | Notes                                             |
|------------------|------------------------|---------------------------------------------------|
| `posting_id`     | *(generated)*          | `make_posting_id(source, job_link, title, date)`  |
| `title`          | `job_title`            | VERIFY                                            |
| `role_normalized`| *(from role mapping)*  | Applied in bootstrap                              |
| `skills`         | `job_skills`           | Comma-separated in job_skills.csv; VERIFY         |
| `seniority`      | `job_level`            | VERIFY; mapped via SENIORITY_MAP                  |
| `platform`       | `"linkedin"` (constant)|                                                   |
| `country`        | `"global"` (constant)  |                                                   |
| `posted_date`    | `first_seen`           | VERIFY; date string → YYYY-MM                     |
| `source_dataset` | `"1m_linkedin_skills_2024_kaggle"` (constant) |                          |

---

## Source 3: Data Science Job Postings and Skills 2024

**Kaggle dataset:** "Data Science Job Postings and Skills" by asaniczka  
**`source_dataset` value:** `data_science_jobs_2024_kaggle`  
**Expected files in `data/raw/kaggle/data_science_2024/`:**
- `linkedin_job_postings.csv` or `job_postings.csv` — VERIFY filename
- `job_skills.csv`

### Column mapping

| Canonical field  | Source column          | Notes                                             |
|------------------|------------------------|---------------------------------------------------|
| `posting_id`     | *(generated)*          | `make_posting_id(source, job_link, title, date)`  |
| `title`          | `job_title`            | VERIFY                                            |
| `role_normalized`| *(from role mapping)*  | Applied in bootstrap                              |
| `skills`         | `job_skills`           | VERIFY; same structure as source 2                |
| `seniority`      | `job_level`            | VERIFY; mapped via SENIORITY_MAP                  |
| `platform`       | `"linkedin"` (constant)|                                                   |
| `country`        | `"global"` (constant)  | Dataset is global; no country filter              |
| `posted_date`    | `first_seen`           | VERIFY; date string → YYYY-MM; fallback `2024-01` |
| `source_dataset` | `"data_science_jobs_2024_kaggle"` (constant) |                            |

---

## Source 4: Online Job Postings Historical

**Kaggle dataset:** "Online Job Postings" (historical, multi-year)  
**`source_dataset` value:** `online_job_posts_historical_kaggle`  
**Verified file:** `job_posting.csv` (9,919 rows, encoding: latin-1)  
**Files in `data/raw/kaggle/online_historical/`:**
- `job_posting.csv` ✓ VERIFIED

### Column mapping — VERIFIED

| Canonical field  | Source column           | Notes                                              |
|------------------|-------------------------|----------------------------------------------------|
| `posting_id`     | *(generated)*           | `make_posting_id(source, None, title, date)`       |
| `title`          | `Job Opening Title`     | ✓ VERIFIED                                         |
| `role_normalized`| *(from role mapping)*   | Applied in bootstrap via `map_role(title)`         |
| `skills`         | `Keywords`              | ✓ VERIFIED; comma-separated tech keywords/skills   |
| `seniority`      | `Seniority`             | ✓ VERIFIED; values: non_manager→entry_level, manager/head/director/c_level→senior |
| `platform`       | `"historical"` (constant) |                                                  |
| `country`        | `"global"` (constant)   |                                                    |
| `posted_date`    | `First Seen At`         | ✓ VERIFIED; ISO 8601 e.g. `2024-05-29T19:59:45Z`  |
| `source_dataset` | `"online_job_posts_historical_kaggle"` (constant) |                        |

### Additional available columns (not used in canonical schema)
- `O*NET Occupation Name` — standardized occupation name; useful for future role mapping
- `O*NET Family` — occupation family (e.g. "Architecture and Engineering")
- `Job Opening URL` — unique URL; could be used as native_id in future
- `Category` — comma-separated job categories (e.g. `engineering, software_development`)
- `Description` — full job description; reserved for Stage 2 NLP skill extraction
- `Location` / `Location Data` — geographic data

### Seniority value distribution (verified)
- `non_manager`: 7,981 rows → mapped to `entry_level`
- `manager`: 1,809 rows → mapped to `senior`
- `head`: 75 rows → mapped to `senior`
- `director`: 33 rows → mapped to `senior`
- `c_level`: 13 rows → mapped to `senior`
- `vice_president`: 4 rows → mapped to `senior`

---

## Source 5: Philippines Job Postings

**Kaggle dataset:** "Philippines Job Postings" (JobStreet-sourced)  
**`source_dataset` value:** `philippines_job_postings_kaggle`  
**Expected files in `data/raw/kaggle/philippines/`:**
- `*.csv` — VERIFY filename; may be `jobs.csv`, `philippines_jobs.csv`, etc.

### Column mapping

| Canonical field  | Source column               | Notes                                          |
|------------------|-----------------------------|------------------------------------------------|
| `posting_id`     | *(generated)*               | `make_posting_id(source, id_col, title, date)` |
| `title`          | `job_title` or `title`      | VERIFY                                         |
| `role_normalized`| *(from role mapping)*       | Applied in bootstrap                           |
| `skills`         | `""` (empty or extracted)   | VERIFY if skills column exists                 |
| `seniority`      | `experience` or similar     | VERIFY; mapped via SENIORITY_MAP               |
| `platform`       | `"jobstreet"` (constant)    |                                                |
| `country`        | `"PH"` (constant)           | Critical: PH branch depends on this            |
| `posted_date`    | `date_posted` or `created_at` | VERIFY; parse to YYYY-MM                     |
| `source_dataset` | `"philippines_job_postings_kaggle"` (constant) |                         |

---

## Verification Checklist

Before each transformer is considered production-ready, run:

```powershell
# From backend/
python -c "
import pandas as pd
df = pd.read_csv('data/raw/kaggle/<source>/<file>.csv', nrows=5)
print(df.columns.tolist())
print(df.head(2))
"
```

Check the output against the `VERIFY` annotations above and update this document
with the confirmed column names.

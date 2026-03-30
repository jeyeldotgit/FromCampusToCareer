# From Campus to Career - System Intelligence Documentation

## Model and Algorithm Reference (Developer Version)

## 1. Overview

`From Campus to Career` uses a hybrid intelligence architecture. No single model powers the whole system. Each component uses the technique most appropriate for its task:

- Transformer NLP for semantic career intent matching
- Rule-based NLP for skill extraction and normalization
- Statistical computation for market demand scoring
- Supervised trend modeling for skill decay detection
- Rule-based logic for gap prioritization
- Unsupervised learning for career affinity signals

This document is implementation-facing and aligned with the capstone concept paper.

## 2. Component Map


| Component                 | Category        | Technique / Model                              | Purpose                                              |
| ------------------------- | --------------- | ---------------------------------------------- | ---------------------------------------------------- |
| Career Intent Parsing     | Transformer NLP | Sentence-BERT (`all-MiniLM-L6-v2`)             | Maps free-text student intent to active job titles   |
| Skill Extraction          | Rule-based NLP  | spaCy `PhraseMatcher`                          | Extracts skill mentions from job postings            |
| Skill Normalization       | Rule-based      | Alias lookup table                             | Resolves skill variants to canonical taxonomy        |
| Skill Demand Index (SDI)  | Statistical     | Frequency + exponential decay weighting        | Ranks skill demand by role and time                  |
| Skill Decay Warning       | Supervised ML   | Linear Regression slope analysis               | Detects declining demand in student-owned skills     |
| Gap Analysis              | Rule-based      | Set difference + depth comparison + thresholds | Identifies and ranks missing or under-leveled skills |
| Career Affinity Indicator | Unsupervised ML | K-Means clustering                             | Maps academic strengths to likely career paths       |


## 3. NLP Components

### 3.1 Career Intent Parsing

**Category:** Transformer-based NLP  
**Model:** Sentence-BERT (`all-MiniLM-L6-v2`)  
**Library:** `sentence-transformers`

**Purpose**

- Convert student free-text intent into semantic embeddings
- Match intent to active Philippine job titles using cosine similarity
- Support English and Filipino-English (Taglish) intent entries

**Pipeline**

1. Student enters free-text intent.
2. Model encodes text to a 384-d vector.
3. Cosine similarity is computed against pre-encoded role-title vectors.
4. Top-3 role matches with confidence are returned.
5. Student confirms final target role.

**Example**
Input: `gusto ko maging data analyst sa tech company`  
Output:

1. `Data Analyst` (0.94)
2. `Business Intelligence Analyst` (0.81)
3. `Data Reporting Specialist` (0.73)

**Validation Target**

- Development target: Top-3 accuracy >= 0.85
- Minimum acceptance threshold: Top-3 accuracy >= 0.80

---

### 3.2 Skill Extraction from Job Postings

**Category:** Rule-based NLP  
**Model:** spaCy `PhraseMatcher`  
**Library:** `spaCy`

**Purpose**

- Extract known skills from raw posting text using canonical taxonomy terms
- Scale efficiently for large posting volumes

**Why Rule-Based Here**

- Task is taxonomy-driven (known-skill detection), not open-ended entity discovery
- Faster and cheaper than transformer inference at large scale
- Deterministic and easy to audit

**Pipeline**

1. Raw posting text enters NLP preprocessor.
2. spaCy tokenizes text.
3. `PhraseMatcher` finds single- and multi-word skill patterns (case-insensitive).
4. Matched skills are sent to normalization.
5. Canonical skill IDs are stored per posting.

**Example**
Input:  
`We are looking for a candidate proficient in Python and SQL. Experience with Tableau or Power BI required. Knowledge of Machine Learning is a plus.`

Output:  
`["Python", "SQL", "Tableau", "Power BI", "Machine Learning"]`

**Validation Target**

- F1 score >= 0.85 on manually labeled Philippine job-posting samples

---

### 3.3 Skill Normalization

**Category:** Rule-based  
**Technique:** Alias lookup table  
**Library:** Python dictionary map

**Purpose**

- Collapse variants to canonical skill names for accurate counting and trends

**Reference Logic**

```python
ALIAS_MAP = {
    "reactjs": "React",
    "react.js": "React",
    "nodejs": "Node.js",
    "node": "Node.js",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "ml": "Machine Learning",
}

def normalize(raw: str) -> str | None:
    return ALIAS_MAP.get(raw.strip().lower())
```

**Behavior**

- Canonical hit: return canonical skill
- Unknown term: return `None` and flag for admin taxonomy review

## 4. Statistical Component

### 4.1 Skill Demand Index (SDI) Computation

**Category:** Statistical computation  
**Technique:** Frequency analysis + exponential recency weighting  
**Libraries:** `pandas`, `numpy`

**Purpose**

- Compute demand strength for each skill per role using entry-level Philippine postings
- Prioritize recent market behavior while retaining historical context

**Base Formula (per time period)**

```text
SDI(skill, role, t) =
count(entry-level postings for role at t mentioning skill)
/
count(total entry-level postings for role at t)
```

**Recency-Weighted SDI**

```text
SDI_weighted(skill, role) =
sum( SDI(skill, role, t) * decay_factor^(N - t_index) )
/
sum( decay_factor^(N - t_index) )
```

Where:

- `N` = number of time periods
- `t_index` = chronological index (`1` oldest, `N` newest)
- `decay_factor` default = `0.90`

**Pipeline**

1. Ingest unified postings dataset.
2. Filter to entry-level postings.
3. Group by role and period (`YYYY-MM`).
4. Compute total postings and per-skill counts.
5. Store SDI snapshots per skill-role-period.
6. Compute weighted SDI for current decision outputs.

**Example**

- Role: `Data Analyst`
- Period: `2025-03`
- Total entry-level postings: `847`
- SQL mentions: `771`
- Result: `SDI(SQL, Data Analyst, 2025-03) = 0.91`

**Validation Target**

- Pearson correlation >= 0.95 versus manual frequency counts on audit samples

## 5. Machine Learning Components

### 5.1 Skill Decay Warning Engine

**Category:** Supervised ML / trend modeling  
**Model:** `LinearRegression`  
**Library:** `scikit-learn`

**Purpose**

- Detect whether a student-owned skill is losing market relevance over time

**Core Logic**

1. Pull SDI time series for `(skill, role)`.
2. Fit linear regression: `time_index -> SDI`.
3. Evaluate slope (`coef_`) and fit quality (`R^2`).
4. If slope is below decay threshold, mark as decaying.
5. Recommend replacement skill using growth slope + co-occurrence rules.

**Slope Bands**

- `slope > +0.015`: Growing
- `-0.015 <= slope <= +0.015`: Stable
- `slope < -0.015`: Decaying (alert)

**Example**
Input skill: `Microsoft Access`  
SDI history: `[0.41, 0.33, 0.28, 0.19, 0.14]`  
Output:

- slope: `-0.068`
- `R^2`: `0.97`
- status: `Decaying`
- replacement: `Power BI` (example growth slope `+0.14`)

**Validation Target**

- Trend detection accuracy >= 0.80 on labeled growth/stable/decline samples

---

### 5.2 Gap Analysis

**Category:** Rule-based computation  
**Technique:** Set difference + depth-level comparison + SDI thresholds  
**Libraries:** Python set logic, `pandas`

**Purpose**

- Identify missing skills and under-leveled skills for target role readiness

**Depth Crediting Rules (from student grades)**

- `1.00-1.50`: Advanced
- `1.51-2.00`: Proficient
- `2.01-2.75`: Intermediate
- `2.76-3.00`: Foundational
- `>3.00` or failed: Not credited

**Priority Bands (by weighted SDI)**

- `>= 0.70`: Critical
- `>= 0.40 and < 0.70`: Important
- `< 0.40`: Emerging

**Gap Logic**

- `Missing gap`: skill absent in student inventory
- `Depth gap`: skill exists but student depth < market-required depth
- `No gap`: student depth >= required depth

**Corrected Example**
Target role: `Data Analyst`  
Student skills: `Python (Intermediate), SQL (Advanced), Statistics (Foundational), Excel (Intermediate)`

Output:

1. `Tableau` - Critical (SDI 0.78) - Missing
2. `Python` - Critical (SDI 0.74) - Depth gap (market requires Advanced)
3. `Power BI` - Important (SDI 0.63) - Missing
4. `Excel` - Important (SDI 0.58) - Depth gap (market requires Advanced)
5. `dbt` - Emerging (SDI 0.31) - Missing

`SQL` is not shown as a gap because student depth already meets requirement.

---

### 5.3 Career Affinity Indicator

**Category:** Unsupervised ML  
**Model:** `KMeans`  
**Library:** `scikit-learn`

**Purpose**

- Surface career paths aligned with student academic strengths

**Pipeline**

1. Encode subjects via skill-tag feature vectors.
2. Cluster subjects by domain (`k=5`, configurable).
3. Compute student average grade per cluster.
4. Identify strongest clusters.
5. Map strongest cluster(s) to role families.

**Example Output**

- Analytical cluster average: `1.50` (strongest)
- Programming cluster average: `2.25`
- Systems cluster average: `2.25`

Affinity signal:

- `Data Analyst` - Strong
- `Business Analyst` - Strong
- `Data Engineer` - Moderate

**Validation Target**

- Cluster quality indicator (internal): silhouette score >= 0.60
- Practical validation: student and adviser face-validation during UAT

## 6. Evaluation Summary


| Component                | Technique / Model           | Metric                      | Target                               |
| ------------------------ | --------------------------- | --------------------------- | ------------------------------------ |
| Career Intent Parsing    | SBERT                       | Top-3 accuracy              | >= 0.85 (>= 0.80 minimum acceptance) |
| Skill Extraction         | spaCy PhraseMatcher         | F1 score                    | >= 0.85                              |
| SDI Computation          | Frequency + decay weighting | Pearson correlation         | >= 0.95                              |
| Skill Decay Warning      | Linear Regression trend     | Detection accuracy          | >= 0.80                              |
| Gap Analysis             | Rule-based comparison       | Manual logic audit          | 100% rule-consistent outputs         |
| Career Affinity          | K-Means                     | Silhouette score (internal) | >= 0.60                              |
| Overall System Usability | SUS                         | SUS score                   | >= 80                                |


## 7. What Is ML vs Non-ML

**ML / AI components**

- Career Intent Parsing (`SBERT`)
- Skill Decay Warning (`LinearRegression`)
- Career Affinity Indicator (`KMeans`)

**NLP but not transformer**

- Skill Extraction (`spaCy PhraseMatcher`)
- Skill Normalization (alias mapping)

**Statistical computation**

- Skill Demand Index (frequency + recency weighting)

**Rule-based logic**

- Gap identification and depth comparison
- SDI-based priority classification

## 8. Implementation Notes for Developers

- Keep every component modular and independently testable.
- Version all model artifacts and taxonomy dictionaries.
- Log confidence scores, slopes, and decision thresholds for auditability.
- Store SDI snapshots as time series to support decay analysis and dashboards.
- Expose component outputs via stable backend contracts for mobile rendering.

## 9. Alignment Statement

This intelligence design aligns with the capstone concept paper's core claims:

- real-time Philippine market grounding
- grade-weighted skill crediting
- recency-weighted SDI
- reverse-direction skill decay monitoring
- personalized, demand-prioritized career guidance


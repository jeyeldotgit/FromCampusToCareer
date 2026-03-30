# From Campus to Career

## Modular Monolith Architecture Draft

## 1. Architecture Decision

The backend architecture is a **modular monolith**:

- one deployable backend service
- one primary relational database
- one codebase with strict internal module boundaries

This is the recommended architecture for the capstone because it keeps development fast, reduces operational complexity, and still allows clean scaling later.

## 2. Why Modular Monolith for This Project

- Faster delivery for student timeline and limited team size
- Easier debugging than distributed microservices
- Lower hosting and DevOps overhead
- Clear separation of concerns through modules
- Future-ready path to split high-load modules into services when needed

## 3. High-Level System Context

Clients:

- Mobile app (Android/iOS)
- Admin web panel

Backend:

- Modular monolith API
- Background worker process (same codebase, separate runtime)

Data:

- PostgreSQL (or equivalent relational DB)
- Raw storage for source payloads/files

External:

- Philippine job platforms and datasets
- Push notification provider

## 4. Core Module Boundaries

Each module owns its domain logic and tables. Cross-module access happens through application services, not direct table coupling.

### 4.1 `auth`

- User registration/login
- Role-based access (`student`, `admin`)
- Token/session management

### 4.2 `student_profile`

- Student academic profile
- Courses with grades
- Certifications and portfolio projects
- Declared target roles

### 4.3 `taxonomy_admin`

- Canonical skills
- Alias mapping
- Course-to-skill mapping
- Grade-to-depth mapping
- Role catalog management

### 4.4 `ingestion`

- Historical dataset import
- Live PH scraping connectors
- Raw payload persistence
- Source run metadata and job status

### 4.5 `normalization`

- Canonical unified schema mapping
- `posting_id` deterministic generation
- Seniority, platform, country standardization
- Role normalization and confidence scoring
- Skill extraction and normalization pipeline

### 4.6 `analytics_sdi`

- SDI snapshot computation
- PH-only and global branches
- Time-series persistence by role/skill/period

### 4.7 `analytics_decay`

- Linear regression trend detection per owned skill
- Decay/growth/stable classification
- Replacement skill suggestion logic

### 4.8 `gap_and_roadmap`

- Gap identification (missing + depth gaps)
- SDI-priority ranking
- Career roadmap generation
- Readiness score computation and history tracking

### 4.9 `career_affinity`

- Subject cluster analysis
- K-Means affinity signal generation
- Career-path alignment outputs

### 4.10 `notifications`

- Push/in-app alert orchestration
- Decay alerts and roadmap reminders
- Delivery status tracking

### 4.11 `reporting_observability`

- Data quality checks
- Pipeline run logs
- Admin health dashboard metrics

## 5. Canonical Data Contract (Unified Job Postings)

All analytics modules consume the same canonical schema:

- `posting_id`
- `title`
- `role_normalized`
- `skills`
- `seniority`
- `platform`
- `country`
- `posted_date` (`YYYY-MM`)
- `source_dataset`

This contract prevents logic drift between ingestion and analytics.

## 6. Runtime Topology

Use two runtime processes from one codebase:

1. `api-service`

- serves student and admin endpoints
- handles read/write for app actions

2. `worker-service`

- runs scheduled jobs and heavy analytics
- performs ingestion, normalization, SDI refresh, and decay refresh

Both use the same modules and database schema.

## 7. Job Orchestration Pattern

Recommended task chain for PH live pipeline:

1. Fetch PH source data
2. Save raw payload
3. Normalize into canonical schema
4. Extract and normalize skills
5. Upsert into PH postings table
6. Recompute PH SDI snapshots
7. Run quality checks
8. Publish run report and alerts

Global branch runs separately for decay time-series depth.

## 8. API Surface (Initial)

Student-facing endpoints:

- `POST /student/profile`
- `POST /student/target-role`
- `GET /student/gap-analysis`
- `GET /student/readiness-history`
- `GET /student/decay-alerts`
- `GET /student/roadmap`
- `GET /student/career-affinity`

Admin endpoints:

- `GET/POST /admin/skills`
- `GET/POST /admin/aliases`
- `GET/POST /admin/course-skill-mappings`
- `GET /admin/pipeline-runs`
- `POST /admin/jobs/run`

## 9. Data Storage Strategy

Transactional tables:

- users, student_profiles, course_records, certifications, projects
- skills, skill_aliases, role_catalog, course_skill_map, grade_depth_rules
- job_postings_unified, job_postings_ph, sdi_snapshots_ph, sdi_snapshots_global
- decay_alerts, gap_results, roadmap_items, readiness_history
- pipeline_runs, pipeline_run_logs, data_quality_reports

Raw storage:

- full source job payloads
- original descriptions and metadata for reprocessing

## 10. Guardrails and Engineering Rules

- No module may bypass canonical normalization.
- Heavy analytics must run in worker jobs, not synchronous API requests.
- Every scheduled job must be idempotent and safe to rerun.
- Use deterministic `posting_id` generation for dedup consistency.
- Keep feature flags for thresholds (`decay_threshold`, SDI priority bands).

## 11. Scaling Path

When needed, split these first:

1. `ingestion + normalization` as independent data service
2. `analytics_sdi + analytics_decay` as async analytics service

Everything else can remain in core app longer.

## 12. Architecture Summary

The modular monolith gives the team speed now and clean evolution later:

- simple deployment
- strict module boundaries
- shared canonical data contract
- clear separation between online API and background analytics jobs

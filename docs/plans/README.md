# Backend plans — source of truth

**Canonical MVP / stage plan**

- [`ARCH-PLAN-MVP-2026-03-28-v2.md`](ARCH-PLAN-MVP-2026-03-28-v2.md) — scope, modules, stages, risks. Edit this file when the plan changes; do not duplicate the full plan under `.cursor/plans/`.

**Pipeline runbooks (implementation detail)**

1. [`PIPELINE-ingestion.md`](PIPELINE-ingestion.md) — CSV → `job_postings_unified`
2. [`PIPELINE-normalization.md`](PIPELINE-normalization.md) — `job_postings_unified` → `posting_skills`
3. [`PIPELINE-analytics_sdi.md`](PIPELINE-analytics_sdi.md) — SDI SQL/Python parity, `ph` + `global`, `get_weighted_sdi` fallback

**Related architecture docs**

- [`../predevelopment/architecture.md`](../predevelopment/architecture.md) — modular monolith boundaries and topology

**Review signoffs (active)**

- [`REVIEW-SIGNOFF-backend-docs-2026-04-07.md`](REVIEW-SIGNOFF-backend-docs-2026-04-07.md) — documentation single source of truth + SDI scope alignment

**Historical review artifacts**

- [`../archive/`](../archive/) — past `REVIEW-SIGNOFF-*` notes (read-only audit trail)

**Stage checklist (demo)**

- [`../../../stages/MVP-Documentation.md`](../../../stages/MVP-Documentation.md) — short checklist and links only

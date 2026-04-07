# From Campus to Career

## Agentic Coding Guide — Role Prompting Reference

---

## Overview

This project uses three distinct AI roles to separate architectural thinking, critical review, and implementation. Each role is a Cursor rule that must be explicitly activated per session. Never run multiple roles in the same session.


| Role               | Rule File               | Mode         | Produces                            |
| ------------------ | ----------------------- | ------------ | ----------------------------------- |
| Software Architect | `backend-architect.mdc` | Ask or Agent | `ARCH-PLAN-<module>-<date>.md`      |
| Technical Reviewer | `backend-reviewer.mdc`  | Ask          | `REVIEW-SIGNOFF-<module>-<date>.md` |
| Senior Engineer    | `backend-engineer.mdc`  | Agent        | Working code + passing tests        |


**Artifact storage:** Save all plans and sign-offs in `backend/docs/plans/`.

---

## The Three-Phase Loop (Per Module)

```
[Architect] → ARCH-PLAN → [Reviewer] → REVIEW-SIGNOFF → [Engineer] → Code → [Reviewer] → Post-impl check
```

Never skip a phase. The engineer may not start without a REVIEW-SIGNOFF marked **approved** or **approved with conditions** (with conditions addressed).

---

## Phase 1 — Architect Session

### When to use

- Starting a new module
- Changing module boundaries or data contracts
- Designing a new database schema or job workflow

### How to activate

In a new chat, `@mention` the rule file, then open with the session header:

```
@backend-architect.mdc

ACTIVE ROLE: backend-architect
MODULE: <module_name>
CONTEXT: @backend/docs/predevelopment/architecture.md

<your design request here>
```

### Full prompt template

```
@backend-architect.mdc

ACTIVE ROLE: backend-architect
MODULE: ingestion
CONTEXT: @backend/docs/predevelopment/architecture.md @backend/docs/predevelopment/initial-unified-dataset-and-scraping.md

Design the ingestion module. Include:
- module purpose and boundaries
- folder structure under backend/
- DB schema changes (if any)
- which jobs are sync vs async
- interfaces exposed to normalization and other consumers
- risks and open questions

Produce ARCH-PLAN-ingestion-2026-03-28.
Do not write any implementation code.
```

### What to do with the output

1. Copy the produced plan.
2. Save it as `backend/docs/plans/ARCH-PLAN-<module>-<date>.md`.
3. Open a new chat for Phase 2.

---

## Phase 2 — Reviewer Session

### When to use

- After the architect produces an ARCH-PLAN
- After the engineer writes code (post-implementation check)

### How to activate

```
@backend-reviewer.mdc

ACTIVE ROLE: backend-reviewer
INPUT: ARCH-PLAN-<module>-<date>

<paste or @reference the plan>
```

### Full prompt template (pre-implementation review)

```
@backend-reviewer.mdc

ACTIVE ROLE: backend-reviewer
INPUT: @backend/docs/plans/ARCH-PLAN-ingestion-2026-03-28.md

Review this architecture plan for the ingestion module.
Check:
- module boundary coherence
- unnecessary complexity for MVP
- ETL data flow validity
- background task separation
- folder structure scalability
- hidden technical debt

Produce `REVIEW-SIGNOFF-<module>-<YYYY-MM-DD>.md`.
State: approved / approved with conditions / rejected.
List any required changes before the engineer starts.
```

### Full prompt template (post-implementation review)

```
@backend-reviewer.mdc

ACTIVE ROLE: backend-reviewer
MODULE: ingestion
ARCH-PLAN: @backend/docs/plans/ARCH-PLAN-ingestion-2026-03-28.md
SIGN-OFF: @backend/docs/plans/REVIEW-SIGNOFF-<module>-<date>.md

Review the implemented ingestion module code.
Check for drift from the approved plan, missing test coverage, and any tech debt introduced.
Flag anything that must be fixed before moving to the next module.
```

### What to do with the output

- **Approved:** Proceed to Phase 3.
- **Approved with conditions:** Address each condition, then proceed.
- **Rejected:** Return to the architect with the reviewer's notes. Produce a revised ARCH-PLAN.
- Save the sign-off as `backend/docs/plans/REVIEW-SIGNOFF-<module>-<date>.md`.

---

## Phase 3 — Engineer Session

### When to use

- You have an approved REVIEW-SIGNOFF
- You are ready to write code for exactly one module

### How to activate

Switch to **Agent mode** first. Then:

```
@backend-engineer.mdc

ACTIVE ROLE: backend-engineer
MODULE: <module_name>
APPROVED PLAN: @backend/docs/plans/ARCH-PLAN-<module>-<date>.md
SIGN-OFF: @backend/docs/plans/REVIEW-SIGNOFF-<module>-<date>.md (approved)
ACCEPTANCE CRITERIA:
  - <criterion 1>
  - <criterion 2>
  - <criterion 3>
EXIT CONDITION: all acceptance criteria pass; no other module is touched.
```

### Full prompt template

```
@backend-engineer.mdc

ACTIVE ROLE: backend-engineer
MODULE: ingestion
APPROVED PLAN: @backend/docs/plans/ARCH-PLAN-ingestion-2026-03-28.md
SIGN-OFF: @backend/docs/plans/REVIEW-SIGNOFF-<module>-<date>.md (approved)
ACCEPTANCE CRITERIA:
  - historical_bootstrap job produces valid 9-column canonical CSV
  - deterministic posting_id is idempotent across reruns
  - invalid rows quarantined with reason code
  - unit tests pass for transformer and posting_id function
EXIT CONDITION: all criteria pass; ingestion module only; do not touch normalization.

Implement the ingestion module only. Follow the approved folder structure strictly.
Do not redesign any boundaries. Stop when exit criteria are confirmed.
```

### Rules to enforce in every engineer session

- One module per session — state it explicitly and hold the boundary.
- Acceptance criteria must be confirmed before the session ends.
- If the AI begins touching another module, stop it and redirect.

---

## Artifact Naming Convention


| Artifact          | Filename pattern                          | Save location         |
| ----------------- | ----------------------------------------- | --------------------- |
| Architecture plan | `ARCH-PLAN-<module>-<YYYY-MM-DD>.md`      | `backend/docs/plans/` |
| Review sign-off   | `REVIEW-SIGNOFF-<module>-<YYYY-MM-DD>.md` | `backend/docs/plans/` (active); superseded → `backend/docs/archive/` |


**Module name values** (from `architecture.md`):

`auth` · `student_profile` · `taxonomy_admin` · `ingestion` · `normalization` · `analytics_sdi` · `analytics_decay` · `gap_and_roadmap` · `career_affinity` · `notifications` · `reporting_observability`

---

## Common Mistakes to Avoid


| Mistake                                    | What happens                                              | Fix                                                              |
| ------------------------------------------ | --------------------------------------------------------- | ---------------------------------------------------------------- |
| Skipping the reviewer                      | Engineer builds the wrong thing                           | Always produce and save a sign-off before Agent mode             |
| Running two roles in one session           | AI averages the roles, loses sharpness                    | One role per session; `@mention` only the rule you need          |
| No acceptance criteria in engineer session | AI keeps going or drifts to other modules                 | Always include explicit criteria and an exit condition           |
| Not saving artifacts as files              | No paper trail; future sessions lose context              | Save every ARCH-PLAN and REVIEW-SIGNOFF to `backend/docs/plans/` |
| Asking the engineer to design              | Violates the boundary; introduces unreviewed architecture | Return to architect; produce a new plan                          |


---

## Quick Reference Card

### Start a new module

1. New chat → `@backend-architect.mdc` → produce ARCH-PLAN → save to `docs/plans/`
2. New chat → `@backend-reviewer.mdc` → review plan → produce REVIEW-SIGNOFF → save to `docs/plans/`
3. Switch to Agent mode → new chat → `@backend-engineer.mdc` → implement with bounded criteria
4. New chat → `@backend-reviewer.mdc` → post-implementation check

### Resume an in-progress module

```
@backend-engineer.mdc

ACTIVE ROLE: backend-engineer
MODULE: <module>
RESUMING SESSION
APPROVED PLAN: @backend/docs/plans/ARCH-PLAN-<module>-<date>.md
REMAINING CRITERIA:
  - <what is still unfinished>
```

### Escalate a reviewer rejection back to architect

```
@backend-architect.mdc

ACTIVE ROLE: backend-architect
MODULE: <module>
REVIEWER FEEDBACK: @backend/docs/plans/REVIEW-SIGNOFF-<module>-<date>.md

Revise the architecture plan to address the reviewer's rejection reasons.
Produce ARCH-PLAN-<module>-<date>-v2.
```


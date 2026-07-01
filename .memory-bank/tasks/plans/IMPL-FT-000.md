---
description: Implementation plan for FT-000 Foundation Dev Path.
status: active
type: implementation_plan
feature_id: FT-000
last_updated: 2026-07-01
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/features/FT-000-foundation.md
  - .memory-bank/requirements.md
  - .memory-bank/workflows/tier-policy.md
---
# IMPL-FT-000 Foundation Dev Path

## Objective

Create the minimum executable foundation that product feature tasks can rely on:
current task-record protocol, backend scaffold anchors, Linux Mint local
bootstrap, local PostgreSQL init, migration/readiness path, DB session baseline,
local runtime roots, redaction baseline, and a final gate.

## Non-Goals

- Do not implement FT-001 auth/session product behavior.
- Do not implement FT-002 Farm/Plant lifecycle or `tomato_001` seed behavior.
- Do not implement FT-003 direct Account creation/admin/audit product workflows.
- Do not implement Bus, agent runtime, MessageEnvelope/UI Feed, Safety Gate,
  photo catalog, timeline taxonomy, dataset governance, or PWA UI.
- Do not recreate `.memory-bank/contracts/foundation-critical-path.md`.

## Task Queue

| Task | Tier | Status | Purpose |
|---|---|---|---|
| `TASK-000-T1-FT-000-W0` | T1 | done | Align task schema/protocol evidence and backend scaffold/package anchors. |
| `TASK-001-T2-FT-000-W0` | T2 | done | Implement Linux Mint local bootstrap and local runtime configuration roots. |
| `TASK-002-T2-FT-000-W0` | T2 | done | Implement local PostgreSQL init, Alembic migration, and DB readiness baseline. |
| `TASK-003-T3-FT-000-W0` | T3 | done | Implement secret redaction baseline for bootstrap, settings, errors, and evidence. |
| `TASK-004-T2-FT-000-W0` | T2 | done | Run final Foundation gate and record build/start/bootstrap/db/migration/test evidence. |

All `FT-000/W0` tasks are done. W0 semantic red-verification is
`semantic-pass`. `/mb-sync` does not generate or promote product tasks.

## Dependency Order

```text
TASK-000-T1-FT-000-W0
  -> TASK-001-T2-FT-000-W0
  -> TASK-002-T2-FT-000-W0
  -> TASK-003-T3-FT-000-W0
  -> TASK-004-T2-FT-000-W0
```

The final gate depends on all implementation/probe tasks. Product tasks created
later must depend directly or transitively on `TASK-004-T2-FT-000-W0`.

## Verification Strategy

- T1 task may use compact protocol and local checks.
- T2 tasks require full protocol, complete indexed task cards, `/verify PASS`, and
  MB-SYNC.
- T3 redaction task requires full protocol, complete indexed task card, `/verify PASS`,
  per-task `/red-verify` semantic-pass, `HUMAN_CHECKPOINT: done`, and
  `ROLLBACK_RECOVERY_NOTE: present` before closure.
- Final gate verifies the complete `.memory-bank/foundation.md` exit criteria.

## Handoff

Foundation is complete. Product tasking may proceed for features with completed
feature-level SDD designs. FT-001 planning/review and W1 are complete; TASK-007
is the next promotion candidate under a separate owner readiness decision.

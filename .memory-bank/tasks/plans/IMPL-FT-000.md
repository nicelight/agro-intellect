---
description: Implementation plan for FT-000 Foundation Dev Path.
status: active
type: implementation_plan
feature_id: FT-000
last_updated: 2026-06-24
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
- Do not implement FT-003 admin/invite/audit product workflows.
- Do not implement Bus, agent runtime, MessageEnvelope/UI Feed, Safety Gate,
  photo catalog, timeline taxonomy, dataset governance, or PWA UI.
- Do not recreate `.memory-bank/contracts/foundation-critical-path.md`.

## Task Queue

| Task | Tier | Status | Purpose |
|---|---|---|---|
| `TASK-000-T1-FT-000-W0` | T1 | done | Align task schema/protocol evidence and backend scaffold/package anchors. |
| `TASK-001-T2-FT-000-W0` | T2 | done | Implement Linux Mint local bootstrap and local runtime configuration roots. |
| `TASK-002-T2-FT-000-W0` | T2 | planned | Implement local PostgreSQL init, Alembic migration, and DB readiness baseline. |
| `TASK-003-T3-FT-000-W0` | T3 | planned | Implement secret redaction baseline for bootstrap, settings, errors, and evidence. |
| `TASK-004-T2-FT-000-W0` | T2 | planned | Run final Foundation gate and record build/start/bootstrap/db/migration/test evidence. |

`TASK-002-T2-FT-000-W0` has all direct dependencies done and is eligible for a
separate scheduler/owner promotion pass. `/mb-sync` does not promote dependent
tasks by itself.

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
- T2 tasks require full protocol, required packets, `/verify PASS`, and
  MB-SYNC.
- T3 redaction task requires full protocol, required packet, `/verify PASS`,
  per-task `/red-verify` semantic-pass, `HUMAN_CHECKPOINT: done`, and
  `ROLLBACK_RECOVERY_NOTE: present` before closure.
- Final gate verifies the complete `.memory-bank/foundation.md` exit criteria.

## Handoff

After `/foundation-to-tasks`, run:

```bash
node scripts/mb-doctor.mjs
```

Then execute and verify `FT-000` tasks in dependency order. Do not run product
`/prd-to-tasks` until the final gate task is `done`.

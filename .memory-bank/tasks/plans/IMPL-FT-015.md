---
description: Implementation plan for FT-015 local-only runtime, product redaction, photo storage pressure, and stateless prompt handoff.
status: active
type: implementation_plan
feature_id: FT-015
last_updated: 2026-08-13
source_of_truth:
  - .memory-bank/features/FT-015-local-security-privacy-storage-prompt.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/contracts/product-surface-redaction.md
  - .memory-bank/testing/local-privacy-storage.md
---
# IMPL-FT-015 — Local Security Privacy And Storage Prompt

## Goal

Close REQ-020 with a fail-closed `local_only` runtime, the supported
loopback-only launch boundary, product-surface secret/auth redaction, one
authoritative Farm photo-pressure read, and a protected stateless handoff that
FT-016 can render without gaining storage or sync authority.

## Scope

- validate `local_only` as the only accepted MVP sync status;
- retain and prove the supported `127.0.0.1` launch path without adding the
  optional LAN capability;
- apply the canonical product redaction contract to current log/error,
  manifest, Timeline, Plant History/export, atomic Bus/UI Feed publication,
  generic Agent Runtime, and each competence request owner;
- aggregate accepted original photo bytes once per authoritative Photo Catalog
  row and compare strictly with `209715200`;
- expose one authenticated Farm-wide `GET /api/photos/storage-status` with an
  exact `PhotoStorageStatus` response and `Cache-Control: no-store`;
- prove acknowledge/dismiss are Account-isolated transient consumer actions,
  with no backend mutation, Timeline event, upload authority, or sync change;
- preserve the future screenshot/browser implementation for FT-016.

## Non-goals

- no LAN mode, host override, CORS configuration, bearer-LAN transport, TLS,
  remote access, or LAN live smoke;
- no Svelte/SvelteKit scaffold, component, route, browser storage, screenshot,
  or first-demo implementation;
- no prompt table, acknowledgment/dismiss endpoint, cooldown, episode, growth
  delta, migration, Timeline event, or durable preference;
- no filesystem/disk usage scan, manifest/database/log/cache/export accounting,
  server upload/sync, remote target, or `server_verified`;
- no change to Photo Catalog identity, artifact retention, Dataset Candidate
  lifecycle, agent authority, UI Feed consumability, or provider selection.

## Capability ownership and accepted edges

- **Runtime Substrate** owns validated local settings, the loopback start path,
  and shared sanitization primitives under `backend/app/config.py`,
  `backend/app/core/`, and `scripts/`; product owners retain output authority.
- **Photo Intake** owns aggregation and the protected status endpoint under
  `backend/app/photo_intake/` and `backend/app/api/photos.py`; it consumes
  [Local Runtime Policy](../../contracts/boundary-map.md#local-runtime-policy),
  [Product Surface Redaction](../../contracts/boundary-map.md#product-surface-redaction),
  and [ActorContext Gate](../../contracts/boundary-map.md#actorcontext-gate).
- **Timeline Audit** and **Plant History** remain independent serializer
  owners. **Agent Chat & UI Feed** owns one atomic guarded-publication result.
- **Agent Runtime Core**, **Vision Observation**, **Plant State**,
  **Hydroponics Advisor**, **Safety Gate**, **Task & Follow-Up**, and
  **Companion Governance** each own their strict request result. **Dataset
  Governance** owns both Dataset Agent request types through its one shared
  post-TASK-060 runtime/provider-call flow. Every owner consumes only the
  shared primitive through
  [Product Surface Redaction](../../contracts/boundary-map.md#product-surface-redaction).
- **Operator PWA** remains an FT-016 consumer through
  [Presentation Calls Backend Authority](../../contracts/boundary-map.md#presentation-calls-backend-authority);
  no frontend code is created by this plan.

Business/data decisions stay in the owning service/repository. FastAPI handlers,
`backend/app/main.py`, and generic helpers do not own aggregation, prompt state,
or cross-module orchestration.

## Sequential task strategy

| Candidate | Independent result | Accepted dependencies |
|---|---|---|
| TASK-062 | fail-closed `local_only` settings | verified Foundation gate |
| TASK-063 | supported loopback-only exposure proof | verified Foundation gate |
| TASK-064 | runtime log/API-error redaction | Foundation plus terminal Access & Admin HTTP owner |
| TASK-065 | authoritative Farm photo-pressure aggregation | terminal Photo Catalog owner |
| TASK-072 | current browser-capture non-applicability and FT-016 handoff | verified Foundation gate |
| TASK-066 | protected status plus stateless per-Account handoff | TASK-065 and terminal Photo HTTP owner |
| TASK-067 | photo-manifest redaction | TASK-064 and terminal Photo Artifact owner |
| TASK-068 | Timeline append redaction | TASK-064 and terminal Timeline owner |
| TASK-069 | atomic Bus/UI Feed redaction | TASK-064 and terminal Feed owner |
| TASK-070 | generic Agent Runtime request redaction | TASK-064 and terminal generic runtime owner |
| TASK-071 | Plant History/export redaction | TASK-064 and terminal Plant History repair |
| TASK-073 | Vision Observation request/media redaction | TASK-064 and terminal Vision owner |
| TASK-074 | Plant State request redaction | TASK-064 and terminal Plant State owner |
| TASK-075 | Hydroponics Advisor request redaction | TASK-064 and terminal Advisor owner |
| TASK-076 | Safety Gate request redaction | TASK-064 and terminal classifier owner |
| TASK-077 | Task and Follow-Up request redaction | TASK-064 and terminal Task runtime owner |
| TASK-078 | Companion request redaction | TASK-064 and terminal Companion runtime owner |
| TASK-079 | both Dataset Agent requests through one shared flow | TASK-064 and terminal TASK-060 shared-flow owner |

Tasks in the same wave are independent readiness peers; canonical execution
remains sequential. Dependency proof stays with its owning task.

## Expected advisory change surface

- Runtime Substrate: `backend/app/config.py`, `backend/app/core/`,
  `.env.example`, local runtime tests and runbook assertions.
- Photo Intake: `backend/app/photo_intake/repository.py`, `service.py`,
  `storage.py`, `backend/app/api/photos.py`, and focused photo/API tests.
- Timeline and Plant History: independent `backend/app/timeline/` and
  `backend/app/plant_history/` owner paths plus their focused tests.
- Bus/UI: `backend/app/agent_chat/` and its atomic publication/feed tests.
- Agent context: `backend/app/agent_runtime/` plus the existing
  `vision_observation/`, `plant_state/`, `hydroponics_advisor/`,
  `safety_gate/`, `task_follow_up/`, `companion_governance/`, and
  `dataset_governance/` request owners and focused provider-spy tests.
- Operator PWA handoff: FT-016 canonical links only; no `frontend/` code or
  capture implementation is created.
- Durable design/evidence stays in the linked FT-015 specs, task cards,
  `.protocols/`, and `.tasks/`; advisory paths are not hard write boundaries.

## Verification, gates, and UAT

- Each T2/T3 card records honest claim-linked RED followed by equivalent GREEN,
  or preserves pre-implementation GREEN when the exact owner behavior already
  satisfies the claim without a production change.
- Focused settings/runtime, photo repository/service/API, serializer/writer,
  atomic Bus/UI, and owner-specific provider-request suites prove each owned
  result independently. The Dataset suite distinguishes both requests inside
  its shared runtime flow.
- Cross-surface secret tasks use the same configured corpus but do not inherit
  each other's proof.
- Applicable owner regressions and the full deterministic backend suite run
  where the task changes a shared redaction primitive or multi-consumer path.
- All cards run `node scripts/mb-lint.mjs` and `git diff --check`; no external
  provider, remote upload/server, frontend, or live LAN smoke is required.
- T3 tasks require `/verify` plus per-task `/red-verify`; after all tasks are
  implemented, FT-015 requires feature-level `/red-verify --feature FT-015`.

## Governing sources and invariants

- Governing requirement: REQ-020. REQ-021 applies only to the responsibility
  and future-browser handoff ACs; this plan does not own the FT-016 demo.
- Constitution local-first, low-maintenance, bounded-autonomy, no-SaaS, and
  KISS rules remain binding.
- [Photo Artifacts](../../domains/photo-artifacts.md#farm-photo-storage-pressure),
  [Photo Intake HTTP](../../contracts/photo-intake-http.md#storage-status-behavior),
  [Product Surface Redaction](../../contracts/product-surface-redaction.md#surface-rules),
  and [Local Privacy Verification](../../testing/local-privacy-storage.md)
  are the direct design/proof owners.
- PostgreSQL Photo Catalog is the sole aggregation authority; filesystem and
  Dataset refs never contribute.
- Redaction happens before output and never mutates source credentials or
  grants authority.
- Prompt actions persist nothing; every fresh status request re-evaluates the
  current Farm total and remains `local_only`.

## Handoff

Queue action: `rebuild_required`, completed as a targeted repair of the
existing planned queue. TASK-062 through TASK-070 preserve their identities;
only TASK-064/068/069/070 changed where direct context or execution cohesion
required it, and TASK-071 through TASK-079 carry the extracted sibling
outcomes. The resulting eighteen-card queue targets Global Planning Revision 4
and must receive fresh `/review-tasks-plan FT-015` approval before execution
or scheduler promotion.

---
description: Foundation Dev Path evidence and feature pressure map.
status: active
owner: architecture
last_updated: 2026-06-23
source_of_truth:
  - .memory-bank/spec-backbone.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/foundation-critical-path.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/index.md
---
# Foundation Dev Path

## Gate Anchors
- Foundation Required: true
- Foundation Requirement: REQ-000
- Foundation Pseudo-Feature: FT-000
- Foundation Gate Task: pending_/foundation-to-tasks

## Decision

Foundation is required before product feature tasking.

Reason: the first useful MVP path crosses too many shared authority boundaries to implement feature-by-feature safely without a verified walking skeleton. The existing backend scaffold proves only FastAPI app creation, settings, database handle, Alembic entrypoint, and pytest harness. It does not yet prove the critical event/agent/safety/state/export chain.

`REQ-000`, `FT-000`, `TASK-*`, packets, protocols, and implementation plans are not created by `/spec-design`; `/foundation-to-tasks` owns those artifacts.

`/spec-design` does not choose the final foundation gate task id or infer the number of foundation tasks. `/foundation-to-tasks` must decide the task queue, create exactly one final gate task, and replace `pending_/foundation-to-tasks` with that concrete task id.

The executable contract for the critical path is [.memory-bank/contracts/foundation-critical-path.md](contracts/foundation-critical-path.md). `/foundation-to-tasks` must use it as a normative input when creating `FT-000` task records and the final foundation gate task.

## Critical Path

The foundation must prove this path with a minimal fixture or smoke workflow:

```text
Photo/User input
  -> BusEventEnvelope
  -> Agent invocation
  -> Project-owned adapter
  -> MessageEnvelope
  -> UIFeedEvent projection split
  -> Safety / State / Task transitions
  -> PostgreSQL mutable state + timeline.jsonl append-only audit
  -> photo JSON export snapshot
```

## Minimal Work Path
- Build command: `python -m pip install -e ".[test]"`
- Start command: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Primary entrypoint: `backend.app.main:create_app`
- Smoke path: foundation integration test or local smoke endpoint exercises one authorized user input and one photo fixture through the Critical Path.
- Test command: `python -m pytest tests`
- Evidence: pytest output, generated timeline JSONL sample, PostgreSQL/read-model rows or test DB assertions, generated photo JSON export sample, and redaction/context-hygiene assertions.

## Required Compatibility Probes
- Input/photo probe: satisfies `C-FND-001` by accepting a minimal observation/manual measurement payload and a small photo fixture, computing or recording photo identity, and creating source refs.
- Bus probe: satisfies `C-FND-002` by creating a valid BusEventEnvelope with `consumable_by_agents` and `authorization_scope`.
- Agent probe: satisfies `C-FND-003` by invoking the model adapter boundary through a project-owned adapter. Test-only stubs are allowed only inside tests and must not be wired as MVP runtime/demo acceptance.
- Message/UI split probe: satisfies `C-FND-004` by producing a MessageEnvelope and a separate UIFeedEvent projection; UI Feed projection is never consumed by the agent context builder.
- Safety/state/task probe: satisfies `C-FND-005` by blocking or fail-closed routing a physical-action implication while allowing only a safe clarification/task request.
- Persistence/audit/export probe: satisfies `C-FND-006` through `C-FND-008` by writing mutable state to PostgreSQL/read model, appending a timeline event, and emitting a photo JSON export snapshot with refs back to runtime evidence.
- Redaction/context-hygiene probe: satisfies `C-FND-009` over Bus, adapter, MessageEnvelope, UI Feed, SafetyRouteResult, timeline, export, logs, and captured smoke output.

## Feature Pressure Map
| Feature | Pressure | Foundation Response | Probe | Status |
|---|---|---|---|---|
| FT-001 | ActorContext and role/session contracts must be present before protected input/context paths. | Use a minimal authorized ActorContext fixture or service boundary without full account UI. | Context fixture rejects missing/unauthorized actor. | planned |
| FT-002 | Plant identity and PlantAccessGrant filter every Plant-scoped path. | Seed or fixture one Farm and `tomato_001` permission context. | Unauthorized Plant context cannot enter Bus or agent invocation. | planned |
| FT-003 | Admin audit must not leak into agent facts. | Keep admin audit out of foundation path except safe refs when needed. | Audit/display text is excluded from agent context fixtures. | planned |
| FT-004 | Daily/user input starts the product path. | Minimal observation/manual measurement command enters the same persistence and Bus pipeline. | User input creates source refs and BusEventEnvelope. | planned |
| FT-005 | Photo artifact, manifest, and export refs are shared by agents and dataset flow. | Accept a small photo fixture, store/catalog identity, and export photo JSON snapshot. | Photo JSON export includes refs and does not override runtime state. | planned |
| FT-006 | Runtime state vs timeline authority is cross-cutting. | Write state to PostgreSQL/read model and append timeline JSONL separately. | Timeline replay cannot mutate state in the smoke. | planned |
| FT-007 | Real model-backed agent runtime cannot be a fake product path. | Build adapter seam and runtime decision path; test doubles remain test-only. | Adapter invocation creates auditable runtime decision evidence. | planned |
| FT-008 | Bus/UI Feed split is a core anti-cheat boundary. | Produce separate BusEventEnvelope and UIFeedEvent projection. | Context builder excludes UIFeedEvent content. | planned |
| FT-009 | Vision/photo observation depends on actual photo bytes/refs. | Prove photo refs can reach the adapter boundary without mock product output. | Vision-capable provider can be configured later; test validates boundary shape. | planned |
| FT-010 | Missing/stale data policy affects advice and Safety Gate handoff. | Include a missing-data clarification branch. | Missing data produces clarification/task request, not invented evidence. | planned |
| FT-011 | Physical-action wording must fail closed. | Include one physical-action implication in the foundation smoke. | Safety route blocks or marks pending; no action unlock. | planned |
| FT-012 | Human approval creates tasks/outcomes only after gates. | Prove task-state transition shape without completing approval workflow. | No automated action task is created by agent output alone. | planned |
| FT-013 | Companion governance must stay separate from Safety Gate. | Keep governance out of foundation path except explicit separation assertion. | DecisionRecord absence cannot be treated as Safety Gate approval. | planned |
| FT-014 | Dataset/export evidence must be non-trainable by default. | Photo JSON export carries evidence refs and non-trainable/default metadata. | `can_train_on` remains false or absent until dataset governance permits it. | planned |
| FT-015 | Local privacy, redaction, and storage boundaries affect all artifacts. | Foundation smoke asserts `local_only` and no secrets in logs/timeline/export/feed. | Redaction check over generated artifacts. | planned |
| FT-016 | First demo depends on the whole cross-boundary path. | Foundation gate proves the path before first-demo UI tasking. | One end-to-end backend smoke artifact exists. | planned |

## Deferred Decisions
| Decision | Why deferred | Trigger to revisit |
|---|---|---|
| Exact public HTTP routes for the critical path | Endpoint naming belongs to feature-local design and implementation tasks. Foundation may use minimal internal service or smoke-only route. | `/foundation-to-tasks` task slicing or `/prd-to-tasks FT-004/FT-005/FT-016`. |
| Exact database tables and migrations | `/spec-design` records authority boundaries; concrete schemas belong to FT-000 tasks and later feature specs/tasks. | First FT-000 persistence task. |
| Real provider/model configuration | MVP runtime requires real model-backed flows, but secrets/provider setup must not be invented in docs. | Agent runtime foundation task or explicit provider decision. |
| Full Safety Gate action taxonomy | Foundation needs fail-closed proof, not the full future taxonomy. | `/prd-to-tasks FT-011` or safety-specific task. |
| Full frontend UI behavior | Foundation proves backend/event/export path first; operator UI belongs to FT-016. | `/prd-to-tasks FT-016`. |

## Foundation Exit Criteria
- Minimal path passes.
- Compatibility probes pass.
- `node scripts/mb-doctor.mjs` passes at the foundation/task-queue boundary after `/foundation-to-tasks`.
- Final foundation gate task selected by `/foundation-to-tasks` is `done`.
- Build/start/test/smoke evidence is recorded under `.tasks/` and linked from task records.
- BusEventEnvelope, MessageEnvelope, and UIFeedEvent are distinct in evidence.
- [.memory-bank/contracts/foundation-critical-path.md](contracts/foundation-critical-path.md) `C-FND-001` through `C-FND-009` are satisfied by linked task evidence.
- PostgreSQL/read-model assertions, timeline JSONL append, and photo JSON export snapshot are all present.
- Safety fail-closed behavior is proven for physical-action implication.
- No fake/stubbed product-agent runtime path is accepted as MVP demo evidence.
- No P0/P1 design pressure from the Feature Pressure Map remains unresolved.
- Product feature dev path is allowed only after the final foundation gate is done.

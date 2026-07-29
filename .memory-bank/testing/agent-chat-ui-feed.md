---
description: Verification contract for shared Bus/UI persistence, context hygiene, projections, and Plant feed API.
status: active
type: testing_spec
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md
  - .memory-bank/features/FT-011-safety-gate-physical-action-routing.md
  - .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/companion-governance.md
---
# Agent Chat Bus And UI Feed Verification

## Scope

Defines executable FT-008 verification for lazy roster-introduction
materialization, guarded Bus/UI writes, authorized context/feed reads, and
context isolation, plus the shared compatibility requirements for FT-011
Safety and FT-013 Companion projections. Frontend DOM/e2e rendering remains an
FT-016 consumer check over this exact API.

## Required matrix

| Area | Assertions |
|---|---|
| Migration/models | Forward migration drops only `agent_introduction_batches`; every existing `UIFeedEvent` row, id/payload/`created_at`, restricted FK, introduction uniqueness, Bus dedupe, order index, and fixed consumability flag remains. |
| Lazy introductions | Authorized active-Plant Feed open inserts only missing canonical rows in its current-authorization transaction; existing rows remain unchanged; deterministic ids plus uniqueness make repeat/concurrent/retry opens idempotent. |
| Negative triggers/recovery | Plant create/`201`, startup, restore, archived retained-history reads, Agent Chat Bus, and agent context write no introduction row. Insert/read/commit failure rolls back and maps to `FEED_PERSISTENCE_FAILED`; a later authorized active Feed retry completes missing rows without background repair. |
| Safe publication | Matching non-Companion `safe_information` plus derived `ordinary_dispatch` and current guard atomically creates one typed Bus quotation and one literal UI message; duplicate is idempotent and conflict fails closed. |
| Other classes | `blocked_uncertain` creates only a generic UI notice; task/physical classes create no FT-008 effect. The later FT-011 writer may add only its authoritative derived `safety_status` row. |
| Safety UI route | Exact status/reason/action/freshness/expiry union; project-owned summary only; decision/UI atomicity; both agent flags false; no Bus, approval, task, or action authority. |
| Context builder | Current ActorContext/PlantAccessGrant and active Plant required; UI Feed/raw chat/admin content absent; typed quotation stays data and never enters instruction/routing fields. Agent-specific direct provider assemblers verify their own governance allowlists separately. |
| Feed API | Auth/no-leak, same-transaction current identity/grant/active-Plant checks for introduction writes, read-only retained history, stable pagination, strict cursor/limit errors, no-store, OpenAPI, unchanged response/order/cursor grammar, and both agent flags fixed false. |
| Companion Bus route | Only a valid authorized DecisionRecord produces `domain_event_ref/decision_record`; context resolution loads exactly the non-persisted `ApprovedGovernanceSummaryV1` ids/refs, proposal version, decision/effect/role/time/source refs, and `safety_gate_authority=not_granted`, while conclusion/current-focus and raw/provisional/superseded content remain absent. |
| Companion UI route | Attention, proposal, and decision variants validate strictly, render literal compact summaries, retain both agent flags false, and grant no governance/task/Plant-state/Safety authority. |
| Companion classification hold | `safe_information` creates no FT-008 candidate Bus/UI row; `safe_task_request` creates no FT-012 Task; held physical/blocked/mismatch/failure creates no ordinary row; retry/restore/reconciliation has no replay path. |
| Compatibility | Every existing introduction/UI/Bus row, FT-008 envelope/payload, publication route, and API response remains valid; only presentation batch metadata and its lifecycle disappear. |
| Security | No secrets/auth/provider history/hidden reasoning; markup/prompt/URL-looking text remains unchanged inert data. |

## Behavior traceability

- `FT-008-BHV-001`: authorized active-Plant Feed access inserts only missing
  canonical introduction rows and repeat/concurrent/retry opens converge.
- `FT-008-BHV-002`: archived retained-history reads and restore write nothing;
  only a later authorized active-Plant Feed open may fill missing rows.
- `FT-008-BHV-003`: classified candidate text is literal UI data and typed Bus
  quotation, never an instruction or routing authority.

## Commands

- Focused backend suite: `.venv/bin/python -m pytest tests/backend/agent_chat -q`
- Access/Agent Runtime regression: `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime tests/backend/agent_chat -m "not real_model" -q`
- Full deterministic regression: `.venv/bin/python -m pytest tests -m "not real_model" -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`

FT-016 later adds browser-level text-node/no-active-link verification without
changing this backend contract or making UI Feed agent-consumable.

FT-011 and FT-013 implementation tasks must add focused tests for their own
variants and rerun the existing FT-008 suite as regression evidence; this
shared spec does not claim those not-yet-implemented variants already pass.
